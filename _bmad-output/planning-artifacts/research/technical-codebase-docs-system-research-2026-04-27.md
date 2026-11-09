---
stepsCompleted: [1, 2, 3, 4, 5, 6]
inputDocuments: []
workflowType: 'research'
lastStep: 6
research_type: 'technical'
research_topic: 'Codebase documentation system — markdown wiki kept in sync with GitNexus + Graphiti + BMAD + Claude Code'
research_goals: 'Design a per-project, multi-audience markdown documentation base (functional/business + architecture + runbooks) that stays current via a hybrid of commit-time, session-end, and BMAD-gated triggers. Cover best practices, benchmarks, tools, visualization. Audit and integrate the existing GitNexus + Graphiti + BMAD + Claude Code stack already deployed in the homelab repo.'
user_name: 'tomamourette'
date: '2026-04-27'
web_research_enabled: true
source_verification: true
---

# Research Report: technical

**Date:** 2026-04-27
**Author:** tomamourette
**Research Type:** technical

---

## Research Overview

**Goal.** Design a per-project markdown documentation base for the homelab — multi-audience (users, PO, devs, PM, customers, AI agents), self-maintaining, integrated with the already-deployed GitNexus + Graphiti + BMAD + Claude Code stack — and decide whether the consumption layer is DevOps Wiki, Obsidian, an investigated "LLM-Wiki", or a hybrid. Markdown is the default output unless a clearly superior alternative emerges.

**Method.** Six-step BMAD technical research with three parallel researcher subagents (doc-system landscape, DevOps-wiki vs Obsidian vs LLM-Wiki, Claude-Code-oriented OSS), one direct primary-source review (Karpathy "LLM-Wiki" gist), and direct CLI/MCP-config inspection of the homelab's own GitNexus install. All claims tagged `[verified]` / `[anecdotal]` / `[vendor-claim]` / `[2023-or-earlier]`. Cross-checked against five prior homelab research artifacts (incremental-docs-autoresearch, llm-knowledge-management, graphify-evaluation, memory-systems-evaluation, hybrid-gemma-serving) to avoid re-treading.

**Headline.** Markdown-in-git as single source-of-truth, **Diátaxis** as IA, **Astral + Cline** schema split (`CLAUDE.md → AGENTS.md` + `.claude/rules/<topic>.md`), **GitNexus Code Wiki (OSS)** auto-generates the Reference quadrant, Karpathy's ingest/query/lint loop wired via Claude Code's `SessionEnd` hook, consumption fans out one-way to AzDO Wiki (PM/PO/devs via existing AAD), Obsidian (operator), and optionally Quartz v4 (public/customer). Recommended architecture: **C (hybrid)** with clean fallbacks to A or B if composition cost binds. Six open decisions listed in the Synthesis. **Full executive summary, key findings, and roadmap at the end of the document under "Research Synthesis."**

---

<!-- Content will be appended sequentially through research workflow steps -->

## Technical Research Scope Confirmation

**Research Topic:** Codebase documentation system — markdown wiki kept in sync with GitNexus + Graphiti + BMAD + Claude Code

**Research Goals:** Design a per-project, multi-audience markdown documentation base (functional/business + architecture + runbooks) that stays current via a hybrid of commit-time, session-end, and BMAD-gated triggers. Cover best practices, benchmarks, tools, visualization. Audit and integrate the existing GitNexus + Graphiti + BMAD + Claude Code stack already deployed in the homelab repo.

**Technical Research Scope:**

- Architecture Analysis — doc-system architectures (Backstage TechDocs, MkDocs+mkdocstrings, Docusaurus, Antora, Sphinx, Obsidian-vault-as-source), Diátaxis taxonomy, C4-as-code.
- Implementation Approaches — docs-as-code, ADRs, code-graph→docs, knowledge-graph→docs, drift-detection CI, doc-test coverage, AI-augmented doc tools.
- Technology Stack — markdown-native generators, mermaid/PlantUML/D2, semantic linking, frontmatter metadata, multi-audience tag systems.
- Integration Patterns — Claude Code hooks, BMAD story-done gates, GitNexus MCP queries, Graphiti episode/fact retrieval, MCP-driven doc updates.
- Performance Considerations — drift latency, false-positive update rate, token cost, multi-project scaling, human-vs-agent edit conflict policy.

**Research Methodology:**

- Current web data with rigorous source verification.
- Multi-source validation for critical technical claims.
- Confidence levels for uncertain/vendor-marketed claims.
- Cross-check against prior homelab research artifacts to avoid re-treading.
- Comprehensive technical coverage with architecture-specific insights.

**Scope Confirmed:** 2026-04-27

---

## Technology Stack Analysis

*Two-track analysis: (A) audit of the homelab's currently-deployed stack, then (B) landscape survey of doc-system technology in 2024–2026 with confidence tags `[verified]` / `[vendor-claim]` / `[anecdotal]` / `[2023-or-earlier]`.*

### A. Current Homelab Stack — Audit

#### A.1 Existing Documentation Surface

The homelab repo already has a non-trivial doc baseline at `/docs/`, last regenerated 2026-04-02 by **BMAD Document Project workflow v1.2.0**:

- `index.md` — top-level hub linking generated and pre-existing docs
- `project-overview.md`, `source-tree-analysis.md`, `development-guide.md`, `deployment-guide.md`, `integration-architecture.md`
- Three per-repo architecture docs: `architecture-homelab-infra.md`, `architecture-homelab-apps.md`, `architecture-homelab-playbook.md`
- `project-scan-report.json` — machine-readable scan output (state-tracking artifact)

In addition, each sub-repo has its own pre-existing docs (`README.md`, `SETUP-GUIDE.md`, `TROUBLESHOOTING-GUIDE.md`, `CONFIGURATION.md`, `ARCHITECTURE.md`, etc.) that the index knits together by reference, not duplication.

**Implication:** The repo is *already* operating on a "central `/docs/` index + pre-existing per-repo docs" pattern. Any new system must respect this layering, not flatten it.

#### A.2 BMAD Documentation Skills

| Skill | Mode(s) | Key behavior |
|---|---|---|
| `bmad-document-project` | Single (full) | Brownfield scan → generates `/docs/` baseline (the 8 files above). v1.2.0. |
| `bmad-update-project-docs` | `check` / `update` / `full` | Detects changed files since last update via git, maps to affected docs. `check` = read-only health report; `update` = section-level updates with user confirmation; `full` = delegates to `bmad-document-project`. State tracked between runs. |
| `bmad-generate-project-context` | Single | Produces `project-context.md` (AI-rules / project-context for downstream agents). |
| `bmad-shard-doc` | Single | Splits large MDs into smaller files at level-2 sections. |
| `bmad-index-docs` | Single | Generates/updates an `index.md` referencing all docs in a folder. |

**Strengths observed:** Three-mode incremental flow (`check`/`update`/`full`) is the right shape; git-diff drift detection is already wired; section-level updates preserve unchanged sections (avoids whole-file rewrites that lose history).

**Gaps observed:** Trigger is *user invocation only* — no commit-time, session-end, or BMAD-story-done auto-trigger today. No prose linting, no link checking, no doc-CI. No auto-publishing (renders only via direct file viewing or GitHub).

#### A.3 GitNexus (live code-graph MCP)

- Configured at **user scope** (deferred MCP tools `mcp__gitnexus__*` visible: `context`, `cypher`, `query`, `impact`, `route_map`, `tool_map`, `rename`, `shape_check`, `api_impact`, `detect_changes`, `group_list`, `group_sync`, `list_repos`).
- Wired into `~/.claude/settings.json` via PreToolUse (`Grep|Glob`) and PostToolUse (`Bash`) hooks at `/home/developer/.claude/hooks/gitnexus/{pre,post}.sh` with 3-second timeouts and explicit "graph hint" / "reindex check" status messages.
- **Capability for docs:** `detect_changes` and `impact` are the natural plumbing for "this code area changed, which doc pages depend on it"; `route_map` / `tool_map` give live route/CLI inventories that should *not* be duplicated into markdown.

#### A.4 Graphiti (temporal knowledge-graph MCP)

- Configured at user scope (`mcp__graphiti__*` deferred: `add_memory`, `search_memory_facts`, `search_nodes`, `get_episodes`, `get_entity_edge`, `delete_episode`, `delete_entity_edge`, `get_status`, `clear_graph`).
- Per the MCP server-instructions block: episodes (text/JSON snippets), nodes (entities), facts (temporal relationships with creation/invalidation timestamps), grouped by `group_id`.
- **Capability for docs:** holds the *why* — decisions, episodes, dated context — that markdown should reference but not duplicate. Strong fit for ADR provenance and "decision lineage" sidebars in narrative docs.

#### A.5 Claude Code Auto-Memory

- File-based memory at `~/.claude/projects/-home-developer-workspace-homelab/memory/` with `MEMORY.md` index + per-fact files (user/feedback/project/reference types).
- Already loaded into every conversation (≤200 lines of index).
- **Capability for docs:** captures *operator-level* learnings (e.g., "PVE 9 HA error recovery", "YAML block-scalar regex trap") that often belong in the wiki as runbook sections — but currently live only in Tom's Claude memory, invisible to other audiences (PM, customers, future devs).

#### A.6 BMAD Workflow Status

- BMAD module config at `_bmad/bmm/config.yaml` resolves `project_knowledge: docs/`. Versions: BMAD 6.2.2.
- BMAD is used for *some* work (PRD, architecture, stories, retros) but not all. The doc system must therefore work with **and without** BMAD invocation.

#### A.7 Audit Summary

| Layer | Today | Gap for the wiki goal |
|---|---|---|
| **Source format** | Markdown (CommonMark/GFM) | None — already aligned with default best practice |
| **Information architecture** | Ad-hoc per file; no Diátaxis taxonomy | No multi-audience IA — same doc serves all audiences indistinctly |
| **Generators** | None — files served as raw `.md` via GitHub | No rendered site for non-dev audiences (PM, customers) |
| **Drift detection** | Git-diff via `bmad-update-project-docs` (manual trigger) | No auto-trigger; no link-check; no prose-lint |
| **Visualization** | None in `/docs`; mermaid not yet adopted | Diagrams missing (architecture, flows, C4) |
| **Decision capture** | Graphiti (temporal) + auto-memory + ad-hoc retro markdown in `_bmad-output/` | No ADR catalog under `/docs/adr/`; decisions are scattered |
| **Code → docs** | None automated | mkdocstrings-equivalent for IaC (Terraform/Ansible) is missing |
| **Code-graph → docs** | GitNexus available, not wired to docs | Open ground — unique opportunity vs typical setups |
| **Knowledge-graph → docs** | Graphiti available, not wired to docs | Same — speculative but credible |

---

### B. Landscape Survey — Doc-System Technology Stack (2024–2026)

#### B.1 Source Formats

| Format | Multi-audience | Diagrams | AI-readability | Grep | Verdict for this use case |
|---|---|---|---|---|---|
| **CommonMark/GFM Markdown** | Excellent | Mermaid native in GFM | Excellent (LLMs trained heavily on it) | Excellent | **Default** [verified] |
| **MDX** | Good for devs, opaque to non-devs | Excellent (React) | Good but JSX confuses smaller models | Degraded | Lock-in to React; reach for only if SSG demands it |
| **AsciiDoc** | Excellent (admonitions, includes, conditionals) | Excellent | Good | Good | Technically superior; ecosystem gravity is on MD's side |
| **reStructuredText** | Devs only | Excellent (Sphinx) | Mediocre (noisy directives) | Mediocre | Skip unless Python-only |
| **Quarto** | Excellent for technical/data | Excellent (executable code, multi-engine) | Good | Good | Reach for only if reproducible-executable docs become a need (not the case — GitNexus covers live data) |
| **Org-mode** | Single-author / Emacs | Excellent | Mediocre | Good | Niche; skip |

**Recommendation:** **CommonMark/GFM Markdown** as default narrative format, with **Mermaid fenced blocks** for diagrams. Already aligned with current BMAD output. [verified]

#### B.2 Static Site Generators & Doc Frameworks

| SSG | Source | Multi-project | Search | Diagrams | Plugins | Non-dev fit |
|---|---|---|---|---|---|---|
| **MkDocs + Material** | MD | `monorepo-plugin` / multi-site | Lunr (Material instant search) | Mermaid/PlantUML/Kroki via plugins | Very mature, 100+ | **Strong — friendliest non-dev MD output** [verified] |
| **Docusaurus** | MDX | Multi-instance plugin | Algolia DocSearch / local | Mermaid native v3+, D2 plugin | Very mature | Good but MDX/React surface leaks to writers |
| **Antora** | AsciiDoc | **Best-in-class** multi-repo aggregation | Lunr | PlantUML/Kroki | Mature but small | Killer feature: pulls docs from N git repos into one site [verified] |
| **Sphinx** | rST/MyST-MD | OK (intersphinx) | Built-in | Excellent | Massive (Python-centric) | Poor for non-devs unless heavily themed |
| **Backstage TechDocs** | MD (MkDocs under the hood) | Excellent — designed for catalogs | Backstage search | Mermaid/PlantUML | Mature | Overkill for solo homelab |
| **Hugo + Doks/Hextra** | MD | Module system | Lunr/Pagefind | Mermaid | Hugo core mature | Solid; Go-template friction for writers |
| **Quartz** | MD (Obsidian-flavored) | Single vault | FlexSearch | Mermaid, Excalidraw | Smaller post-v4 rewrite | **Best-in-class for vault-as-source** [verified] |
| **Astro Starlight** | MD/MDX | OK | Pagefind (excellent) | Mermaid via plugin | Growing fast 2024–2026 | Excellent — modern, friendly, fastest-growing [verified] |
| **VitePress** | MD | Single site | Local + Algolia | Mermaid plugin | Vue-aligned | Good if Vue-aligned |
| **Nextra** | MDX | Single-site / docs-theme | FlexSearch | Mermaid native | Next.js shops | Good for Next.js |
| **mdBook** | MD | Single book | Built-in | Mermaid plugin | Rust-bound, simple | Good for "book"-shaped docs |

**Honest tradeoffs:**
- **MkDocs Material** is the pragmatic 2026 default for single-project wiki: zero JS-framework lock-in, plugin sprawl, friendly authoring. [verified]
- **Antora** is the only one *designed* for multi-repo aggregation — relevant given homelab is three-repo.
- **Backstage TechDocs** shines at 50+ services with platform-team buy-in, not solo ops.
- **Starlight** has most momentum 2024→2026 and cleanest UX; smaller plugin set than MkDocs.
- **Quartz v4** is the right answer if Obsidian-vault-as-source is the model.

#### B.3 Wiki / Knowledge-Base Systems

| Tool | Source-of-truth | Publishing | Best fit |
|---|---|---|---|
| **Obsidian (vault) + Quartz v4** | Local MD vault, [[wikilinks]], YAML frontmatter | Quartz → static site | Thinking + writing colocated; freeform graph linking [verified] |
| **Obsidian Publish** | Vault | Hosted (~$10/mo/site) | Convenient but pricey vs Quartz [verified] |
| **Logseq** | Outliner MD/Org | Logseq Publish | Block-level transclusion; smaller community |
| **Foam** | VS Code over MD vault | Any SSG | Devs in VS Code |
| **Dendron** | Hierarchical MD | Next.js publisher | **Company shut down 2023; community fork stagnant** [2023-or-earlier] |
| **Outline** | DB-backed | Web app | Team wiki; *not* git-native |
| **BookStack** | DB-backed (PHP/Laravel) | Self-hosted web | Friendly for non-devs; *not* docs-as-code |
| **MediaWiki** | Wikitext + DB | Self-hosted | Heritage; high ops cost; non-MD source |

**Vault-as-source vs SSG `/docs`:**
- **Vault wins** when writing is exploratory, links are organic, the same person captures and consumes.
- **SSG `/docs` wins** when docs are versioned with code, PR-reviewed, multi-author with rigid IA, drift visible in diffs.
- **Hybrid is real:** Obsidian vault for *narrative/decisions/research*, per-repo `/docs` for *code-coupled reference*. Quartz publishes the vault; MkDocs publishes per-repo. Linked at the seams.

#### B.4 Diagrams & Visualization (2026 state)

| Tool | GitHub render | MkDocs Material | Docusaurus | Obsidian | Backstage TechDocs |
|---|---|---|---|---|---|
| **Mermaid** | Yes (native since 2022) | Yes (plugin) | Yes (native v3+) | Yes (native) | Yes [verified] |
| **PlantUML** | No (image only) | Yes (Kroki/plugin) | Plugin | Plugin | Yes |
| **D2** | No (image only) | Plugin / Kroki | Plugin | Plugin | Via Kroki |
| **Excalidraw-as-code** | No (image) | Embed | Embed | **Native (popular plugin)** | Limited |
| **Structurizr DSL** | No (rendered) | Embed via Structurizr Lite | Embed | Embed | Embed |
| **Likec4** | No (image/HTML) | Embed/iframe | React component | Limited | Limited |
| **Kroki** | N/A (rendering service) | mkdocs-kroki-plugin | Yes | Plugin | Yes |

**2025–2026 shifts:**
- **Mermaid** added sankey, block, packet diagram types through 2024–2025 [verified].
- **D2** has real momentum but Mermaid's GitHub-native rendering keeps it 4× ahead by stars [verified].
- **Likec4** emerged as TypeScript-native C4 alternative to Structurizr DSL; growing but small [verified].
- **Excalidraw-as-code** via Obsidian plugin remains the path for hand-drawn-feel diagrams that round-trip with text [verified].

**Pragmatic stack:** Mermaid for everyday flows + Likec4 or Structurizr DSL for C4 architecture + Kroki as fallback for D2/PlantUML.

#### B.5 Adoption Signals (verified 2026-04-27)

| Project | GitHub stars | Trend |
|---|---|---|
| Mermaid | ~76k | Dominant diagram-as-code [verified] |
| Docusaurus | ~58k | Largest doc-SSG by stars [verified] |
| Backstage | ~30k | TechDocs is a feature, not standalone |
| squidfunk/mkdocs-material | ~22k | Highest-velocity MkDocs theme [verified] |
| MkDocs | ~20k | Steady |
| D2 | ~19k | Real momentum, Mermaid 4× ahead |
| mdBook | ~18k | Niche-loyal (Rust ecosystem) |
| VitePress | ~13k | Strong in Vue |
| Nextra | ~12k | Strong in Next.js |
| PlantUML | ~12k | Mature, slowing |
| lychee | ~10k | Eclipsed `markdown-link-check` |
| Sphinx | ~7k | Stable; Python-bound |
| Quartz | ~7k | Strong growth 2024–2025 [verified] |
| Astro Starlight | ~6k | Fastest-growing 2024–2026 [verified] |
| Vale | ~5k | Prose-linting standard |
| Antora | ~600 (gitlab.com primary) | Niche but loyal |

**Real-world large-project use:**
- Kubernetes: Hugo + Docsy [verified]
- CNCF projects broadly: MkDocs Material is the most common choice [anecdotal but widely observed]
- Backstage (Spotify + CNCF): TechDocs/MkDocs [verified]
- Cloudflare, GitLab, Django, NumPy: Diátaxis-organized docs [verified]
- FastAPI: MkDocs Material + mkdocstrings [verified]
- Rust: mdBook [verified]

**StackOverflow Survey 2024:** Markdown remains top "documentation format" by usage; no comparable 2025 survey published as of 2026-04 [verified].

#### B.6 SSG Shortlist (carried into Step 4 for deeper architectural comparison)

1. **MkDocs Material + mkdocstrings + Mermaid + Vale/lychee/markdownlint CI + ADR folder + Diátaxis IA** — *Best when* one repo's `/docs` rendered cleanly with minimal framework lock-in and rich plugin choice.
2. **Obsidian vault + Quartz v4** — *Best when* narrative/decision-capture and consumption happen in the same vault and graph-style cross-linking matters more than per-repo coupling.
3. **Astro Starlight + Mermaid + Pagefind** — *Best when* a modern, fast, polished static site with low JS-framework gravity is the priority.
4. **Antora + AsciiDoc** — *Best when* docs are aggregated from *multiple* repos into one site (relevant for the three-repo homelab).
5. **Hybrid: Obsidian/Quartz (narrative + ADRs + research) ⟷ MkDocs Material per-repo (`/docs` for code-coupled reference)** — *Best when* the user wants vault freedom for thinking *and* PR-gated docs-as-code per repo.

---

**Sources:**
- CommonMark spec: https://spec.commonmark.org/0.31.2/
- Quarto: https://quarto.org
- MkDocs Material: https://squidfunk.github.io/mkdocs-material/
- Antora: https://antora.org
- Docusaurus: https://docusaurus.io
- Quartz v4: https://quartz.jzhao.xyz
- Astro Starlight: https://starlight.astro.build
- Backstage TechDocs: https://backstage.io/docs/features/techdocs/techdocs-overview
- Mermaid: https://mermaid.js.org
- D2: https://d2lang.com
- Likec4: https://likec4.dev
- Kroki: https://kroki.io
- StackOverflow Developer Survey 2024: https://survey.stackoverflow.co/2024
- Kubernetes docs style: https://kubernetes.io/docs/contribute/style/
- mdBook: https://rust-lang.github.io/mdBook/

Cross-references to prior homelab research (avoid re-treading):
- `technical-incremental-docs-autoresearch-2026-04-03.md` — incremental docs / autoresearch loop pattern
- `technical-llm-knowledge-management-research-2026-04-11.md` — LLM-side knowledge management
- `technical-graphify-evaluation-2026-04-25.md` — graphify pilot verdict
- `technical-memory-systems-evaluation-2026-04-25.md` — Graphiti vs alternatives

---

### C. Consumption-Layer Comparison — DevOps Wiki vs Obsidian vs LLM-Wiki

*User constraint added 2026-04-27: viewing platform = DevOps Wiki and/or Obsidian; investigate "LLM-Wiki" non-biased.*

#### C.1 DevOps Wiki Options — Side-by-side

| Dimension | Azure DevOps Wiki | GitLab Wiki | GitHub Wiki | Gitea / Forgejo Wiki | Wiki.js v2/v3 | BookStack |
|---|---|---|---|---|---|---|
| **Source storage** | Git (`wikiMaster` branch) or Code Wiki at any branch [v]¹ | Git (`<project>.wiki.git`) [v]² | Git (`<repo>.wiki.git`, `master`/`main` only) [v]³ | Git (`<repo>.wiki.git`) [v]⁴ | DB (Postgres/MariaDB); v3 optional git sync [v]⁵ | DB (MySQL/MariaDB), MD import/export only [v]⁶ |
| **MD flavor** | CommonMark + AzDO ext. (`[[_TOC_]]`, mermaid, KaTeX) [v]¹ | GFM + GitLab ext. (Mermaid, optional PlantUML, math) [v]² | GFM, Mermaid native (2022) [v]³ | GFM via Goldmark [v]⁴ | CommonMark + multiple editors [v]⁵ | Custom WYSIWYG block model [v]⁶ |
| **Diagrams** | Mermaid native, no PlantUML [v]¹ | Mermaid + admin-enabled PlantUML [v]² | Mermaid native [v]³ | Mermaid 1.18+, PlantUML external [v]⁴ | Mermaid + PlantUML + draw.io [v]⁵ | draw.io built-in, Mermaid plugin [v]⁶ |
| **Search** | Project-scoped full-text, weak ranking [a] | ES (Premium/Ultimate) or PG basic [v]² | Repo-scoped, default branch only [v]³ | Bleve full-text [v]⁴ | Built-in + optional Algolia/ES [v]⁵ | Built-in SQL FTS [a] |
| **Access / SSO** | AAD/Entra ID native; per-page ACL in Code Wiki only [v]¹ | Full SSO, per-project roles [v]² | Org SSO (Enterprise); no per-page ACL [v]³ | OAuth2/OIDC/LDAP, repo-level only [v]⁴ | 30+ SSO providers [v]⁵ | SAML/OIDC/LDAP, granular per-shelf/page [v]⁶ |
| **Editing UX** | Raw-MD + preview; no WYSIWYG [v]¹ | Raw-MD + preview; WYSIWYG since 15.x [v]² | Raw-MD + preview, basic WYSIWYG [v]³ | Raw-MD + preview [v]⁴ | Multi-editor (MD/WYSIWYG/visual) [v]⁵ | Block WYSIWYG primary, MD secondary [v]⁶ |
| **Agent updates** | REST + git push to `wikiMaster` [v]¹ | REST + git push, clean agent path [v]² | Limited REST; git push works [v]³ | REST + git push [v]⁴ | GraphQL; git only via module [v]⁵ | REST; no git source [v]⁶ |
| **Self-host** | Hosted only / AzDO Server (paid) | Self-host CE; ~4GB RAM, PG+Redis+Sidekiq [v]² | Hosted only / GHES ($$$) | Single Go binary, ~150MB RAM [v]⁴ | Node + DB, ~500MB RAM [v]⁵ | PHP + DB, ~300MB RAM [v]⁶ |
| **Cost** | Free ≤5 users; included via existing Sparkle-CPS tenant | Free CE; SaaS $0–$29/u/mo | Free public; private needs Pro/Team | Free OSS | Free OSS (AGPL v3) | Free OSS (MIT) |
| **Deal-breakers** | 18MB attachment cap, 50MB/page total [v]¹; only `wikiMaster` renders | `.wiki.git` separate from code = drift risk if mirrored | Wikis not in GH global search; private wikis not Google-indexed [v]³ | Smaller community; Mermaid edge cases lag | DB-backed fights "git-as-SoT" unless v3 storage module wired | DB-backed, no git — **disqualified** for the MD-in-git constraint |

[v] = verified, [a] = anecdotal.
Sources: ¹https://learn.microsoft.com/en-us/azure/devops/project/wiki/wiki-file-structure ²https://docs.gitlab.com/ee/user/project/wiki/ ³https://docs.github.com/en/communities/documenting-your-project-with-wikis ⁴https://docs.gitea.com/usage/wiki ⁵https://docs.requarks.io/install ⁶https://www.bookstackapp.com/docs/

**Per-audience honest take (no winner picked yet):**
- **PM-facing**: AzDO Wiki is lowest-friction — user already has tenant via Sparkle-CPS, AAD SSO, PMs already log into AzDO for boards. Wiki.js wins on UX but needs separate SSO setup.
- **Customer-facing**: None of the DevOps wikis are great — they expose internal nav and require seat licenses. BookStack (anonymous role) or a static site (Quartz) is more honest.
- **Dev-facing**: Any git-backed option works. Gitea is closest to "MD-in-git, zero ops"; AzDO Wiki + Code Wiki mode is most operator-friendly given existing creds.

#### C.2 Obsidian as a Viewing Platform

Three distinct surfaces, often confused:

| Surface | What it is | Audience reach |
|---|---|---|
| **Obsidian-the-app** | Local desktop/mobile app reading a vault of `.md` | **Operator only** — install + vault access required |
| **Obsidian Publish** | Hosted SaaS, $10/mo per site, published URL [v]⁷ | Anyone with URL |
| **Quartz v4** | OSS SSG that reads Obsidian vault, emits Hugo-like static site [v]⁸ | Anyone with URL, free, self-hosted |

⁷https://obsidian.md/publish ⁸https://quartz.jzhao.xyz/

**Ops/multi-audience weak spots (state plainly):**
- **No SSO**. Vault access = filesystem access. Publish has site password only.
- **No audit trail**. Edits aren't attributed unless git history is religiously maintained.
- **No granular ACL**. Vault is all-or-nothing; Publish picks *which notes*, not *who*.
- **No native API for agents** — they edit files on disk (fine), but no "wiki API" surface.
- **Plugin sprawl**: rendering depends on reader's plugins — not portable.

**Sync options for git-as-SoT alignment:**
- **Obsidian Sync** — $5/mo, E2EE, no merge UI [v].
- **Git-backed (`obsidian-git` plugin)** — free, single-operator-friendly, perfectly aligns with MD-in-git constraint [v].

**The "Obsidian for thinking + DevOps wiki for publishing" hybrid** is a real and increasingly common operator pattern (Andy Matuschak, Maggie Appleton, the "digital garden" movement since ~2022). In DevOps/infra teams: operator drafts in Obsidian → commits MD → CI mirrors to Confluence/AzDO/Notion/etc. for read-only audiences. [a — well-documented pattern, not a vendor product]

#### C.3 "LLM-Wiki" — What It Actually Means in 2026

**Honest verdict up front:** "LLM-Wiki" is **not a stable product category** in 2026. It's a cluster of three distinct things conflated under one term.

| Sub-pattern | Status | Notes |
|---|---|---|
| **`llms.txt` convention** [v]⁹ | Real spec, real adoption | `/llms.txt` + optional `/llms-full.txt`. Adopted by Mintlify, Anthropic, Cursor, FastAPI, Pydantic, Stripe, Cloudflare. Skewed to dev-tool docs, not internal wikis. Publishing convention only — doesn't tell you where to host or how humans read it. |
| **GitHub repos named `llm-wiki` / `ai-wiki`** | **No dominant project** | Mostly abandoned 2023–2024 RAG-over-MD POCs. Treat as search term, not product. |
| **MD docs exposed via MCP** [v] | **Realest instantiation** | Anthropic's docs MCP, Cursor `@docs`, `docs-mcp-server`¹⁵, Continue.dev `@docs`. The operative pattern: **MD in git → MCP server → LLM client consumes**; humans get a separate surface (IDE/chat/static site). |
| **LLM-specific frontmatter/chunking** | Informal | `llm-friendly: true`, `summary:`, `tags:` — no formal standard. [a] |
| **Hosted "LLM-native" doc platforms** | Mostly *AI-augmented* authoring | Mintlify AI [vc], GitBook AI [vc], Documind, Docusaurus AI plugins. Distinguish AI-augmented authoring (nice-to-have) from LLM-native consumption (rare). |
| **Pure RAG-against-markdown** [v, common] | What most people mean | Index `/docs` into vector store + chat box. Continue.dev, Cursor, most "talk-to-your-docs" demos do this. |

⁹https://llmstxt.org/ ¹⁵https://github.com/arabold/docs-mcp-server

**Verdict:**
- As a **product category** → marketing fluff. No dominant tool owns the name.
- As an **architectural pattern** ("MD source + MCP/RAG serving + multi-modal consumption: humans-via-chat, agents-via-MCP") → real, increasingly common, and probably the right frame for this homelab.
- **Acceptance test**: ask whether your MD is consumable by both `llms.txt` crawlers *and* MCP clients. If yes, you have the LLM-Wiki property regardless of platform.

#### C.4 Cross-cutting Comparison Matrix

Score 1–5 (5 = excellent). N/A = not applicable.

| Option | Audience reach | Authoring (op + agents) | LLM-readability | Drift detection | Git-as-SoT | Op cost | Lock-in | Multi-repo aggreg. |
|---|---|---|---|---|---|---|---|---|
| **AzDO Wiki** | 4 (AAD covers PM/devs; customers awkward) | 4 (git push + REST) | 3 (REST only, no raw-MD public) | 4 (git history + CI hook) | 4 (`wikiMaster` branch) | 5 (already paid via tenant) | 3 (AzDO MD extensions) | 3 (one wiki per project) |
| **GitLab Wiki** | 4 (full SSO) | 4 (git push + REST) | 3 (same as AzDO) | 4 (git native) | 4 (separate `.wiki.git`) | 3 (needs GitLab) | 3 (portable MD) | 3 |
| **GitHub Wiki** | 3 (audience needs GH) | 3 (git push, API limited) | 3 (public crawlable) | 3 (git native) | 4 (separate `.wiki.git`) | 5 (free public) | 3 (GH-specific) | 2 (no cross-repo nav) |
| **Gitea Wiki** | 3 (login req., weak SSO) | 4 (single binary) | 3 (same as GH) | 4 (git native) | 4 (separate `.wiki.git`) | 4 (homelab-friendly) | 5 (OSS, fully portable) | 2 |
| **Wiki.js** | 4 (broad SSO, public mode) | 3 (DB unless v3 storage) | 2 (DB → MD export non-trivial) | 2 (drift fights DB) | 2 (DB by default) | 3 (PG+Node) | 3 (DB schema yours) | 3 (single instance hosts all) |
| **BookStack** | 4 (granular ACL, public) | 2 (WYSIWYG-first) | 1 (DB, no MD source) | 1 (bespoke) | 1 (not git) | 3 (PHP+DB) | 3 (data in DB) | 3 |
| **Obsidian app only** | 1 (operator only) | 5 (best-in-class solo) | 4 (raw `.md` LLM-trivial) | 5 (git history full) | 5 (vault is the repo) | 5 (free) | 5 (MD only) | 5 (vault includes any folders) |
| **Obsidian Publish** | 4 (public URL) | 4 (same vault) | 3 (HTML; raw MD not public) | 3 (git in vault) | 4 (vault git) | 3 ($10/mo) | 2 (proprietary publish format) | 3 |
| **Quartz v4** | 4 (public URL, free) | 4 (vault input) | 4 (HTML + raw MD optional) | 4 (git retained) | 5 (fully git-backed) | 4 (static, low ops) | 5 (OSS) | 4 (multi-vault possible) |
| **`llms.txt`** | N/A (manifest, not UI) | 3 (manifest to maintain) | 5 (designed for it) | 3 (host-dependent) | 5 (pure MD) | 5 (~zero) | 5 (open spec) | 4 (manifest can list many sources) |
| **MCP-served MD** | N/A for humans | 4 (MD in repo, server reads) | 5 (purpose-built) | 4 (CI diff trivial) | 5 (git-native) | 4 (small server) | 4 (MCP open spec) | 5 (one server, many repos) |
| **RAG over MD (chat UI)** | 4 (chat universal) | 3 (vector pipeline) | 5 (by design) | 3 (index lag = staleness) | 5 (MD in git) | 2 (index/embeddings/eval/drift) | 3 (stack-dependent) | 5 (single index across repos) |

#### C.5 Three Realistic Architectures (carry into Step 6)

**Architecture A — Single DevOps Wiki (likely AzDO)**
- Shape: MD in repo → mirrored/published to AzDO Wiki via `wikiMaster` branch or Code Wiki pointer.
- Reads: PM/PO/devs (AzDO web UI), operator.
- Writes: operator + Claude Code agents pushing to `wikiMaster` via git.
- Agents can: push commits, call AzDO REST API, set page order via `.order` files.
- Breaks: customer audience needs separate surface (AzDO seats for external users awkward/expensive); 18MB attachment cap; mediocre search ranking.
- Cost: ~€0 incremental (existing tenant). **Operational cost: low.**

**Architecture B — Obsidian Vault + Quartz/Publish for Audiences**
- Shape: Operator authors in Obsidian against git-backed vault. Quartz v4 (free, self-hosted) renders public-readable subset. Obsidian Publish ($10/mo) is paid alternative.
- Reads: operator (full vault, app), public/PM/customer (Quartz site, no login).
- Writes: operator only; agents can edit `.md` but no review/approval surface.
- Agents can: read vault as plain MD (perfect LLM-readability), commit via git — no API/SSO/audit.
- Breaks: no SSO, no per-audience ACL, weak audit. Devs without Obsidian have degraded experience. CI/agent push works but no PR-review affordance.
- Cost: Quartz ~free + DNS; Publish $10/mo. **Operational cost: medium** (Quartz pipeline, hosting).

**Architecture C — Hybrid (MD-in-repo SoT, mirrored to AzDO + Obsidian + MCP)**
- Shape: Single canonical MD in `homelab` (and 2 other repos). CI mirrors to AzDO Wiki on push. Operator's Obsidian vault is a git submodule / symlinked checkout of the same repo. MCP server exposes the same MD to Claude/Cursor for agents. Optional: Quartz for customer-facing read-only.
- Reads: operator (Obsidian, rich), PM/PO/devs (AzDO Wiki, SSO), customers (Quartz or excluded), AI agents (MCP).
- Writes: operator (Obsidian or any editor), agents (git push), CI (mirror jobs only — never originator).
- Agents can: read via MCP, write via git, validate via CI checks.
- Breaks: 3 surfaces = 3 places to drift. Mirror must be one-way (repo → AzDO) or you fight merge conflicts. Customer story still needs a decision.
- Cost: A's cost + Quartz hosting + ~1–2 days CI mirror setup. **Operational cost: medium-to-high**, but each piece independently replaceable (low lock-in).

**Decision axis for Step 6:** A optimizes for *shipping today* + audience reach via existing AAD. B optimizes for *operator thinking quality* but punts on multi-audience SSO. C optimizes for *not picking* — keeps git as ground truth, lets each audience use its native surface, but pays the mirror-pipeline tax.

---

#### C.6 Addendum — Karpathy's "LLM Wiki" Pattern (primary source)

*Source: Andrej Karpathy gist, https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f (retrieved 2026-04-27). [verified, primary source]*

**Correcting C.3:** the prior section concluded "no dominant project owns the name LLM-Wiki." That's still true at the *product* level — but at the **pattern** level, Karpathy's gist is the canonical reference. It defines a specific, named architectural pattern that maps almost 1:1 onto the homelab's existing stack and onto Architecture B / C above. Treat the gist as the **reference implementation spec** of LLM-Wiki going forward in this research.

##### Core idea (verbatim)

> The LLM **incrementally builds and maintains a persistent wiki** — a structured, interlinked collection of markdown files that sits between you and the raw sources. … Knowledge is compiled once and then *kept current*, not re-derived on every query.

> Obsidian is the IDE; the LLM is the programmer; the wiki is the codebase.

##### The three-layer architecture

| Layer | Role | Owner |
|---|---|---|
| **Raw sources** | Immutable curated documents (articles, papers, transcripts, images) | Human curates; LLM reads, never modifies |
| **The wiki** | LLM-generated markdown — entity pages, concept pages, summaries, comparisons, synthesis, index | **LLM owns entirely** (creates, updates, cross-refs, keeps consistent); human reads |
| **The schema** | A `CLAUDE.md` / `AGENTS.md` config that tells the LLM how the wiki is structured, conventions, and workflows for ingest/query/lint | Co-evolved by human + LLM |

##### The three operations

| Op | What it does |
|---|---|
| **Ingest** | New source → LLM reads, discusses takeaways, writes summary page, updates index, updates relevant entity/concept pages across the wiki, appends to log. *A single source might touch 10–15 wiki pages.* |
| **Query** | Question against the wiki → LLM searches relevant pages, reads, synthesizes answer with citations. **Good answers can be filed back into the wiki as new pages** — explorations compound, don't disappear into chat history. |
| **Lint** | Periodic health-check: contradictions between pages, stale claims newer sources have superseded, orphan pages, important concepts lacking pages, missing cross-refs, data gaps for web search. |

##### The two navigation primitives

| File | Type | Purpose |
|---|---|---|
| **`index.md`** | Content-oriented | Catalog of every page with link + 1-line summary + optional metadata (date, source count). Organized by category (entities/concepts/sources/etc.). LLM updates on every ingest. **At ~100 sources / hundreds of pages, index.md alone replaces RAG/embedding infrastructure.** |
| **`log.md`** | Chronological | Append-only record (ingests, queries, lints). Consistent prefix (e.g. `## [2026-04-02] ingest | Article Title`) makes it grep-able with unix tools. |

##### Tools Karpathy explicitly recommends

- **Obsidian** as the human-facing IDE; graph view as the "shape of the wiki" tool.
- **qmd** (https://github.com/tobi/qmd) — local BM25 + vector + LLM-rerank search over markdown, on-device, with both CLI (LLM shells out) and MCP server (LLM uses as native tool). [verified, by name in gist]
- **Obsidian Web Clipper** — browser → markdown into raw collection.
- **Dataview** — frontmatter-driven dynamic tables/lists across the vault.
- **Marp** — markdown-based slide decks (for synthesizing answers as presentations).
- **Wiki = git repo of MD** — version history, branching, collaboration for free.

##### Why this is operationally important for the homelab

| Karpathy's claim | Maps directly onto the homelab as |
|---|---|
| "Three layers: raw / wiki / schema" | Raw = `_bmad-output/`, sub-repos, ingested research, Slack/podcast/Obsidian-Clipper drops. Wiki = `/docs/` (and per-repo MD). Schema = existing **`CLAUDE.md`** at `/home/developer/workspace/homelab/CLAUDE.md` — already half the schema! |
| "LLM owns the wiki entirely" | Removes the BMAD-vs-non-BMAD divide: the LLM maintains the wiki on every session, not just inside BMAD workflows. Solves the "BMAD is sometimes not used" gap. |
| "Ingest / Query / Lint" trio | Maps onto: (a) Claude Code session-end hook (ingest — new sources from session), (b) `bmad-update-project-docs check`/`update` (query/lint), (c) periodic scheduled `lint` for contradictions and orphans. |
| "index.md + log.md replace RAG at moderate scale" | The homelab is at moderate scale today; you do **not** need to build vector indexing or RAG infra for the wiki itself. GitNexus and Graphiti remain orthogonal (live structure / temporal facts). |
| "Wiki is a git repo of markdown" | Already aligned. AzDO Wiki mirror, MCP-served MD, and Obsidian vault all read from the same git tree. |
| "Memex parallel — the missing piece was *who maintains it*; LLM solves that" | Direct answer to the user's stated goal: "implement a proper system or process or integration to document, and keep our documentation up to date." |

##### Implications for the three architectures (revised)

- **Architecture A (AzDO Wiki only)** — *Karpathy's pattern is portable to it but loses Obsidian's graph view, Dataview, and the `index.md` navigation flow.* AzDO Wiki has its own `[[_TOC_]]` and tree, which is functional but weaker than Obsidian's link graph. Loses operator cognition value.
- **Architecture B (Obsidian + Quartz/Publish)** — **This is exactly Karpathy's recommended shape.** Obsidian as IDE, vault as wiki, git as version control, schema in `CLAUDE.md`. Quartz handles the "publish to non-operator audiences" question without breaking the pattern.
- **Architecture C (Hybrid: MD-in-repo + AzDO + Obsidian + MCP)** — **Karpathy's pattern operates at the MD-source-of-truth layer.** AzDO Wiki and Quartz become read-only mirrors; Obsidian + Claude is the maintenance loop. MCP server exposes the same MD to other LLM clients (Cursor, Continue, future agents). Most aligned with the existing stack.

**Practical revision: Architecture C is now the strongest candidate.** It internalizes Karpathy's pattern (Obsidian as operator IDE, LLM as maintainer, MD-in-git as source-of-truth) **and** solves the multi-audience problem (AzDO Wiki for SSO-gated audiences, Quartz for public, MCP for agents). The mirror-pipeline tax is real but bounded: each mirror is a one-way CI job from a single canonical source.

##### Open question for Step 5/6

Karpathy explicitly says the schema (`CLAUDE.md`/`AGENTS.md`) is co-evolved per domain. The homelab already has a substantial `CLAUDE.md`. **Step 5 should produce: what additional sections need to be added to `CLAUDE.md` to encode the wiki schema (file layout, frontmatter conventions, ingest workflow, query workflow, lint workflow, index/log discipline)?** This is the load-bearing artifact that turns the LLM-Wiki pattern from idea into reproducible workflow.

---

#### C.7 Non-biased Comparison: LLM-Wiki Pattern vs Other Doc-System Patterns

*Self-correction: the prior section over-weighted Karpathy's pattern because the gist is recent, well-written, and cleanly maps to existing tools. Authority bias. This section forces an honest comparison and retracts the premature "Architecture C strongest" claim from C.6 — the answer depends on which axes the user cares about most.*

##### Karpathy's bake-in assumptions (state plainly before comparing)

The LLM-Wiki pattern is **explicitly framed for personal knowledge bases first**. Karpathy lists examples in this order: personal/health/journals → research deep-dives → book companions → business/team (acknowledged, not primary) → competitive analysis / hobbies. The pattern's DNA reflects that:

- **Single curator, single (or few) reader(s).** The human is *both* sourcing and consuming.
- **LLM owns the wiki entirely.** Human edits are the exception, not the norm — discouraged in the pattern.
- **Sources are external** (articles, papers, transcripts) → wiki is *derived synthesis*. The wiki is not a **collaboration artifact** with humans editing in parallel.
- **Operator-as-reader.** No multi-audience model. PM/customer/PO surfaces are not addressed in the gist.
- **No explicit review/approval.** No "PR review of doc changes" affordance. Trust the LLM's edits or correct in conversation.
- **Moderate scale** (~100 sources, hundreds of pages) where `index.md` replaces RAG. Above that, search infra (qmd) is needed.
- **Cost model unaddressed.** "Single source touches 10–15 pages" implies 10–15× LLM-edit cost per ingest. At commit-frequency or multi-source-batch scale this is non-trivial.
- **Hallucinated cross-refs / synthesis** is an unacknowledged failure mode. The LLM "kept current" can be the LLM "confidently wrong."

This is not a criticism of the pattern — it's an honest read of what the pattern was *designed for*. The homelab use case has overlap but also key differences (multi-audience, code-as-source-of-truth not just external articles, mixed BMAD/non-BMAD authoring).

##### Six patterns under comparison

| # | Pattern | One-line description |
|---|---|---|
| **P1** | **Traditional docs-as-code** | Humans write MD in `/docs`, Diátaxis IA, ADRs, manual updates, MkDocs Material renders. PR review on every doc change. *(Kubernetes / CNCF style.)* |
| **P2** | **BMAD-structured doc workflow** | The current homelab pattern: `bmad-document-project` (full scan), `bmad-update-project-docs` (incremental check/update). Manual triggers, git-diff drift detection. |
| **P3** | **DevOps Wiki workflow** | Humans write directly in AzDO / GitLab / GitHub Wiki via web UI. CI/agents minimally involved. SSO + audit out of the box. *(Enterprise / corp wiki style.)* |
| **P4** | **Knowledge-graph-only** | No markdown wiki. Graphiti / Mem0 / Neo4j hold all decisions and entities. Humans query the graph. *(Pure temporal-fact model.)* |
| **P5** | **RAG-over-MD chat UI** | MD is indexed, humans don't browse — they ask a chat bot. Continue.dev / Cursor `@docs` / hosted chat-doc tools. |
| **P6** | **Karpathy LLM-Wiki** | LLM owns wiki, ingest/query/lint, `index.md` + `log.md`, Obsidian as IDE. As specified in the gist. |

##### Comparison matrix (1–5 honest scoring)

| Axis | P1 docs-as-code | P2 BMAD | P3 DevOps wiki | P4 KG-only | P5 RAG chat | P6 LLM-Wiki |
|---|---|---|---|---|---|---|
| **Multi-audience suitability** (PM/customer/PO/dev) | 4 — render to site, IA serves audiences | 3 — same MD for all, no IA filtering | 5 — SSO + ACL out of box | 1 — humans can't browse a graph | 3 — chat works for non-tech if UX good | 2 — pattern is operator-first; multi-audience is bolted on |
| **Maintenance cost (steady state)** | 2 — humans drift, abandon | 3 — incremental help, still manual trigger | 2 — same drift problem as P1 | 4 — graph stays current if writes go through it | 4 — staleness is the index's problem, not yours | 5 — LLM does maintenance; that's the whole point |
| **Quality / drift reliability** | 4 — humans notice nuance | 4 — git-diff catches structural drift | 3 — humans drift quietly | 3 — graph drift is invisible | 3 — index lag = silent staleness | 3 — LLM hallucinated cross-refs, confidently-wrong synthesis are real failure modes |
| **Onboarding cost (new person)** | 5 — render, link, read | 4 — same | 5 — log in, browse | 1 — graph queries are not for newcomers | 3 — chat onboarding is fine, depth is shallow | 2 — newcomer needs to internalize the schema and operator workflow |
| **Time-to-first-useful-doc** | 1 — slowest, all human-written | 3 — BMAD scaffold helps | 2 — humans still write | 5 — already in graph if Graphiti was used | 4 — index any MD you have | 4 — LLM bootstraps fast |
| **Lock-in / portability** | 5 — pure MD | 4 — BMAD schemas, but MD is portable | 3 — wiki-specific MD extensions | 2 — Graphiti/Neo4j-specific | 3 — index format coupled to vendor | 5 — pure MD; schema is text |
| **LLM cost (steady)** | 5 — ~$0 | 5 — ~$0 except on update runs | 5 — ~$0 | 4 — Graphiti reads cost ~$0; writes cost something | 3 — every query costs tokens; index re-build costs more | 2 — every ingest touches 10–15 pages = expensive; lint passes are expensive |
| **Human cognitive load** | 2 — lots of writing | 3 — less writing, BMAD helps | 2 — lots of writing | 3 — graph thinking is a skill | 4 — just ask | 4 — curate sources + ask questions; LLM does grunt |
| **Verifiability / ground truth** | 5 — what's in the doc *is* the doc | 5 — same | 5 — same | 4 — graph is queryable, but synthesis is not pre-computed | 3 — answers vary per query; non-reproducible | 2 — synthesized pages can be wrong; provenance to source needs explicit citations |
| **Failure mode visibility** | 5 — drift visible in PR diff | 5 — drift report from `bmad check` | 4 — humans notice missing pages | 2 — silent | 2 — silent (stale index) | 3 — log.md helps; lint catches some; synthesis errors silent |
| **Multi-author / parallel writing** | 5 — PR review designed for it | 4 — same as P1 | 5 — wiki app handles it | 3 — graph writes need conflict policy | N/A | 1 — pattern assumes single curator; concurrent humans + LLM editing same page is a known weakness |
| **Fit with existing GitNexus** | 3 — no native wire-up | 3 — same | 3 — same | 4 — both are graph tools, complementary | 3 — could feed the index | 4 — GitNexus's `detect_changes` + `impact` map onto LLM-Wiki "ingest" trigger |
| **Fit with existing Graphiti** | 2 — orthogonal | 2 — same | 2 — same | 5 — *is* a Graphiti use case | 3 — Graphiti can feed index | 5 — Graphiti as ADR/decision provenance store, wiki as narrative; clean split |
| **Fit with existing BMAD** | 4 — BMAD outputs MD | 5 — *is* the current BMAD pattern | 3 — BMAD outputs need mirror to wiki | 2 — disjoint | 2 — same | 3 — BMAD-on / BMAD-off both work, but BMAD outputs need an "ingest" path into the wiki |
| **Scales beyond 100 sources** | 4 — depends on IA discipline | 4 — same | 5 — wiki engines built for it | 5 — graphs scale | 4 — RAG scales | 3 — `index.md` breaks at scale, then qmd or external search is needed |

**Aggregate read** (no axis is weighted equally — the *user* picks weights in synthesis):
- **P1 docs-as-code** wins on portability, verifiability, multi-author. Loses on maintenance cost.
- **P2 BMAD-structured** is "P1 with a fast-start scaffold." Same wins/losses, slightly better on first-doc time.
- **P3 DevOps wiki** wins on multi-audience SSO and onboarding. Loses on lock-in, drift quietly.
- **P4 KG-only** wins on time-to-first-useful and machine consumption. Loses on every human-facing axis.
- **P5 RAG chat** wins on cognitive load. Loses on verifiability and visibility.
- **P6 Karpathy LLM-Wiki** wins on **maintenance cost reduction** and operator cognitive load. Loses on **multi-author parallelism, verifiability, and steady-state LLM cost**. Bakes in a single-curator assumption.

##### Where the LLM-Wiki pattern *genuinely* beats alternatives

1. **The "who maintains it" problem.** P1, P2, P3 all hit the wall where humans abandon doc maintenance. P6 explicitly solves it. None of P1/P2/P3 do.
2. **Compounding synthesis.** P5 (RAG chat) re-derives every query; P6 builds a persistent artifact. For a domain you'll revisit (homelab is a multi-year domain), this is a real advantage.
3. **MD-in-git portability.** P3 and P5 lock you in. P6 stays portable.
4. **Operator cognition for the curator.** Obsidian + linked MD is a *thinking surface*, not just a doc surface. P1/P2/P3 are not thinking surfaces.

##### Where the LLM-Wiki pattern *loses* to alternatives

1. **Multi-audience SSO/ACL.** P3 wins outright. P6 has to bolt on a publish layer (Quartz + AzDO mirror).
2. **Multi-author / PR-review culture.** If multiple humans edit docs in parallel and want review-before-merge, P1 is purpose-built; P6 fights against its grain.
3. **Verifiability of synthesis.** P1's claim is "what the doc says is what someone wrote and reviewed." P6's claim is "what the doc says is what the LLM wrote based on sources" — provenance and review are weaker.
4. **Steady-state LLM cost.** Free vs ~$X/month. At low source-volume this is irrelevant; at scale it matters.
5. **Failure mode: confidently-wrong synthesis.** P6 has a unique failure mode: a clean, well-written wiki page that's subtly wrong because the LLM stitched two sources poorly. P1 has the same risk for human writers but humans-being-wrong is more discoverable than LLM-being-wrong (which reads authoritatively).

##### Honest verdict

- **No pattern is universally best.** P6 is best *if* the binding constraint is maintenance cost; P3 is best *if* multi-audience SSO is binding; P1 is best *if* verifiability and PR-review are binding.
- **For this user's stated constraints** (multi-audience including PM/customer, BMAD-on/BMAD-off mix, source-of-truth in markdown, GitNexus + Graphiti already wired): the honest read is that **no single pattern fits all audiences and all triggers**. The user must either:
  - Pick one pattern and accept its losses (single-pattern, simpler ops).
  - Compose patterns at different layers — e.g., P6 for *operator/dev/AI-agent* layer + P3 for *PM/customer* layer + P2 for *BMAD-gated* layer, all sharing one MD source-of-truth. (Architecture C is essentially this composition.)
- **Retracting the C.6 claim:** "Architecture C is now the strongest candidate" was premature. Architecture C is the *most-composed* candidate, but composition costs (3 surfaces, 3 drift risks, 1–2 days CI mirror setup, ongoing pipeline maintenance, LLM-Wiki ingest/lint costs). Architecture A (AzDO Wiki only, P3 pattern) is genuinely viable and has the lowest steady-state cost. **Architecture B (Obsidian + Quartz + LLM-Wiki) is genuinely viable** if non-tech audiences are de-prioritized or pushed to a Quartz-rendered subset.

##### Decision axes (carry into Step 6)

The right pick depends on which axis dominates for the user:

1. **"I want PMs/customers to read this without friction"** → P3 / Architecture A is the honest answer.
2. **"I want my own thinking + the LLM to do maintenance work, audience secondary"** → P6 / Architecture B.
3. **"I want one source-of-truth and each audience gets its native surface, and I'll pay the composition tax"** → P6+P3 / Architecture C.
4. **"I want the lowest possible LLM cost and don't mind writing docs myself"** → P1 / MkDocs Material + Diátaxis on the existing `/docs/`.
5. **"I'm not sure my docs need to be browsed at all — agents and chat are enough"** → P5 / RAG-over-MD with no public site.

The synthesis step (Step 6) will need the user's pick on this axis to commit. Step 3, 4, 5 will continue to research integration patterns, architectural patterns, and implementation tools that work across multiple of these axes — keeping options open.

---

#### C.8 Claude-Code-Oriented Documentation — OSS Landscape (verified 2026-04-27)

*All star counts and recency from live GitHub fetches on 2026-04-27.*

##### Curated lists & indexes

| Repo | Stars | Status |
|---|---|---|
| `hesreallyhim/awesome-claude-code` | **41.5k** | Active but flooded — 266 open issues, "update in progress" banner; curation can't keep up |
| `langgptai/awesome-claude-code` | n/a | **404 / abandoned** |
| `wshobson/agents` | **34.4k** | Most active large-collection repo; tracks Anthropic's "2–8 components per plugin" guidance; 184 agents / 16 orchestrators / 150 skills |
| `disler/claude-code-hooks-mastery` | **3.6k** | Pedagogical example repo — all 13 hook lifecycle events with worked examples; high signal-to-noise |
| `anthropics/claude-cookbooks` | **41.7k** | **Claude API only — NOT Claude Code.** Frequently mis-cited |
| `anthropics/skills` | **125k** | **Canonical SKILL.md schema source.** Small (31 commits), official, includes Document Skills (PDF/DOCX/etc.) |
| `PatrickJS/awesome-cursorrules` | **39.3k** | Cross-pollination value — same conceptual layout as CLAUDE.md, more mature ecosystem |
| `VoltAgent/awesome-claude-code-subagents` | **18.5k** | Active, narrower scope than `wshobson/agents` |
| `travisvn/awesome-claude-skills` | **11.9k** | Skills-specific (post-Oct 2025 official launch); 328 open PRs (curation backlog) |

**Headline:** `wshobson/agents` and `anthropics/skills` are the two ground-truth repos. Awesome-lists are useful for discovery but suffer typical curation lag.

##### CLAUDE.md / AGENTS.md exemplars in popular OSS

| Repo | Stars | Approach | Length |
|---|---|---|---|
| `astral-sh/uv` | **84k** | `CLAUDE.md` = single line `@AGENTS.md`; AGENTS.md is canonical | ~1 line + AGENTS.md |
| `astral-sh/ruff` | **47.3k** | Same Astral pattern (CLAUDE.md → AGENTS.md redirect) | ~1 line |
| `pulumi/pulumi` | **25.1k** | Both files present; dual-schema declaration | mid |
| `dagger/dagger` | **15.7k** | AGENTS.md only — **38 lines**, philosophy + commit hygiene | 38 |
| `temporalio/temporal` | **19.9k** | AGENTS.md ~104 lines — forbid-lists tied to lint gates (no `time.Sleep` in tests, must pass `make lint-code`) | 104 |
| `cline/cline` | **61.1k** | **Manifest pattern**: CLAUDE.md is 3 lines pointing to `.clinerules/general.md`, `.clinerules/network.md`, `.clinerules/cli.md`, `.agents/skills/` | 3 + topic-split |
| `sst/opencode` | **151k** | AGENTS.md only (vendor-neutral, even with heavy Claude usage) | mid |
| `ruvnet/claude-flow` (rebranded to `ruflo` v3.5.80; same project) | **33.7k** | **CLAUDE.md = 1,094 lines** + `CLAUDE.local.md`; behavioral rules + file org + V3 CLI ref (~140 subcommands) + 60+ agent types + hooks. **Past the threshold where a single file helps an agent.** | 1094 |
| `anthropics/claude-code` | **118k** | **Ships ZERO CLAUDE.md / AGENTS.md.** Uses `.claude/commands/`, `.claude-plugin/`, external docs at `code.claude.com/docs` | 0 |
| `continuedev/continue` | **32.8k** | No root file; `.continue/checks/*.md` as **enforceable CI rules** (markdown-as-policy) | distributed |
| `Aider-AI/aider` | **44k** | None — pre-AGENTS.md design, README + repo-map + commit hygiene | 0 |
| `fastapi/fastapi` | **97.7k** | None — type hints + OpenAPI auto-gen as implicit AI-readability | 0 |

**Direct call-out for the homelab:** `ruvnet/claude-flow` (rebranded to `ruflo` v3.5.80; same project) (which the homelab uses) ships the **worst-in-class** example — 1,094-line CLAUDE.md. The homelab's own root `CLAUDE.md` is currently substantial and trending toward the same anti-pattern. **Astral's `@AGENTS.md` redirect** or **Cline's manifest + topic-split** are the proven alternatives.

##### Karpathy LLM-Wiki implementations (gist published 2026-04-04, 5k+ forks)

| Repo | Stars | What it ships |
|---|---|---|
| `lucasastorian/llmwiki` | **700** | Most-starred concrete impl — MCP-based, points at folder, Claude writes wiki |
| `Pratiyush/llm-wiki` | **177** | **Best-engineered** — converts `.jsonl` session transcripts → static HTML wiki, 16 lint rules, MCP server with 12 tools, stdlib-only Python |
| `MehmetGoekce/llm-wiki` | **74** | Two-layer cache (L1 rules / L2 wiki), Logseq + Obsidian. Honest about Karpathy gaps |
| `kfchou/wiki-skills` | **100** | Skill bundle: `wiki-init`, `wiki-ingest`, `wiki-query`, `wiki-lint`, `wiki-update` — conceptually clean, minimal proof-of-life |
| `Astro-Han/karpathy-llm-wiki` | low | Cross-tool ambition (Claude/Cursor/Codex) |

**Verdict on Karpathy implementations:** Real but young — gist is only ~3 weeks old. None has crossed 1k stars. Treat as **reference implementations to study, not battle-tested tooling**. `Pratiyush/llm-wiki` and `kfchou/wiki-skills` are worth studying for their command shapes (`init`/`ingest`/`query`/`lint`/`update`).

##### Auto-doc generators / schema scaffolders

| Repo | Stars | Verdict |
|---|---|---|
| `agentsmd/agents.md` (spec authority) | **20.7k** | The AGENTS.md spec source — vendor-neutral, sections: Testing, Dev Env, PR conventions, Code Style |
| `levnikolaevich/claude-code-skills` | **432** | Ships `documentation-pipeline` plugin — generates root docs, ADRs, runbooks, API specs via coordinated workers. Production-shaped |
| `avinshe/agentseed` | **59** | `npx agentseed init` scaffolds AGENTS.md + CLAUDE.md + .cursorrules from codebase scan |
| Various sub-100-star generators | — | Mostly boilerplate output; human curation still load-bearing |

##### llms.txt ecosystem

| Repo | Stars | Notes |
|---|---|---|
| `AnswerDotAI/llms-txt` | **2.3k** | **Spec source.** H1 title + blockquote summary + H2 file-list with markdown links. Adopters: FastHTML, all nbdev, Answer.AI, fast.ai |
| `thedaviddias/llms-txt-hub` | **815** | Largest directory of `llms.txt` adopters — discovery, not spec |

##### Patterns worth lifting (with best-demo repo per pattern)

1. **Stub-redirect for cross-tool compat.** `CLAUDE.md` = `@AGENTS.md`; real content in vendor-neutral AGENTS.md. **Best demo:** `astral-sh/uv`, `ruff`, `pulumi`. Single source of truth, both Anthropic and OpenAI Codex find it.
2. **Manifest + topic-split.** Top-level CLAUDE.md = 3–10 line pointer into `.clinerules/<topic>.md` or `.claude/rules/<topic>.md`. **Best demo:** `cline/cline`. Stops single-file sprawl; lets agents load only the relevant slice.
3. **Tight forbid-lists tied to lint gates.** AGENTS.md as a pre-flight checklist (38–104 lines), not a tutorial. **Best demo:** `temporalio/temporal`, `dagger/dagger`.
4. **Skill-as-folder with YAML frontmatter.** `SKILL.md` with required `name` + `description` frontmatter, plus optional `workflow.md` / `steps/`. **Best demo:** `anthropics/skills` (canonical) + `bmad-code-org/BMAD-METHOD`.
5. **Karpathy three-layer wiki: raw / wiki / schema.** **Best demo:** `Pratiyush/llm-wiki` (engineering), `MehmetGoekce/llm-wiki` (cleanest L1/L2 split), `kfchou/wiki-skills` (command shapes).
6. **`/llms.txt` at site root + `.md` shadow URLs.** Curated H2 index pointing to canonical doc paths. **Best demo:** AnswerDotAI spec + nbdev's automatic `.md` generation.
7. **Markdown-as-policy in CI.** Agent-readable rules become CI checks (`.continue/checks/*.md`). **Best demo:** `continuedev/continue`. Closes the loop between "docs the agent reads" and "rules the agent must satisfy."
8. **Dual-schema declaration.** Ship both `AGENTS.md` and `CLAUDE.md` (one as stub) so cross-tool teams aren't forced to choose. **Best demo:** Astral repos, Pulumi.

##### Anti-patterns observed

- **The 1,000+ line CLAUDE.md.** `ruvnet/claude-flow` (rebranded to `ruflo` v3.5.80; same project) ships the worst-in-class — single file mixes behavioral rules, file org, full CLI reference, and 60+ agent definitions. Agents skim, humans don't reread, edits create merge conflicts. **The homelab's stack inherits this risk.**
- **CLAUDE.md as marketing copy.** Long prose narrative with no enforceable rules — agents waste tokens, get no guidance.
- **Awesome-list curation collapse.** Pattern doesn't scale past ~6 months without paid maintenance.
- **Trivial AGENTS.md generators.** Output starter scaffolds with no project-specific signal — pure boilerplate.
- **Karpathy fork-as-star inflation.** 5k+ forks within days, but real implementations cluster at 60–700 stars. Many forks are bookmarks, not implementations.
- **Anthropic itself ships no CLAUDE.md.** Either deliberate signal that the file convention isn't load-bearing, or a gap. Worth noting before assuming the schema is universal.
- **Cookbooks ≠ Code patterns.** `anthropics/claude-cookbooks` (41.7k stars) is API-only, frequently mis-cited as a Claude Code resource.

##### Direct implications for the homelab

1. **Audit the existing root `CLAUDE.md`.** Length-check it against the 100–150 line sweet spot (Temporal/Dagger range) vs the 1,094 line claude-flow anti-pattern. Refactor candidates: Astral stub-redirect, Cline manifest split, or Temporal-style forbid-list reduction.
2. **Adopt `AGENTS.md` alongside `CLAUDE.md`** for cross-tool portability (Cursor, Codex, future agents). Astral pattern is the cheapest implementation.
3. **Study `Pratiyush/llm-wiki` and `kfchou/wiki-skills`** as concrete LLM-Wiki implementations before designing the homelab's version — their `init/ingest/query/lint/update` command shapes are good defaults.
4. **Consider `levnikolaevich/claude-code-skills` documentation-pipeline plugin** as a candidate to lift or fork rather than build from scratch.
5. **`/llms.txt` is cheap to add** — at the seam between the homelab and any future hosted doc site (Quartz / static), a curated H2 index makes the wiki queryable by external LLM clients without rebuilding.
6. **`.continue/checks/*.md` markdown-as-policy** is a useful pattern to translate into Claude Code hooks — agent rules expressed as markdown that CI also enforces.

##### Sources
- https://github.com/wshobson/agents
- https://github.com/anthropics/skills
- https://github.com/hesreallyhim/awesome-claude-code
- https://github.com/disler/claude-code-hooks-mastery
- https://github.com/astral-sh/uv (CLAUDE.md, AGENTS.md)
- https://github.com/astral-sh/ruff (CLAUDE.md)
- https://github.com/dagger/dagger (AGENTS.md)
- https://github.com/temporalio/temporal (AGENTS.md)
- https://github.com/cline/cline (CLAUDE.md)
- https://github.com/sst/opencode
- https://github.com/ruvnet/claude-flow (CLAUDE.md)
- https://github.com/anthropics/claude-code
- https://github.com/continuedev/continue
- https://github.com/Aider-AI/aider
- https://github.com/agentsmd/agents.md
- https://github.com/AnswerDotAI/llms-txt
- https://github.com/thedaviddias/llms-txt-hub
- https://github.com/bmad-code-org/BMAD-METHOD
- https://github.com/aj-geddes/claude-code-bmad-skills
- https://github.com/lucasastorian/llmwiki
- https://github.com/Pratiyush/llm-wiki
- https://github.com/MehmetGoekce/llm-wiki
- https://github.com/kfchou/wiki-skills
- https://github.com/levnikolaevich/claude-code-skills
- https://github.com/avinshe/agentseed

---

### C.9 GitNexus Code Wiki — direct evaluation (verified 2026-04-27)

*Verified by: local CLI (`docker exec gitnexus node /app/gitnexus/dist/cli/index.js wiki --help` and `analyze --help`) + GitHub README at `github.com/abhigyanpatwari/GitNexus`.*

User flagged this section: GitNexus's marketing copy advertises "**Auto-updating Code Wiki – always up-to-date documentation (Code Wiki is also available in OSS)**." Direct verification clarifies the OSS / Enterprise split and the actual capability shape.

#### C.9.1 What it is — direct CLI capabilities

Three documentation-related sub-commands, all in the OSS package (`gitnexus` v1.6.3, license **PolyForm-Noncommercial-1.0.0** — free for the homelab's non-commercial use; commercial use requires separate licensing):

| Command | What it does |
|---|---|
| `gitnexus analyze` | Builds the knowledge graph. **By default, injects a "gitnexus section" with stats into `AGENTS.md` and `CLAUDE.md`.** Flags: `--skip-agents-md` (opt out of AGENTS.md/CLAUDE.md mutation), `--no-stats` (omit volatile counts), `--skills` (also generate skills, see below), `--embeddings` (semantic search). |
| `gitnexus wiki` | Reads the indexed graph, **groups files into modules via LLM, generates per-module documentation pages + overview**, with cross-references to the knowledge graph. Requires LLM API key (OpenAI / Cursor / Azure). Default model `minimax/minimax-m2.5`. Concurrency 3. `--review` stops after grouping for human review of module structure. `--gist` publishes as public GitHub Gist. |
| `gitnexus analyze --skills` | Detects functional areas via **Leiden community detection** and **generates `SKILL.md` files at `.claude/skills/generated/`** — one per community, describing key files, entry points, execution flows, cross-area connections. |

#### C.9.2 OSS vs Enterprise — the actual split

Quoted from the GitNexus README:

- **OSS:** `wiki` command exists and works. **Wiki generation is manual** — invoke `gitnexus wiki` to regenerate.
- **Enterprise:** "**Auto-updating** Code Wiki — always up-to-date documentation". The *automation* (continuous regeneration on changes) is the enterprise feature; the wiki capability itself ships in OSS.
- **Commercial-licensing path:** "available as fully managed SaaS or self-hosted deployment" via `founders@akonlabs.com`. PolyForm-NC blocks commercial use of OSS without licensing.

**For this homelab:** the OSS Code Wiki is fully usable. The "auto-updating" gap is solvable with **a Claude Code SessionEnd hook or scheduled cron that calls `gitnexus wiki`** — i.e., recreating the enterprise feature in shell.

#### C.9.3 Local state on the homelab

- **No `.gitnexus/` index directory** at homelab root → `analyze` hasn't been run on the top-level workspace; the GitNexus daemon at `127.0.0.1:4747` likely indexes per-repo (homelab-playbook, homelab-infra, homelab-apps separately).
- **Existing post-commit hook** (`/home/developer/.claude/hooks/gitnexus/post.sh`) calls `gitnexus analyze --skip-agents-md` on every `git commit` — so reindex is auto, but AGENTS.md/CLAUDE.md mutation is explicitly disabled (per E2-S05 carry-over noted in the script).
- **No `.claude/skills/generated/`** dir → `analyze --skills` has not been opted in.
- **Two on-disk wiki scaffolds exist** but are **test layouts, not adopted production wikis** (per user clarification 2026-04-27 — exclude from "current state" baseline):
  - `homelab-playbook/wiki/` — Diátaxis-shaped scaffold (test).
  - `homelab/wiki/` — Karpathy three-layer scaffold (test).

#### C.9.4 Where it fits in the comparison

GitNexus Code Wiki is **a code-graph-driven reference-doc generator**, not a full doc system. Honest mapping:

| Diátaxis quadrant | Can GitNexus Code Wiki cover it? |
|---|---|
| **Reference** (per-module API/structure docs) | ✅ Strong — direct from knowledge graph, low hallucination because grounded in AST/community detection |
| **Tutorials** (learning) | ❌ No — narrative is not in the graph |
| **How-to** (task-oriented) | ❌ No — operator runbooks are not derivable from code |
| **Explanation** (understanding/why) | ⚠️ Partial — module overviews are LLM-synthesized, but *why* decisions were made lives in Graphiti and BMAD outputs |

**Treat GitNexus Code Wiki as an *ingest source* into the wiki layer, not the wiki itself.** It produces high-quality reference docs and SKILL.md files; it does not produce ADRs, runbooks, tutorials, business docs, or PM-facing narrative.

#### C.9.5 Comparison matrix — adding GitNexus Code Wiki

Extending the matrix from §C.4 with one new column:

| Axis | GitNexus Code Wiki (OSS) |
|---|---|
| **Audience reach** | 3 — generated MD readable anywhere; per-module pages opaque to non-tech audiences |
| **Authoring (op + agents)** | 5 — fully automated from graph; zero manual writing for reference layer |
| **LLM-readability** | 4 — pure markdown output |
| **Drift detection** | 5 — graph itself drifts forward on every commit (OSS reindex via post-commit hook); wiki regen catches up |
| **Git-as-SoT** | 4 — graph is derived from git; wiki output can be committed back |
| **Op cost** | 3 — LLM cost per regen (full repo at concurrency 3); auto-updating is enterprise-only |
| **Lock-in** | 3 — PolyForm-NC license; single maintainer; commercial use blocked |
| **Multi-repo aggregation** | 4 — `group` subcommand exists for cross-repo impact; same daemon serves all indexed repos |
| **Hallucination risk** | 4 — LLM still synthesizes module-level prose, but cross-refs are graph-grounded → **lower than free-form LLM-Wiki synthesis** |
| **Coverage** | 2 — reference layer only; misses tutorials/how-tos/explanation/decisions |

#### C.9.6 Implications — does GitNexus Code Wiki change Architecture C?

Yes, materially. **It becomes the right tool for the *reference* layer of Diátaxis**, replacing manual maintenance of per-repo architecture / source-tree / module docs that BMAD's `bmad-document-project` currently generates.

Revised Architecture C source-flow (C.5 update):

```
                                       ┌───────────────┐
GitNexus knowledge graph (auto reindex) ─→  REFERENCE   │
   │                                   │     LAYER      │
   ├─ analyze --skills → .claude/skills/generated/      │
   ├─ wiki → /docs/reference/<module>.md                │
   │                                                     │
Graphiti episodes ────────────────────→ │  EXPLANATION   │
   ├─ "why" decisions, ADR provenance  │     LAYER      │
   │                                                     │
BMAD outputs (PRDs, ADRs, retros) ────→ │  EXPLANATION   │
   ├─ formal artifacts, business intent │ + TUTORIALS   │
   │                                                     │
Operator authoring (Obsidian) ────────→ │  HOW-TO       │
   ├─ runbooks, procedures, troubleshooting              │
   │                                                     │
External `raw/` sources ──────────────→ │  HOW-TO /     │
   ├─ articles, transcripts, external docs               │
                                       └───────┬───────┘
                                               │
                                               ▼
                                   /docs/ — single MD source-of-truth
                                               │
                            ┌──────────────────┼──────────────────┐
                            ▼                  ▼                  ▼
                       Obsidian          AzDO Wiki mirror      Quartz site
                       (operator)         (PM/PO/devs)         (public, opt.)
                                                ▼
                                          MCP server
                                          (AI agents)
```

**Practical consequence:** the homelab can **stop manually maintaining the per-repo architecture docs** that `bmad-document-project` generated on 2026-04-02 (`architecture-homelab-infra.md`, `architecture-homelab-apps.md`, `architecture-homelab-playbook.md`, `source-tree-analysis.md`). Replace those with `gitnexus wiki` regeneration. Keep BMAD for narrative artifacts (PRDs, retros, research, ADRs), Graphiti for decision provenance, and operator authoring for runbooks.

#### C.9.7 Risks specific to GitNexus Code Wiki

- **Single-maintainer dependency.** `abhigyanpatwari/GitNexus` is a one-person project today. Bus-factor risk; mitigated by the OSS license keeping the existing version usable indefinitely.
- **PolyForm-NC license.** **Sparkle-CPS work is commercial** — using GitNexus Code Wiki on the Sparkle-CPS codebase requires commercial licensing. Homelab itself is non-commercial = clean.
- **AGENTS.md/CLAUDE.md mutation by default.** Existing `--skip-agents-md` flag in the post-commit hook is correct — keep it on. Do not let GitNexus inject stats sections that fight the Astral / Cline patterns proposed in §C.8.
- **LLM cost on full regen.** Mitigate by `--review` to gate module structure changes; only regen modules whose graph delta exceeds a threshold (custom wrapper).
- **Module structure may not match human IA.** Leiden communities are mathematically detected, may produce groups that don't match the user's mental model. The `--review` flag is the manual override.

#### C.9.8 Action item

**Suggested test:** run `gitnexus wiki --review` against `homelab-playbook` (smallest of the three repos, where the BMAD doc baseline is already current) to evaluate the actual output quality before committing to the integration. ~5 min wall-clock + small LLM bill. Compare side-by-side with `architecture-homelab-playbook.md` (the existing BMAD-generated equivalent) to assess fitness.

---

## Integration Patterns Analysis

*Adapted from the generic API/microservices template to the actual integration concerns of a documentation system. Focus: triggers, source-flow, consumption fan-out, cross-tool schema, hook lifecycle, conflict resolution, provenance, failure modes.*

### 3.1 Trigger Integration — when do doc updates fire?

Five distinct trigger sources, each with different latency, cost, and reliability tradeoffs:

| Trigger | Latency | LLM cost | Reliability | Best for |
|---|---|---|---|---|
| **Pre-commit hook** (git) | seconds | per-commit (small) | high (gates the commit) | Lint/link/policy checks; **not** narrative updates (slows down commits) |
| **Post-commit / push CI** (GitHub Action / GitLab CI) | minutes | per-push | high | Full ingest of changed paths into wiki; mirror jobs |
| **Claude Code SessionEnd hook** | seconds at session-close | per-session | medium (fires only when Claude is used) | Karpathy "ingest" — capture session learnings into wiki + log.md |
| **BMAD story-done gate** | manual at story completion | per-story | high *when used* — the user's stack is mixed BMAD/non-BMAD | PRD/ADR/architecture sync into wiki |
| **Scheduled (cron / scheduled remote agent)** | weekly/daily | per-run | very high (independent of human action) | Karpathy "lint" — contradiction-check, orphan detection, drift report |
| **Manual (current homelab)** | on-demand | low | low (relies on operator memory) | Bootstrap, full re-scan |

**Recommended hybrid (minimum viable):** SessionEnd (cheap session-ingest) + scheduled weekly lint (catches drift) + post-commit CI (lint/link/mirror). BMAD story-done becomes additive when BMAD is in use. Pre-commit stays narrow (lint + policy only — no LLM in the commit path).

### 3.2 Source-Flow Integration — what feeds into the wiki?

| Source | API / mechanism | Ingest path |
|---|---|---|
| **Code changes** | GitNexus `mcp__gitnexus__detect_changes` + `impact` | "These code paths changed → these wiki pages depend on them" — agent updates affected pages |
| **Decisions / temporal facts** | Graphiti `mcp__graphiti__add_memory` (writer) + `search_memory_facts` (reader) | Agent reads recent episodes/facts on session-start; cited in wiki frontmatter as `provenance: graphiti://<episode-uuid>` |
| **Operator learnings** | Claude auto-memory (`~/.claude/projects/<project>/memory/`) | Already-validated facts; promote runbook-shaped entries into the wiki on `lint` pass |
| **BMAD outputs** | `_bmad-output/` directory + BMAD skill outputs | Each PRD / ADR / retro / research artifact triggers an ingest event; mapped into Diátaxis quadrants |
| **External sources** | Obsidian Web Clipper / drag-into-`raw/` / curl into `raw/` | Karpathy "raw sources" layer — immutable, agent reads but never modifies |

**Source-of-truth split (formalized):**
- **GitNexus** = live code structure (queries, never duplicated into MD).
- **Graphiti** = temporal decision facts (queries on session-start; cited, not duplicated).
- **Auto-memory** = operator-only working notes (promoted to wiki on lint).
- **BMAD outputs** = formal artifacts (PRDs, ADRs, retros) — first-class ingest source.
- **Wiki MD** = narrative + synthesis layer (the Karpathy "wiki" layer).
- **`raw/`** = immutable external sources.

### 3.3 Consumption Fan-out Integration — who reads the same MD?

A single MD source-of-truth in git fans out to multiple consumption surfaces:

| Consumer | Read mechanism | Format expected |
|---|---|---|
| **Operator** | Obsidian (filesystem on git-backed vault) | Raw `.md` with `[[wikilinks]]`, frontmatter, mermaid blocks |
| **PM / PO / Devs (SSO-gated)** | Azure DevOps Wiki via mirror to `wikiMaster` branch | CommonMark + AzDO extensions (`[[_TOC_]]`, mermaid) — Astral mirror pattern |
| **Customers / public** *(if scoped in)* | Quartz v4 static site (subset of vault published) | HTML; raw `.md` optionally exposed alongside |
| **AI agents (Claude / Cursor / Continue)** | MCP server (`docs-mcp-server` or similar) + `/llms.txt` at site root | Pure markdown, AnswerDotAI llms.txt spec |
| **CI (lint / link-check / drift)** | Direct file access | Raw `.md` |

**Critical integration constraint:** consumption is **read-only fan-out** from a single SoT (the git repo). Mirror pipelines are **one-way**; if any consumer becomes a writer, you fight merge conflicts. Confirmed against `git as SoT` in §C.5 Architecture C.

### 3.4 Cross-Tool Schema Integration — CLAUDE.md / AGENTS.md / .cursorrules / .continue/checks

Schema files (the "instruction layer for AI agents reading the codebase") proliferate per-tool. Real OSS projects converge on three patterns (per §C.8):

| Pattern | Mechanism | Best for |
|---|---|---|
| **Astral stub-redirect** | `CLAUDE.md` = single line `@AGENTS.md`; AGENTS.md is canonical | Cross-tool teams that don't want to choose Anthropic vs Codex |
| **Cline manifest + topic split** | `CLAUDE.md` (3 lines) → `.claude/rules/<topic>.md` files | Long-rule codebases; lets agents lazy-load relevant slices |
| **Temporal forbid-list** | 38–104 lines of pre-flight rules tied to lint gates | Codebases with strict invariants; pairs with CI |

**Compatibility with Claude Code's `InstructionsLoaded` hook:** Cline's manifest pattern integrates cleanly — each `.claude/rules/*.md` lazy-load fires its own `InstructionsLoaded` event, allowing per-rule learning hooks. Single-file 1k-line CLAUDE.md (claude-flow / ruflo anti-pattern) only fires once at session start, hard to instrument.

### 3.5 Claude Code Hook Lifecycle — the integration backbone

*Verified 2026-04-27 against https://code.claude.com/docs/en/hooks*

The hook events most relevant to a documentation system, mapped to Karpathy's ingest/query/lint trio:

| Hook event | Doc-system role | Karpathy op |
|---|---|---|
| **SessionStart** | Load wiki schema; surface "docs may be stale" if `bmad-update-project-docs check` shows drift | (priming) |
| **InstructionsLoaded** | Confirm CLAUDE.md / AGENTS.md / `.claude/rules/<topic>.md` schema is in context; log which slices loaded | (priming) |
| **UserPromptSubmit** | Detect decision-making prompts ("we decided …", "let's go with …") → suggest ADR draft | (ingest signal) |
| **PreToolUse** | Gate edits to `/docs/` source (enforce frontmatter, owner field, log entry) | (write-time validation) |
| **PostToolUse** (`Edit`/`Write` matcher on `/docs/**`) | Append entry to `log.md`; trigger downstream lint | **ingest** |
| **PostToolBatch** | Batch-flush `log.md` updates after a session of doc edits | **ingest** |
| **SubagentStop** | Capture researcher subagent outputs as candidate `raw/` ingests | **ingest** |
| **TaskCompleted** | Universal "story-done" — fires for both BMAD and non-BMAD work; trigger Karpathy ingest of session deltas | **ingest** |
| **FileChanged** (matcher on `/docs/**`, `_bmad-output/**`) | Detect external edits (humans editing in Obsidian outside Claude) → reconcile on next session | (drift signal) |
| **PreCompact** | Persist any pending wiki edits to `log.md` before context loss | (durability) |
| **PostCompact** | Reload wiki schema; reset session-ingest counter | (recovery) |
| **SessionEnd** | **Primary ingest trigger** per Karpathy — synthesize session learnings into wiki, append to `log.md`, optionally trigger CI mirror to AzDO | **ingest** |
| **Stop** | Lightweight turn-end — useful for incremental log entries without full ingest | (partial ingest) |

**Existing homelab hook wiring** (`~/.claude/settings.json`): GitNexus has hooks on `PreToolUse: Grep|Glob` and `PostToolUse: Bash`. The doc system would add hooks on `PostToolUse: Edit|Write`, `SessionEnd`, and `TaskCompleted` — non-overlapping with existing wiring.

**Reference example:** `disler/claude-code-hooks-mastery` (3.6k stars) implements all 13 hook events with worked scripts; suitable as a template for the doc-system hooks.

### 3.6 Conflict-Resolution Integration — humans + agents editing the same MD

Karpathy's "LLM owns the wiki entirely" assumption breaks when multiple humans edit, when humans review agent edits, or when BMAD and non-BMAD workflows produce parallel updates. Patterns:

| Pattern | Mechanism | Tradeoff |
|---|---|---|
| **Owner-tagged sections** | Frontmatter `owner: llm` vs `owner: human`; agents only edit `owner: llm` sections | Discipline-dependent; sections drift across owners |
| **Append-only `log.md`** | Karpathy primitive — chronological, never edited | No merge conflicts ever; downside: log grows unbounded (rotate annually) |
| **Wiki-bot branches** | Agents push to `wiki-bot/<date>` branches → auto-PR → operator merges | Adds PR-review affordance; slows ingest by review latency |
| **Human-write-window lock** | `.docs-lock` file present → agents skip edits | Simple; manual lifecycle |
| **CRDT / per-paragraph attribution** | Heavyweight (Yjs / Automerge) | Overkill for a homelab |

**Recommended for the homelab:** combine *append-only log.md* (always safe) + *owner-tagged sections in frontmatter* (sane default) + *wiki-bot branches with auto-PR for non-trivial changes* (review affordance). Skip CRDT.

### 3.7 Provenance / Citation Integration

Synthesized wiki content must trace back to sources, otherwise the LLM-Wiki failure mode (confidently-wrong synthesis) becomes invisible. Concrete pattern:

```yaml
---
owner: llm
last_ingested: 2026-04-27
sources:
  - graphiti://episode/3f9a-...
  - file://homelab-infra/terraform/main.tf:84-120
  - file://homelab-apps/CONFIGURATION.md
  - bmad://_bmad-output/planning-artifacts/research/technical-pve3-storage-architecture-research-2026-04-20.md
  - external://https://docs.proxmox.com/ha-manager/  (retrieved 2026-04-23)
ingest_log: log.md#2026-04-27-ingest-pve3-storage-research
contradictions: []
---
```

Reasoning:
- `graphiti://` URIs cite temporal episodes — when agents synthesize "we decided X", they link to the Graphiti episode that recorded it. Resolves on read via `mcp__graphiti__get_entity_edge`.
- `file://` paths with line ranges cite code; resolvable via GitNexus `route_map`.
- `bmad://` paths cite BMAD outputs (PRDs, ADRs, research artifacts).
- `external://` cites web sources with retrieval date.
- `ingest_log` cross-links into `log.md` for the audit trail.
- `contradictions: []` is populated by the `lint` pass when newer sources contradict older claims.

### 3.8 Failure-Mode Integration — what happens when each integration breaks?

| Failure | Symptom | Fallback / mitigation |
|---|---|---|
| **GitNexus down** | `detect_changes` MCP timeouts | Fall back to `git diff --name-only HEAD~10` for ingest path detection; existing 3-second hook timeout already protects against hangs |
| **Graphiti down** | Provenance citations fail to resolve | Wiki still readable (cited URIs are stable strings); session-end ingest skips Graphiti enrichment, queues for retry |
| **Hooks misfire / timeout** | `log.md` entries missed | Scheduled lint pass detects gaps (compares git log of `/docs/` vs `log.md` entries) and back-fills |
| **Mirror to AzDO Wiki fails** | AzDO wiki goes stale | Existing crash-notifier pattern (`scripts/crash-notifier`) already handles ntfy alerts; reuse for mirror-failure alerts |
| **Confidently-wrong synthesis** | Wiki page reads cleanly but contradicts a source | Lint pass cross-checks `sources:` frontmatter against current source content; flags contradictions; manual review queue |
| **Cross-tool schema drift** (CLAUDE.md vs AGENTS.md diverge) | Different agents see different rules | Pre-commit hook diffs the two; if Astral stub-redirect pattern adopted, single source of truth |
| **Operator edits in Obsidian outside session** (FileChanged) | Agent's last-known-state lags | `FileChanged` hook + `last_ingested` frontmatter timestamp catch on next SessionStart |
| **Session compaction loses pending edits** | Wiki updates not persisted | `PreCompact` hook flushes pending edits to `log.md` first |

### 3.9 Integration Dependencies & Build-Order

A staged rollout that respects integration dependencies (carry into Step 5 implementation planning):

1. **Foundation (week 1)**: Define wiki schema in `CLAUDE.md` / `AGENTS.md` (Astral or Cline pattern). Audit current root CLAUDE.md against the 100–150 line sweet spot.
2. **Frontmatter + log.md primitives (week 1)**: Add `owner`, `last_ingested`, `sources`, `ingest_log` to all `/docs/` files. Initialize `log.md`.
3. **SessionEnd ingest hook (week 1–2)**: Wire the primary Karpathy "ingest" trigger using `disler/claude-code-hooks-mastery` template.
4. **Lint pass (week 2)**: `markdownlint` + `lychee` (link-check) + `vale` (prose) + custom contradictions check via `sources:` frontmatter.
5. **GitNexus integration (week 2–3)**: Use `detect_changes` + `impact` to map code changes → affected wiki pages.
6. **Graphiti integration (week 2–3)**: Cite episodes in `sources:`; query on SessionStart for "recent decisions."
7. **AzDO mirror (week 3–4)**: One-way CI job from `wikiMaster` branch on push.
8. **Scheduled weekly lint (week 4)**: Scheduled remote agent runs `lint` op + posts report.
9. **Optional: MCP server + llms.txt (week 4+)**: Expose `/docs/` to other LLM clients (Cursor, Continue) for cross-tool consumption.
10. **Optional: Quartz v4 build (week 4+)**: Public-readable subset for non-AAD audiences.

Each step is independently rollback-able; failure of any later step doesn't break earlier ones.

**Sources:**
- Claude Code Hooks reference: https://code.claude.com/docs/en/hooks (verified 2026-04-27)
- `disler/claude-code-hooks-mastery`: https://github.com/disler/claude-code-hooks-mastery
- Karpathy LLM-Wiki gist: https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f
- AnswerDotAI llms.txt spec: https://github.com/AnswerDotAI/llms-txt
- AzDO Wiki file structure: https://learn.microsoft.com/en-us/azure/devops/project/wiki/wiki-file-structure
- `Pratiyush/llm-wiki` (frontmatter + lint patterns): https://github.com/Pratiyush/llm-wiki

---

## Architectural Patterns and Design

*Adapted from generic system-architecture template to doc-system architecture: information architecture, source-of-truth topology, file/folder layout, schema architecture, multi-repo strategy. Three concrete architecture sketches (A/B/C) are made implementation-ready.*

### 4.1 Information Architecture — Diátaxis as the spine

**Decision:** adopt **Diátaxis** (https://diataxis.fr) as the wiki's information architecture. Verified adoption by Django, Cloudflare, GitLab, NumPy, FastAPI. The four quadrants map cleanly onto the homelab's mixed audience and onto Karpathy's three-layer model:

| Diátaxis quadrant | Audience served | Source-of-truth tooling |
|---|---|---|
| **Tutorials** (learning-oriented) | New devs, customers, PM onboarding | Operator authoring (Obsidian / direct MD) |
| **How-to** (task-oriented) | Devs, operator, oncall | Operator authoring + auto-memory promotion |
| **Reference** (information-oriented) | Devs, AI agents | **GitNexus Code Wiki** (auto-generated from graph) + mkdocstrings-style API docs where applicable |
| **Explanation** (understanding-oriented) | All audiences (the "why") | **Graphiti** (decisions) + **BMAD outputs** (PRDs, ADRs, retros) + LLM-Wiki synthesis |

Crosscut: **ADRs** sit in Explanation as a first-class subfolder; **Glossary** sits as a Reference cross-cut.

### 4.2 Source-of-Truth Topology (formalized)

```
┌──────────────────────────────────────────────────────────────┐
│  AUTHORITATIVE STORES (each fact-type has ONE home)          │
├──────────────────────────────────────────────────────────────┤
│  Code / config        → git repo (homelab-infra/apps/playbook)│
│  Live code structure  → GitNexus knowledge graph              │
│  Temporal decisions   → Graphiti episodes/facts               │
│  Operator learnings   → Claude auto-memory (~/.claude/.../mem)│
│  Formal artifacts     → BMAD outputs (_bmad-output/)          │
│  External sources     → /raw/ folders (immutable)             │
│  Narrative wiki       → /docs/ markdown (this is the gap)    │
└──────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────┐
│  DERIVED / RENDERED VIEWS (read-only, regeneratable)          │
├──────────────────────────────────────────────────────────────┤
│  Reference docs       → gitnexus wiki output                  │
│  Generated skills     → .claude/skills/generated/             │
│  AzDO Wiki mirror     → wikiMaster branch (one-way mirror)    │
│  Quartz public site   → static HTML (optional)                │
│  MCP-served MD        → /docs/ exposed to other LLM clients   │
│  llms.txt             → site-root manifest                    │
└──────────────────────────────────────────────────────────────┘
```

**Architectural rule:** any fact has exactly one authoritative home. Derived views never become writers. If a contradiction arises, the authoritative store wins by definition.

### 4.3 File/Folder Layout — concrete

#### 4.3.1 Per-repo `/docs/` (Diátaxis-aligned)

```
<repo>/
├── CLAUDE.md                    # Astral stub: single line `@AGENTS.md`
├── AGENTS.md                    # Canonical schema (cross-tool: Cursor/Codex/Continue)
├── .claude/
│   └── rules/                   # Cline manifest split — topic-specific rules
│       ├── general.md           # behavioral rules (~50 lines)
│       ├── file-organization.md # folder discipline
│       ├── security.md          # secrets, validation, OWASP
│       ├── testing.md           # TDD, integration tests
│       └── docs.md              # wiki schema, frontmatter spec, ingest/query/lint workflow
├── llms.txt                     # AnswerDotAI spec — H1/blockquote/H2 file list
└── docs/
    ├── index.md                 # Karpathy "index.md" — content-oriented catalog
    ├── log.md                   # Karpathy "log.md" — chronological append-only
    ├── tutorials/               # Diátaxis quadrant 1
    ├── how-to/                  # Diátaxis quadrant 2 (runbooks live here)
    ├── reference/               # Diátaxis quadrant 3
    │   └── generated/           # gitnexus wiki output (regeneratable)
    ├── explanation/             # Diátaxis quadrant 4
    │   ├── adr/                 # MADR-format ADRs
    │   └── architecture/        # C4 diagrams (Likec4 or Mermaid)
    └── raw/                     # Karpathy "raw" layer — immutable external sources
        ├── articles/
        ├── transcripts/
        └── assets/
```

**Notes:**
- `CLAUDE.md` = `@AGENTS.md` (Astral pattern, §C.8 #1) keeps Anthropic's loader happy while AGENTS.md is the canonical doc cross-tool teams expect.
- `.claude/rules/<topic>.md` (Cline pattern, §C.8 #2) lazy-loads via `InstructionsLoaded` hook (§3.5). Each file is 50–150 lines max.
- `docs/log.md` is the Karpathy primitive — append-only, grep-friendly, fixed prefix per §C.6.
- `docs/reference/generated/` is the GitNexus Code Wiki target. `.gitignore` it from human-edit but commit to git for AzDO mirror visibility.
- `docs/raw/` houses immutable external ingests (Obsidian Web Clipper, downloaded transcripts, etc.).

#### 4.3.2 Workspace-level `homelab-playbook/wiki/` (cross-repo aggregator)

Three repos × per-repo `/docs/` would scatter cross-cutting docs. A workspace-level wiki at `homelab-playbook/wiki/` aggregates *cross-repo concerns* — without duplicating per-repo content:

```
homelab-playbook/wiki/
├── _schema.md                   # workspace-level wiki rules (Karpathy "schema" layer)
├── index.md                     # entry point linking to each repo's /docs/index.md
├── architecture/                # cross-repo architecture (homelab-infra + apps + playbook)
│   ├── overview.md              # the C4 System Context + Container view
│   ├── c4-context.md            # Likec4 / Mermaid C4 diagrams
│   └── integration.md           # cross-repo data flows
├── decisions/                   # workspace-level ADRs (cross-repo)
│   ├── adr-001-three-repo-split.md
│   └── ...
├── glossary/                    # cross-repo terminology
├── projects/                    # active project state (epics, sprint summaries)
│   ├── pve3-storage-redesign.md
│   ├── cloud-dr-pattern-e-azure.md
│   └── ...
├── runbooks/                    # cross-repo runbooks
│   ├── pve9-ha-error-recovery.md
│   ├── tailscale-auth-recovery.md
│   └── ...
├── log.md                       # workspace-level Karpathy log
└── raw/                         # workspace-level immutable sources
```

**Architectural rule for the cross-repo split:**
- Anything *internal* to a single repo lives in `<repo>/docs/`.
- Anything *spanning* repos or *operational* (runbooks, glossary, project state, cross-repo ADRs) lives in `homelab-playbook/wiki/`.
- `homelab-playbook/wiki/index.md` cross-links to each `<repo>/docs/index.md` to give readers one entry point.

#### 4.3.3 Frontmatter spec (single source-of-truth)

Per §3.7, finalized:

```yaml
---
title: "PVE 9 HA Error Recovery"
diataxis: how-to                  # tutorial | how-to | reference | explanation
audience: [operator, oncall]      # operator | oncall | dev | pm | po | customer | agent
owner: human                       # llm | human (governs §3.6 conflict resolution)
status: stable                     # stable | draft | deprecated
last_ingested: 2026-04-27
last_human_edit: 2026-04-23
sources:
  - graphiti://episode/3f9a-...
  - file://homelab-infra/terraform/main.tf:84-120
  - bmad://_bmad-output/planning-artifacts/research/technical-pve3-storage-architecture-research-2026-04-20.md
  - external://https://docs.proxmox.com/ha-manager/  (retrieved 2026-04-23)
ingest_log: log.md#2026-04-23-ingest-pve3-storage
contradictions: []
tags: [pve, ha, recovery, runbook]
---
```

### 4.4 Schema Architecture — `CLAUDE.md` / `AGENTS.md` / `.claude/rules/` split

**Decision:** combine **Astral stub-redirect** (§C.8 #1) + **Cline manifest+topic-split** (§C.8 #2). Concrete shape:

```
CLAUDE.md                # 1 line: `@AGENTS.md`
AGENTS.md                # ~80–120 lines: behavioral rules + project shape + pointers
.claude/rules/
├── general.md           # behavioral invariants (DO X, NEVER Y) — 50 lines
├── file-organization.md # where things live — 30 lines
├── security.md          # OWASP, secrets, validation — 50 lines
├── testing.md           # TDD discipline, mock vs integration — 40 lines
├── docs.md              # **wiki schema + ingest/query/lint workflow** — 100 lines
└── concurrency.md       # batching, parallelism rules — 30 lines
```

**Why this combo:** AGENTS.md is the canonical entry (works for Claude Code, Cursor, Codex, OpenCode). It points to topic files in `.claude/rules/` for organization and PR review-ability. Avoids the 1,094-line CLAUDE.md anti-pattern (§C.8) without sacrificing depth.

> **CORRECTION (added 2026-04-27 via companion research `technical-claude-md-best-practices-2026-04-27.md` §3.1):** earlier drafts of this section claimed `.claude/rules/<topic>.md` files lazy-load via `InstructionsLoaded` hook. **This is wrong.** `@`-imports in CLAUDE.md/AGENTS.md resolve **eagerly** at session start (max 5 levels of recursion) per https://docs.claude.com/en/docs/claude-code/memory. The Cline-style topic split **organizes content but does NOT save session-start tokens** — it only reorganizes them on disk. Genuine lazy-load requires (a) **Skills** (frontmatter scanned at start, body loaded on routing match), (b) **Slash commands** (body loaded on `/name` invocation), (c) **`UserPromptSubmit` hooks** that conditionally inject context, or (d) `paths:` frontmatter on rules files (load only when matching files are touched). Keep the topic split for organization; move procedural content into Skills for actual token savings. Anthropic explicitly endorses the Astral `@AGENTS.md` pattern verbatim.

**Migration path from current state:** the homelab's existing root `CLAUDE.md` is substantial. Refactor in two passes:
1. **Pass 1 (cheap, reversible):** rename existing `CLAUDE.md` → `AGENTS.md`; create new `CLAUDE.md` containing `@AGENTS.md`; commit. Both Anthropic and Codex tools find the right file.
2. **Pass 2 (decomposition):** split AGENTS.md sections into `.claude/rules/<topic>.md` files, leaving AGENTS.md as a 100-line manifest pointing at them. Test with a Claude Code session that the right rules load.

### 4.5 The Three Architectures Made Concrete

#### 4.5.1 Architecture A — Single AzDO Wiki (P3 dominant)

```
homelab repo (single SoT for MD)
├── /docs/  (Diátaxis-aligned, see §4.3.1)
└── (wikiMaster branch — auto-mirrored from main /docs/ via CI)

Azure DevOps Wiki (consumption surface)
├── pulls from wikiMaster branch
├── AAD SSO (PMs/PO/devs already have access via Sparkle-CPS tenant)
└── customer access = N/A (gap acknowledged)

AI agents
└── read /docs/ via filesystem (no MCP; same git tree)
```

**Loses:** customer audience (gap), Karpathy LLM-Wiki maintenance loop, GitNexus Code Wiki integration.
**Wins:** lowest steady-state cost, fastest to ship.

#### 4.5.2 Architecture B — Obsidian + Quartz (P6 dominant)

```
homelab repo (single SoT for MD; same /docs/ folder as A)

Operator IDE
└── Obsidian (vault = /docs/ via obsidian-git plugin)

Public consumption surface
└── Quartz v4 (free, OSS) builds /docs/ → static site
    └── deployed via Cloudflare/Tailscale-only (Tom's default per phone-notif memory)

Agent maintenance loop (Karpathy LLM-Wiki)
├── SessionEnd hook → ingest session learnings → /docs/ + log.md
├── Scheduled weekly lint → contradictions, orphans, drift report
└── Manual `gitnexus wiki --review` when reference layer needs regen
```

**Loses:** SSO (Quartz is anonymous-only or behind Tailscale ACL), audit trail, PM/PO native experience (no AzDO).
**Wins:** Karpathy operator-cognition gains, low ops, full GitNexus integration.

#### 4.5.3 Architecture C — Hybrid (P6 + P3 + P5 composed)

```
homelab repo /docs/  (Diátaxis-aligned, single SoT)
        │
        ├──→ wikiMaster branch  ──→ Azure DevOps Wiki (PMs/PO/devs, AAD SSO)
        │    (one-way CI mirror on push to main)
        │
        ├──→ Obsidian vault (operator IDE; obsidian-git plugin)
        │
        ├──→ Quartz v4 build  ──→ Tailscale-served static site (customers, optional)
        │    (one-way CI build)
        │
        ├──→ docs-mcp-server  ──→ Cursor / Continue / future LLM clients
        │
        ├──→ /llms.txt at site root  ──→ external LLM crawlers
        │
        └──→ GitNexus Code Wiki regen  ──→ /docs/reference/generated/
             (SessionEnd hook + scheduled cron)

Maintenance loop (Karpathy ingest/query/lint per §3.5)
├── Sources flow IN: GitNexus, Graphiti, BMAD outputs, auto-memory promotion, /raw/
└── Lint pass: contradictions, orphans, broken citations
```

**Loses:** highest composition complexity (3 mirror surfaces, 1–2 days CI setup, ongoing pipeline maintenance).
**Wins:** every audience gets its native surface from a single SoT; lock-in is low (each consumer is replaceable).

### 4.6 Architectural Decisions Worth Recording (ADRs to draft in Step 5)

The synthesis step needs these decisions made explicit. Drafting them as ADR titles now (template per `MADR 4.0` https://adr.github.io):

| ADR | Title | Why it's load-bearing |
|---|---|---|
| **ADR-001** | Adopt Diátaxis as wiki IA | Affects every other doc decision |
| **ADR-002** | Wiki is markdown-in-git as single SoT, all consumption is read-only fan-out | Architectural invariant; everything else depends on it |
| **ADR-003** | CLAUDE.md = `@AGENTS.md`; AGENTS.md is canonical; topic split via `.claude/rules/` | Replaces current root CLAUDE.md; cross-tool portability |
| **ADR-004** | Pick architecture (A vs B vs C) | The synthesis-step decision; gates Step 5 implementation |
| **ADR-005** | Frontmatter spec is mandatory on all `/docs/` files | Without this, provenance and lint don't work |
| **ADR-006** | GitNexus Code Wiki generates `/docs/reference/generated/` only; never edits other folders | Bounds the auto-generator's blast radius |
| **ADR-007** | Graphiti is authoritative for temporal decisions; wiki cites by URI, never duplicates | Locks the source-of-truth topology in §4.2 |
| **ADR-008** | Workspace-level wiki at `homelab-playbook/wiki/` for cross-repo concerns; per-repo `/docs/` for repo-internal | Multi-repo strategy |
| **ADR-009** | log.md is append-only, prefix-formatted, rotated annually | Karpathy primitive, makes failure-mode #3 in §3.8 work |
| **ADR-010** | Mirrors are one-way only (repo → AzDO, repo → Quartz); consumers never write back | Prevents merge-conflict failure mode |

### 4.7 Information Architecture Cross-cuts

Three architectural concerns that don't fit a single Diátaxis quadrant — they cut across:

| Cross-cut | Where it lives | Why |
|---|---|---|
| **ADRs** | `docs/explanation/adr/` per-repo + `homelab-playbook/wiki/decisions/` workspace-level | ADRs are explanation but indexed independently; the workspace level holds cross-repo decisions |
| **Glossary** | `docs/reference/glossary.md` per-repo + `homelab-playbook/wiki/glossary/` workspace-level | Reference-quadrant but consumed by all audiences; needs a stable URL |
| **Project state** | `homelab-playbook/wiki/projects/<project>.md` only | Cross-cuts repos; tracks epic/sprint state — not per-repo |
| **Runbooks** | `docs/how-to/` per-repo + `homelab-playbook/wiki/runbooks/` workspace-level (cross-repo ones) | How-to quadrant; promote from auto-memory entries |

### 4.8 Architecture-level NFRs (non-functional requirements)

| NFR | Target | Rationale |
|---|---|---|
| Drift latency (a code change → its doc page is flagged stale) | < 24 hours | Scheduled lint + post-commit GitNexus reindex catch within a day |
| Doc-mirror latency (commit to /docs/ → AzDO Wiki updated) | < 5 minutes | One-way CI job; existing CI runners are fast |
| Wiki regen full cost (LLM bill) | < $5/month at homelab volume | GitNexus Code Wiki concurrency 3, bounded per-module regen |
| Schema-file load size at session start | < 10k tokens | Cline split keeps `.claude/rules/<topic>.md` lazy-loaded |
| Hallucination escape rate (synthesized claim contradicts source) | flagged within 1 week | Lint pass cross-checks `sources:` frontmatter against current source content |
| Multi-audience accessibility | every audience has a native surface | A: PMs/devs only. B: operator + public. C: all four (PM/PO/devs/customers/agents) |

### 4.9 Sources
- Diátaxis: https://diataxis.fr (verified 2026-04-27)
- C4 model: https://c4model.com
- MADR 4.0 (ADR template): https://adr.github.io
- Karpathy LLM-Wiki gist: https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f
- AnswerDotAI llms.txt spec: https://github.com/AnswerDotAI/llms-txt
- Astral CLAUDE.md/AGENTS.md pattern: https://github.com/astral-sh/uv
- Cline manifest pattern: https://github.com/cline/cline
- GitNexus README: https://github.com/abhigyanpatwari/GitNexus
- Claude Code hooks: https://code.claude.com/docs/en/hooks (verified 2026-04-27)

---

## Implementation Approaches and Technology Adoption

*Adapted from the generic adoption template to a doc-system implementation: concrete tools, hook scripts, ADR drafts, lint configs, mirror CI, week-by-week build plan, cost & risk model. All three architectures (A/B/C) share the foundation; arch-specific work is called out.*

### 5.1 Bill of Materials — concrete tools

| Layer | Tool | Install/version | License | Cost |
|---|---|---|---|---|
| **Markdown lint** | `markdownlint-cli2` | `npm i -g markdownlint-cli2@^0.13` | MIT | $0 |
| **Link check** | `lychee` | Cargo / GitHub release v0.15+ | Apache-2.0 / MIT | $0 |
| **Prose lint** | `Vale` (with Microsoft + write-good styles) | `apt install vale` or GitHub release v3+ | MIT | $0 |
| **Code-graph wiki gen** | `gitnexus wiki` (existing) | local container (already running) | PolyForm-NC | $0 (homelab non-comm) + LLM bill |
| **Skill gen** | `gitnexus analyze --skills` | same | same | LLM bill on skills regen |
| **Diagrams** | Mermaid (renders natively in GitHub, AzDO Wiki, Obsidian); Likec4 for C4 | npm `@likec4/cli` for build | MIT | $0 |
| **MCP doc serve** | `docs-mcp-server` (https://github.com/arabold/docs-mcp-server) | npm | MIT | $0 |
| **Static site (arch B/C)** | Quartz v4 (https://quartz.jzhao.xyz) | npm | MIT | $0 |
| **Vault sync (arch B/C)** | `obsidian-git` plugin (community plugin) | from Obsidian community plugins | MIT | $0 |
| **AzDO mirror (arch A/C)** | git push to `wikiMaster` branch via Azure Pipelines or Claude Code agent | existing tenant | proprietary | already paid |
| **Citation-check** | custom Python (see §5.5) | pure stdlib | n/a | $0 |
| **Frontmatter schema** | JSON Schema + `ajv-cli` or `python-frontmatter` | npm/pip | MIT | $0 |
| **Wiki search (optional)** | `qmd` (https://github.com/tobi/qmd) per Karpathy gist | Go binary | MIT | $0 |

**LLM cost projection (homelab volume, ~10k LOC across 3 repos):**
- `gitnexus wiki` full regen: ~30–60 modules × ~1 LLM call each at concurrency 3 → **$0.50–$2 per full regen**.
- SessionEnd ingest (10–15 page touches per session): ~$0.10–0.30/session × ~20 sessions/month → **~$2–6/month**.
- Scheduled weekly lint (cross-check sources): ~$0.50/run × 4 = **~$2/month**.
- **Total target: < $10/month** (NFR §4.8 set $5; this overshoots by 2× but is bounded — adjust by gating regen on graph-delta threshold).

### 5.2 ADR Drafts — load-bearing decisions

Drafting the **3 most load-bearing** from §4.6 fully (others as skeletons in §5.2.4 — to be completed during Step 6 synthesis or first implementation week).

#### 5.2.1 ADR-002: Markdown-in-git is the single source of truth; consumption is read-only fan-out

```markdown
# ADR-002: Markdown-in-git is the single source of truth; consumption is read-only fan-out

- Status: proposed
- Date: 2026-04-27
- Deciders: tomamourette
- Supersedes: n/a

## Context and Problem Statement

The homelab needs documentation across multiple audiences (PM, PO, devs, customers, AI agents) and multiple consumption surfaces (Obsidian, AzDO Wiki, Quartz site, MCP server). Without a clear source-of-truth rule, the wiki will drift across surfaces and merge conflicts will follow.

## Decision Drivers

- Multi-audience requirement — different surfaces, same content.
- Verifiability — claims must trace to a single canonical source.
- Mixed authoring — humans (Obsidian, direct edit, web UI) and AI agents (Claude Code) both write.
- Failure-mode containment — a stale mirror must not propagate back.

## Considered Options

1. AzDO Wiki as canonical (humans edit there; mirror to repo).
2. Obsidian vault as canonical (operator edits there; sync via obsidian-git).
3. **Markdown-in-git is canonical**; all surfaces are one-way read-only mirrors.

## Decision

Option 3. The `<repo>/docs/` directory and `homelab-playbook/wiki/` directory are the only authoritative locations for narrative documentation. AzDO Wiki, Quartz, MCP server, llms.txt are derived views. Mirror jobs are one-way only.

## Consequences

- Positive: any audience can read; no merge conflicts across surfaces; provenance is git history.
- Negative: edits made in AzDO Wiki UI are lost (never propagate back). Mitigation: AzDO Wiki configured as read-only or labeled as such.
- Negative: requires the operator to author in either Obsidian (via vault on the same git tree) or directly in the repo — no web-UI authoring path.
```

#### 5.2.2 ADR-003: CLAUDE.md = `@AGENTS.md`; AGENTS.md is canonical; topic split via `.claude/rules/`

```markdown
# ADR-003: CLAUDE.md is a stub redirect; AGENTS.md is canonical schema; rules split into .claude/rules/

- Status: proposed
- Date: 2026-04-27
- Deciders: tomamourette
- Supersedes: existing 250+ line root CLAUDE.md

## Context and Problem Statement

The current root `CLAUDE.md` mixes behavioral rules, file organization, security, build commands, swarm config, and CLI references in one file. It is trending toward the 1,094-line `ruvnet/claude-flow` (rebranded ruflo) anti-pattern (per §C.8). Cross-tool teams (Cursor, Codex) cannot read CLAUDE.md.

## Decision Drivers

- Cross-tool portability (Claude Code, Cursor, Codex, Continue, OpenCode all expect different files).
- Lazy-load via `InstructionsLoaded` hook only the relevant rules, keeping context lean (NFR <10k tokens).
- Reduce single-file merge conflicts.
- Match high-quality OSS exemplars (Astral, Cline, Temporal, Dagger).

## Considered Options

1. Keep CLAUDE.md monolithic, just trim it.
2. Migrate everything to AGENTS.md (drop CLAUDE.md).
3. **Astral pattern** (CLAUDE.md = stub redirect; AGENTS.md is canonical) **+ Cline pattern** (split content into `.claude/rules/<topic>.md`).

## Decision

Option 3.
- `CLAUDE.md` contains a single line: `@AGENTS.md` (Astral pattern, ref §C.8 #1).
- `AGENTS.md` is a 80–120 line manifest pointing at topic files.
- `.claude/rules/<topic>.md` files (general / file-organization / security / testing / docs / concurrency) hold detailed rules, lazy-loaded.

## Migration Path

Pass 1 (cheap, same-day):
1. `mv CLAUDE.md AGENTS.md`
2. `printf '@AGENTS.md\n' > CLAUDE.md`
3. Commit. Both Anthropic and Codex tools find the right file.

Pass 2 (decomposition, ~half-day):
4. Identify ~6 topic boundaries in AGENTS.md.
5. Move sections into `.claude/rules/<topic>.md`.
6. Replace each moved section in AGENTS.md with a 1-line pointer (`See .claude/rules/<topic>.md`).
7. Verify with a Claude Code session that the right rules load.

## Consequences

- Positive: cross-tool portability, lean context, easier maintenance.
- Negative: migration cost (~half-day total).
- Negative: agents must support `@AGENTS.md` indirection (Claude Code does; Cursor/Codex pick AGENTS.md directly).
```

#### 5.2.3 ADR-005: Frontmatter spec is mandatory on all `/docs/` files

```markdown
# ADR-005: Frontmatter spec is mandatory on all /docs/ files

- Status: proposed
- Date: 2026-04-27
- Deciders: tomamourette

## Context and Problem Statement

Without uniform frontmatter, provenance, multi-audience filtering, drift detection, and lint passes (§3.7, §3.8) cannot work. Files generated by GitNexus, BMAD, and humans must agree on a single schema.

## Decision

All `/docs/**/*.md` files MUST carry the frontmatter spec from §4.3.3:

```yaml
title, diataxis, audience, owner, status, last_ingested, last_human_edit,
sources, ingest_log, contradictions, tags
```

A pre-commit hook validates frontmatter via JSON Schema + `ajv-cli`. Files that fail validation cannot be committed.

`docs/log.md` and `docs/index.md` are exempt (they have their own structural rules).

## Consequences

- Positive: enables provenance, lint, multi-audience filtering, drift tracking.
- Negative: every existing `/docs/` file needs frontmatter added (~8 files in current homelab baseline; ~30 min one-time cost).
- Negative: humans authoring quickly may forget frontmatter — pre-commit catches; agents have no excuse.
```

#### 5.2.4 ADR skeletons (drafts to complete in Step 6 / first impl week)

- **ADR-001** Adopt Diátaxis IA (decision: yes; tradeoffs: writer discipline; alternatives: ad-hoc, C4-only, divio).
- **ADR-004** Pick architecture (A vs B vs C) — *the* synthesis decision; carries forward to Step 6.
- **ADR-006** GitNexus Code Wiki bounded to `/docs/reference/generated/`; never edits other folders.
- **ADR-007** Graphiti is authoritative for temporal decisions; wiki cites by `graphiti://` URI.
- **ADR-008** Workspace `homelab-playbook/wiki/` for cross-repo concerns; per-repo `/docs/` for repo-internal.
- **ADR-009** `log.md` is append-only, prefix-formatted, rotated annually.
- **ADR-010** Mirrors are one-way only (no consumer writes back to the SoT).

### 5.3 Hook Script Implementations

Three hooks, all under `~/.claude/hooks/docs/`. Existing `gitnexus/{pre,post}.sh` provide the template (`set +e`, fail-silent, 3-second timeout).

#### 5.3.1 SessionEnd ingest hook (`~/.claude/hooks/docs/session-end.sh`)

The Karpathy "ingest" trigger. Fires when a Claude Code session ends; queues an ingest of session learnings into the wiki.

```bash
#!/usr/bin/env bash
# Doc-system SessionEnd hook — Karpathy ingest trigger.
# Reads session transcript, extracts decisions/learnings, queues for wiki ingest.
# Per CLAUDE.md hook-discipline: 3-second timeout, fail-silent.
set +e

PROJECT_ROOT="${CLAUDE_PROJECT_ROOT:-/home/developer/workspace/homelab}"
INGEST_QUEUE="$PROJECT_ROOT/homelab-playbook/wiki/_meta/ingest-queue.jsonl"

# Read SessionEnd payload from stdin (JSON metadata)
PAYLOAD=$(cat 2>/dev/null || echo '{}')
SESSION_ID=$(printf '%s' "$PAYLOAD" | jq -r '.session_id // empty' 2>/dev/null)
TERMINATION=$(printf '%s' "$PAYLOAD" | jq -r '.termination_reason // "unknown"' 2>/dev/null)

# Skip if session ended due to error or was empty
if [ "$TERMINATION" = "error" ] || [ -z "$SESSION_ID" ]; then
  exit 0
fi

# Append a queue entry — actual ingest happens async via separate `docs-ingest` runner
# (avoids blocking the Claude Code shutdown path)
mkdir -p "$(dirname "$INGEST_QUEUE")"
printf '{"ts":"%s","session_id":"%s","termination":"%s","status":"pending"}\n' \
  "$(date -Iseconds)" "$SESSION_ID" "$TERMINATION" \
  >> "$INGEST_QUEUE" 2>/dev/null

exit 0
```

A separate `docs-ingest` runner (cron or systemd timer, every 15 min) drains the queue, runs the actual LLM-driven ingest against the session transcript, and updates wiki pages + log.md. This decouples Claude Code shutdown latency from LLM cost/time.

#### 5.3.2 PostToolUse log.md hook (`~/.claude/hooks/docs/post-tooluse-edit.sh`)

Append a log.md entry every time an Edit/Write hits `/docs/**`.

```bash
#!/usr/bin/env bash
# Doc-system PostToolUse hook (matcher: Edit|Write|MultiEdit).
# Appends an entry to log.md when a /docs/ file is modified.
set +e
PROJECT_ROOT="${CLAUDE_PROJECT_ROOT:-/home/developer/workspace/homelab}"

PAYLOAD=$(cat 2>/dev/null || echo '{}')
FILE_PATH=$(printf '%s' "$PAYLOAD" | jq -r '.tool_input.file_path // empty' 2>/dev/null)

# Filter: only docs files
case "$FILE_PATH" in
  */docs/*|*/wiki/*) ;;
  *) exit 0 ;;
esac

# Append to the log.md of the relevant wiki
LOG_DIR=$(dirname "$FILE_PATH")
while [ "$LOG_DIR" != "/" ] && [ ! -f "$LOG_DIR/log.md" ]; do
  LOG_DIR=$(dirname "$LOG_DIR")
done
[ ! -f "$LOG_DIR/log.md" ] && exit 0

REL=$(realpath --relative-to="$LOG_DIR" "$FILE_PATH" 2>/dev/null)
printf '## [%s] edit | %s | session=%s\n' \
  "$(date -Iseconds)" "$REL" "${CLAUDE_SESSION_ID:-unknown}" \
  >> "$LOG_DIR/log.md"

exit 0
```

Wired in `~/.claude/settings.json`:
```json
{
  "PostToolUse": [
    {
      "matcher": "Edit|Write|MultiEdit",
      "hooks": [
        {"type": "command", "command": "/home/developer/.claude/hooks/docs/post-tooluse-edit.sh", "timeout": 3, "statusMessage": "doc log.md append"}
      ]
    }
  ]
}
```

#### 5.3.3 Scheduled lint runner (cron or scheduled remote agent)

Not a Claude Code hook — runs weekly via cron (or `/schedule` skill).

```bash
#!/usr/bin/env bash
# Weekly doc lint — Karpathy lint pass.
# Run via cron: 0 6 * * 1 /home/developer/.claude/hooks/docs/weekly-lint.sh
set -euo pipefail
PROJECT_ROOT="${1:-/home/developer/workspace/homelab}"
REPORT="$PROJECT_ROOT/homelab-playbook/wiki/_meta/lint-$(date -I).md"

cd "$PROJECT_ROOT"

{
  echo "# Doc Lint Report — $(date -I)"
  echo ""
  echo "## markdownlint"
  npx markdownlint-cli2 "**/docs/**/*.md" "**/wiki/**/*.md" 2>&1 || true
  echo ""
  echo "## lychee (link check)"
  lychee --no-progress "**/docs/**/*.md" "**/wiki/**/*.md" 2>&1 || true
  echo ""
  echo "## vale (prose)"
  vale --output line "**/docs/**/*.md" "**/wiki/**/*.md" 2>&1 || true
  echo ""
  echo "## citation check"
  python3 ~/.claude/hooks/docs/check-citations.py "$PROJECT_ROOT" 2>&1 || true
  echo ""
  echo "## orphan pages (no inbound links)"
  python3 ~/.claude/hooks/docs/check-orphans.py "$PROJECT_ROOT" 2>&1 || true
} > "$REPORT"

# Notify via existing crash-notifier pattern (adapt for ntfy info topic)
curl -s -d "Weekly doc lint: $REPORT" "http://192.168.50.101/ntfy/docs-lint" || true
```

### 5.4 Lint Configs (concrete)

#### 5.4.1 `.markdownlint-cli2.yaml` (repo root)

```yaml
config:
  default: true
  MD013: false   # line length — disabled for tables/code
  MD041: false   # first-line-h1 — frontmatter conflicts
  MD033:         # inline HTML — allow specific tags for callouts
    allowed_elements: [details, summary, kbd, sup, sub]
  MD024:
    siblings_only: true
globs:
  - "**/docs/**/*.md"
  - "**/wiki/**/*.md"
ignores:
  - "**/node_modules/**"
  - "**/_bmad-output/**"   # BMAD outputs are raw, not wiki
  - "**/docs/reference/generated/**"  # GitNexus output, lint exempt
```

#### 5.4.2 `.lychee.toml` (repo root)

```toml
include = ["**/docs/**/*.md", "**/wiki/**/*.md"]
exclude = ["graphiti://*", "bmad://*", "file://*"]   # citation URIs handled by check-citations.py
exclude_path = ["node_modules", "_bmad-output"]
timeout = 20
max_concurrency = 4
accept = [200, 206, 429]
cache = true
max_cache_age = "1d"
```

#### 5.4.3 `.vale.ini` (repo root)

```ini
StylesPath = .vale/styles
MinAlertLevel = warning

Packages = Microsoft, write-good, proselint

[*.md]
BasedOnStyles = Vale, Microsoft, write-good
TokenIgnores = (\$+[^\n$]+\$+), (\b[A-Z][a-zA-Z0-9]+\.[a-zA-Z0-9]+\b)

[docs/explanation/adr/*.md]
# ADRs are technical; relax some prose rules
write-good.Passive = NO
```

#### 5.4.4 `check-citations.py` (custom — citation-resolver)

```python
#!/usr/bin/env python3
"""Validate frontmatter `sources:` URIs resolve.
Schemes:
  graphiti://episode/<uuid>  -> resolved via mcp__graphiti__get_entity_edge
  file://<path>:<lo>-<hi>    -> file exists, line range valid
  bmad://<path>              -> file exists in _bmad-output/
  external://<url>           -> lychee handles
"""
import re, sys, json
from pathlib import Path
import frontmatter

ROOT = Path(sys.argv[1])
errors = []
for md in ROOT.rglob("docs/**/*.md"):
    fm = frontmatter.load(md)
    for src in fm.metadata.get("sources", []):
        if src.startswith("file://"):
            m = re.match(r"file://([^:]+)(?::(\d+)-(\d+))?", src)
            if m:
                p = ROOT / m.group(1)
                if not p.exists():
                    errors.append((md, src, "file missing"))
        elif src.startswith("bmad://"):
            p = ROOT / src.removeprefix("bmad://")
            if not p.exists():
                errors.append((md, src, "bmad source missing"))
        # graphiti:// validation requires MCP call — defer to runtime
for e in errors:
    print(f"BROKEN  {e[0]}  ::  {e[1]}  ::  {e[2]}")
sys.exit(1 if errors else 0)
```

#### 5.4.5 Frontmatter JSON Schema (`docs/_meta/frontmatter.schema.json`)

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "required": ["title", "diataxis", "audience", "owner", "status", "last_ingested"],
  "properties": {
    "title": {"type": "string", "minLength": 3},
    "diataxis": {"enum": ["tutorial", "how-to", "reference", "explanation"]},
    "audience": {"type": "array", "items": {"enum": ["operator", "oncall", "dev", "pm", "po", "customer", "agent"]}, "minItems": 1},
    "owner": {"enum": ["llm", "human"]},
    "status": {"enum": ["stable", "draft", "deprecated"]},
    "last_ingested": {"type": "string", "format": "date"},
    "last_human_edit": {"type": "string", "format": "date"},
    "sources": {"type": "array", "items": {"type": "string", "pattern": "^(graphiti|file|bmad|external)://"}},
    "ingest_log": {"type": "string"},
    "contradictions": {"type": "array"},
    "tags": {"type": "array", "items": {"type": "string"}}
  }
}
```

Pre-commit hook runs `ajv validate -s docs/_meta/frontmatter.schema.json -d <changed-files>`.

### 5.5 Mirror CI Recipes (architecture A and C)

#### 5.5.1 AzDO Wiki one-way mirror (Azure Pipelines YAML)

```yaml
# azure-pipelines-wiki-mirror.yml
trigger:
  branches:
    include: [main]
  paths:
    include: ['**/docs/**', 'homelab-playbook/wiki/**']
pool: { vmImage: ubuntu-latest }
steps:
  - checkout: self
    persistCredentials: true
  - bash: |
      set -euo pipefail
      # 1. Clone the wikiMaster branch as a separate worktree
      git fetch origin wikiMaster:wikiMaster || git branch wikiMaster
      git worktree add /tmp/wiki wikiMaster
      # 2. Sync /docs/ + /wiki/ trees into the worktree (rsync-style)
      rsync -av --delete \
        --include='*/' --include='*.md' --include='*.png' --include='*.svg' \
        --exclude='*' \
        homelab-playbook/wiki/ /tmp/wiki/playbook-wiki/
      for repo in homelab-infra homelab-apps homelab-playbook; do
        rsync -av --delete \
          --include='*/' --include='*.md' --include='*.png' --include='*.svg' \
          --exclude='*' \
          "$repo/docs/" "/tmp/wiki/$repo/"
      done
      # 3. Commit + push to wikiMaster
      cd /tmp/wiki
      git add -A
      git diff --cached --quiet && exit 0
      git commit -m "wiki: mirror from main @ $(BUILD_SOURCEVERSION)"
      git push origin wikiMaster
    displayName: Mirror /docs/ and /wiki/ to wikiMaster branch
```

The AzDO Wiki is configured (one-time, in the AzDO project settings) as a "Code Wiki" pointing at the `wikiMaster` branch.

#### 5.5.2 Quartz build (architecture B and C, optional)

```yaml
# .github/workflows/quartz-build.yml
on:
  push:
    branches: [main]
    paths: ['homelab-playbook/wiki/**', '**/docs/**']
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: 20 }
      - run: |
          git clone https://github.com/jackyzha0/quartz.git build-quartz
          cd build-quartz
          npm ci
          # Symlink the wiki + per-repo docs as content/
          mkdir -p content
          ln -s ../../homelab-playbook/wiki/* content/
          for r in homelab-infra homelab-apps homelab-playbook; do
            ln -s ../../$r/docs content/$r-docs
          done
          npx quartz build
      - uses: actions/upload-artifact@v4
        with:
          name: quartz-site
          path: build-quartz/public
```

Then deploy `quartz-site` artifact behind Tailscale via `nginx` on a homelab CT (matches your phone-notifications-tailscale memory: Tailscale-only is the default for non-public services).

### 5.6 GitNexus Wiki Integration

Already running (post-commit hook reindexes on every commit). To activate the wiki output:

```bash
# One-time: configure provider/key
gitnexus wiki --provider openai --api-key "$OPENAI_API_KEY"  # or Azure with --base-url

# Test on smallest repo (homelab-playbook) with --review gate
cd /home/developer/workspace/homelab
docker exec gitnexus node /app/gitnexus/dist/cli/index.js wiki --review homelab-playbook
# Inspect the proposed module structure; adjust if needed; let it generate.
# Output writes to homelab-playbook/.gitnexus/wiki/ by default.

# Permanent: scheduled regen (graph-delta gated)
# /home/developer/.claude/hooks/docs/gitnexus-wiki-regen.sh
docker exec gitnexus node /app/gitnexus/dist/cli/index.js wiki "$REPO" \
  --concurrency 3 --no-stats
# Then move output: rsync .gitnexus/wiki/ docs/reference/generated/
```

**Bound the blast radius (per ADR-006):** GitNexus output goes only to `docs/reference/generated/`. A pre-commit hook rejects writes outside this prefix when commit author == "gitnexus-bot".

### 5.7 MCP Doc Server Setup (architecture C)

Use `arabold/docs-mcp-server` (verified via §C.3 §C.8): exposes a markdown directory as MCP resources to any MCP client.

```json
// Add to ~/.claude.json mcpServers
"docs": {
  "command": "npx",
  "args": ["-y", "@arabold/docs-mcp-server", "--root", "/home/developer/workspace/homelab"],
  "type": "stdio"
}
```

Cursor and Continue read the same MCP server via their config files. One source, many clients.

### 5.8 llms.txt Generation

A 30-line script that walks `/docs/` and emits an AnswerDotAI-spec llms.txt:

```python
#!/usr/bin/env python3
"""Generate /llms.txt from docs/ tree."""
from pathlib import Path
import frontmatter

ROOT = Path(".")
print("# Homelab Documentation\n")
print("> Operator-facing wiki for the bi-services.be homelab. Three-repo IaC stack (Proxmox / Terraform / Ansible) with apps and orchestration playbook.\n")
for q in ["tutorials", "how-to", "reference", "explanation"]:
    print(f"## {q.title()}")
    for md in sorted((ROOT / "homelab-playbook/wiki").rglob("*.md")):
        try:
            fm = frontmatter.load(md)
            if fm.metadata.get("diataxis") == q.rstrip("s"):
                title = fm.metadata.get("title", md.stem)
                print(f"- [{title}]({md.as_posix()}): {fm.metadata.get('description', '')}")
        except Exception:
            pass
    print()
```

Run on every push to main; commit `llms.txt` to repo root.

### 5.9 Migration Plan from Current State

The homelab has an 8-file BMAD-generated `/docs/` baseline at workspace root and the existing root `CLAUDE.md`. Migration without breaking BMAD's `bmad-update-project-docs` skill:

| Week | Task | Reversible? | Cost |
|---|---|---|---|
| **W1** | ADR-003 Pass 1 (CLAUDE.md → AGENTS.md + stub) | ✅ git revert | 30 min |
| **W1** | Add frontmatter to existing 8 `/docs/` files (ADR-005) | ✅ revert | 30 min |
| **W1** | Create `docs/log.md` and seed initial entry | ✅ delete | 5 min |
| **W1** | Initialize `docs/_meta/frontmatter.schema.json` + ajv pre-commit | ✅ disable hook | 30 min |
| **W2** | ADR-003 Pass 2 (split AGENTS.md into `.claude/rules/<topic>.md`) | ✅ git revert | 2–3 hrs |
| **W2** | Move existing 8 `/docs/` files into Diátaxis quadrant folders (`tutorials/`, `how-to/`, `reference/`, `explanation/`) | ✅ git revert | 1 hr |
| **W2** | Install markdownlint + lychee + vale; commit configs | ✅ disable | 1 hr |
| **W2** | Wire SessionEnd + PostToolUse hooks (§5.3) | ✅ disable | 2 hrs |
| **W3** | First `gitnexus wiki --review` test on homelab-playbook; iterate on module structure | ✅ delete output | 1–2 hrs + small LLM bill |
| **W3** | Set up scheduled weekly lint cron + report ntfy push | ✅ disable cron | 30 min |
| **W3** | (Architecture A/C) AzDO Wiki mirror pipeline | ✅ stop pipeline | 2–3 hrs |
| **W3** | (Architecture B/C) Obsidian vault as `obsidian-git` checkout of repo | ✅ uninstall plugin | 30 min |
| **W4** | (Architecture C) Quartz build + Tailscale-served deploy | ✅ stop pipeline | 4–6 hrs |
| **W4** | (Architecture C) MCP doc server registered in Cursor/Continue too | ✅ remove from config | 30 min |
| **W4** | Write remaining ADR drafts (ADR-001/004/006/007/008/009/010) into `docs/explanation/adr/` | ✅ revert | 2–3 hrs |
| **W4+** | Ongoing: scheduled lint reports drive cleanup; LLM-Wiki ingest loop runs on every Claude Code session | n/a | <$10/mo LLM |

**Critical path** (architecture-agnostic, must do in order): W1 schema + frontmatter + log.md → W2 hooks + Diátaxis split → W3 GitNexus wiki test + lint cron. Architecture-specific work (AzDO mirror / Quartz / MCP) is parallelizable across W3–W4.

### 5.10 Risks and Mitigations

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| GitNexus single-maintainer dies / project abandoned | Medium | Low (existing version remains usable; OSS license permanent) | Pin docker image SHA; archive image locally |
| LLM cost explodes on `gitnexus wiki` regen | Low–Medium | Medium ($-tens) | Gate regen on graph-delta threshold; track $ in monthly review |
| Hallucinated synthesis confidently-wrong | Medium | High (decision based on wrong page) | Lint pass cross-checks `sources:`; flag contradictions; manual review of `owner: llm` pages monthly |
| Operator authoring drift (humans skip frontmatter, log.md) | High | Medium | Pre-commit hook is the gate; soft-fail with warning the first month, hard-fail after |
| AzDO Wiki mirror conflict (someone edits in AzDO UI) | Medium | Low–Medium | Configure as "Code Wiki" pointing at `wikiMaster` branch (read-only by design); communicate to PMs |
| Cline manifest split breaks because Cursor/Codex don't follow `@AGENTS.md` redirect | Low | Medium | Test in Cursor + Codex sessions before retiring CLAUDE.md content; fallback: keep AGENTS.md+CLAUDE.md as duplicates |
| BMAD doc skills (`bmad-update-project-docs`) collide with new system | Medium | Low | Test BMAD skills against the new layout; update BMAD config `project_knowledge: docs/` if needed |
| Scheduled lint cron silently fails | Medium | High (drift accumulates) | Wire crash-notifier pattern; weekly health-check ntfy includes "lint last ran: $TS" |
| `docs-mcp-server` unmaintained | Low | Low | Trivial to fork or replace — alternative: write a 100-line MCP server |

### 5.11 Sources

- markdownlint-cli2: https://github.com/DavidAnson/markdownlint-cli2
- lychee: https://github.com/lycheeverse/lychee
- Vale: https://vale.sh
- AnswerDotAI llms-txt: https://github.com/AnswerDotAI/llms-txt
- arabold/docs-mcp-server: https://github.com/arabold/docs-mcp-server
- Quartz v4: https://quartz.jzhao.xyz
- obsidian-git: https://github.com/Vinzent03/obsidian-git
- MADR 4.0: https://adr.github.io
- Likec4: https://likec4.dev
- Mermaid: https://mermaid.js.org
- AzDO Wiki Code Wiki mode: https://learn.microsoft.com/en-us/azure/devops/project/wiki/wiki-file-structure

## Technical Research Recommendations

### Implementation Roadmap

Carry into Step 6 synthesis: **W1 foundation (architecture-agnostic) → W2 hooks + Diátaxis migration → W3 GitNexus wiki + lint + arch-specific mirror → W4 polish + ADR backfill.** Total ~4 working weeks at evening cadence.

### Technology Stack Recommendations (locked)

- **Source format**: CommonMark/GFM Markdown.
- **IA**: Diátaxis (tutorials/how-to/reference/explanation) + ADR + glossary cross-cuts.
- **Schema**: CLAUDE.md = `@AGENTS.md`; AGENTS.md canonical; `.claude/rules/<topic>.md` split (Astral + Cline).
- **Reference docs**: `gitnexus wiki` → `docs/reference/generated/`.
- **Diagrams**: Mermaid for flows; Likec4 for C4 architecture.
- **Lint**: markdownlint-cli2 + lychee + Vale + custom citation-checker + ajv frontmatter validation.
- **MCP serve**: `arabold/docs-mcp-server`.
- **Static publish (B/C)**: Quartz v4.
- **Operator IDE (B/C)**: Obsidian + obsidian-git.
- **Mirror to AzDO Wiki (A/C)**: Azure Pipelines YAML one-way to `wikiMaster` branch.
- **Search (optional)**: qmd at scale > 100 pages.

### Skill Development Requirements

- Operator: Diátaxis discipline (knowing which quadrant a doc belongs to); frontmatter literacy.
- AI agents (Claude/Cursor/Codex): need the schema in `.claude/rules/docs.md` written explicitly so they follow ingest/query/lint correctly.
- BMAD: existing skills (`bmad-document-project`, `bmad-update-project-docs`) keep working; the new system layers under them.

### Success Metrics and KPIs

(Drawn from §4.8 NFRs; measurable):
- **Drift latency** ≤24h (scheduled lint catches; lint report attaches a "stale pages" count).
- **Doc-mirror latency** ≤5 min (AzDO pipeline duration).
- **LLM cost** <$10/month (GitNexus regen + ingest + lint combined; tracked in monthly review).
- **Schema-file load size** <10k tokens (measured: AGENTS.md + lazy-loaded `.claude/rules/<topic>.md`).
- **Hallucination escape** flagged within 1 week (lint cross-checks `sources:`; contradictions count = 0 target).
- **Multi-audience coverage** = each audience has a native surface (binary: A=2/4 audiences served, B=2/4, C=4/4).
- **Frontmatter compliance** = 100% on `/docs/**/*.md` (pre-commit gate; baseline failure rate ≤5% pre-W1).

---

## Research Synthesis

### Executive Summary

The homelab has working pieces for documentation — GitNexus indexing every commit, Graphiti capturing temporal decisions, BMAD generating `/docs/` baselines, Claude auto-memory accumulating operator learnings — but no single layer that turns those into a wiki readers (PM, PO, devs, customers, AI agents) can rely on as current. The gap is not tooling, it's the **maintenance loop and the source-of-truth topology**: each fact-type has multiple homes today, and the wiki layer drifts because no one is responsible for keeping it synthesized.

This research surveyed the current state of doc-system technology (10 SSGs, 6 wiki-style systems, the AGENTS.md/CLAUDE.md cross-tool spec landscape, and the Karpathy LLM-Wiki primary source), audited the homelab's existing stack including the GitNexus Code Wiki feature flagged by the user, and produced a non-biased comparison of six doc-system patterns (P1 docs-as-code, P2 BMAD-structured, P3 DevOps wiki, P4 KG-only, P5 RAG chat, P6 Karpathy LLM-Wiki) against the constraints actually in scope. Three deployable architectures emerged (A: AzDO Wiki only, B: Obsidian + Quartz, C: hybrid with all consumption surfaces sharing one git source-of-truth), with concrete tooling, ADR drafts, hook scripts, lint configs, mirror CI recipes, and a 4-week migration plan in §5.

The recommendation is **Architecture C (hybrid)**: keep the markdown in git as the canonical source; mirror one-way to Azure DevOps Wiki for SSO-gated audiences (free via existing Sparkle-CPS tenant); use Obsidian as the operator's IDE via `obsidian-git`; expose the same MD via an MCP server to Cursor/Continue/future LLM clients; optionally publish a Quartz v4 static site behind Tailscale for customer access. Reference docs are auto-generated by `gitnexus wiki` (OSS, free for non-commercial); narrative/decision docs are co-maintained by the operator and Claude Code agents on Karpathy's ingest/query/lint loop. **Architecture C is recommended only if the operator accepts ~4 weeks of evening work and a ≤$10/month LLM bill; if either constraint binds harder, Architecture A is the honest fallback.**

### Key Findings

1. **The "who maintains it" problem is the binding constraint** — not tool choice. P1/P2/P3 patterns all hit the same wall (humans abandon doc maintenance). Karpathy's LLM-Wiki pattern (P6) explicitly solves this by making the LLM the maintainer, with the human as curator and reviewer. *(§C.6, §C.7)*
2. **"LLM-Wiki" is a pattern, not a product** — Karpathy's gist is the canonical spec; downstream OSS implementations exist (`Pratiyush/llm-wiki`, `kfchou/wiki-skills`, etc.) but cluster at 60–700 stars. The pattern maps almost 1:1 onto the homelab's existing stack with `CLAUDE.md` already filling the schema role. *(§C.6, §C.8)*
3. **Diátaxis is the IA spine** — verified adoption by Django, Cloudflare, GitLab, NumPy, FastAPI. Cleanly maps the four quadrants to the homelab's mixed audiences (Tutorials/How-to → users/PM/operator; Reference → devs/agents; Explanation → all). *(§4.1)*
4. **GitNexus Code Wiki (OSS) is a high-leverage, low-effort win** for the Reference quadrant — already running, license-clean for the homelab (PolyForm-NC), auto-generates per-module pages from the knowledge graph. Auto-update is enterprise-only but trivially recreated with a SessionEnd hook. *(§C.9)*
5. **The current root `CLAUDE.md` is at risk of the 1,094-line `claude-flow`/ruflo anti-pattern** — refactor to Astral stub-redirect (`CLAUDE.md → AGENTS.md`) + Cline manifest split (`.claude/rules/<topic>.md`) for cross-tool portability and lazy-loading via the `InstructionsLoaded` hook. *(§C.8, §4.4, ADR-003)*
6. **Source-of-truth topology must be formalized** — every fact-type gets exactly one authoritative home, every consumer is one-way read-only. Without this rule the wiki drifts across surfaces and merge conflicts follow. *(§4.2, ADR-002)*
7. **Existing GitNexus and Claude Code hooks already provide the integration backbone** — the homelab's `~/.claude/settings.json` is wired for hooks, GitNexus reindexes on every commit, the 13 Claude Code hook events cover ingest/query/lint cleanly. The doc system layers on, doesn't replace. *(§3.5)*
8. **The two on-disk wiki scaffolds (`homelab-playbook/wiki/` Diátaxis layout, `homelab/wiki/` Karpathy three-layer) are tests** per user clarification 2026-04-27 — the migration plan starts from the BMAD-generated `/docs/` baseline, not from those scaffolds. *(§C.9.3)*

### Architecture Recommendation

**Recommended: Architecture C (hybrid).**

Rationale:
- **Multi-audience coverage is binding for this user** — the goal explicitly names PM, PO, devs, customers, users. Architecture A serves only PM/PO/devs (AAD-gated); Architecture B serves only operator + public. C is the only one that serves all four with each audience getting its native surface.
- **Existing stack alignment** — GitNexus, Graphiti, BMAD, Claude Code are all *already* aligned with the markdown-in-git pattern. C exploits this; A and B leave value on the table.
- **Lock-in containment** — every consumer in C is independently replaceable (drop AzDO mirror → still have Obsidian + Quartz; drop Quartz → still have AzDO; drop MCP server → write a 100-line replacement). The composition tax buys low lock-in.
- **Operator cognition** — Obsidian as IDE preserves Karpathy's "wiki as codebase" thinking-surface advantage that A loses entirely.

Trigger to fall back to **Architecture A** instead:
- Customer audience drops out of scope (no need for Quartz).
- Time budget < 2 weeks (skip B/C composition; ship just the AzDO mirror).
- LLM cost > €10/month becomes a hard ceiling (shed the GitNexus regen + ingest loop).

Trigger to fall back to **Architecture B** instead:
- PM/PO/customers stop being primary audiences (only operator + public matter).
- AzDO tenant changes (Sparkle-CPS access ends).

### Top Strategic Recommendations

1. **Lock in markdown-in-git as single source-of-truth (ADR-002).** All other decisions cascade from this. *Cost: 0 — it's a decision, not a build.*
2. **Refactor `CLAUDE.md` to `@AGENTS.md` stub + Cline topic split (ADR-003).** Two reversible passes, ~half-day total. Cheapest single highest-leverage architectural change. *Cost: 30 min + 2–3 hrs.*
3. **Add the frontmatter spec (ADR-005) to all `/docs/` files** — gates provenance, multi-audience filtering, lint, drift detection. *Cost: 30 min one-time + ~5 sec per new file.*
4. **Wire the SessionEnd ingest hook (§5.3.1) and the PostToolUse log.md hook (§5.3.2)** as the foundation of the Karpathy loop. Async runner consumes the queue, decoupling Claude Code shutdown from LLM cost. *Cost: ~2 hrs.*
5. **Run `gitnexus wiki --review` against `homelab-playbook` first** (smallest repo, BMAD baseline already current) to evaluate auto-generated reference docs before committing to the integration. *Cost: ~5 min wall-clock + small LLM bill.*
6. **Set up the scheduled weekly lint cron (§5.3.3)** before any other work — it's the safety net that catches every other failure mode silently. *Cost: 30 min.*
7. **Adopt Diátaxis IA (ADR-001) and migrate the existing 8 BMAD-generated docs into quadrant folders** — `tutorials/`, `how-to/`, `reference/`, `explanation/`. Reversible. *Cost: ~1 hr.*

### Implementation Roadmap

Detailed in §5.9. The critical path is architecture-agnostic for the first two weeks; architecture-specific work parallelizes from week 3:

- **Week 1** (foundation): schema split + frontmatter + log.md + JSON Schema validation. **Reversible at every step.**
- **Week 2** (loop): hooks + Diátaxis migration + lint stack (markdownlint, lychee, Vale).
- **Week 3** (test): GitNexus wiki test on `homelab-playbook` + scheduled lint cron + (architecture-specific) AzDO mirror or Obsidian vault.
- **Week 4** (polish): Quartz / MCP server (architecture C only) + ADR backfill.
- **Week 4+** (ongoing): scheduled lint reports drive cleanup; LLM-Wiki ingest loop runs on every Claude Code session.

Total wall-clock: ~4 weeks at evening cadence; ~30–40 hours of operator effort.

### Critical Risks

From §5.10, the three highest-impact:

1. **Hallucinated synthesis** (LLM writes a clean, well-cited page that's subtly wrong). *Mitigation:* lint pass cross-checks `sources:` frontmatter; monthly review of `owner: llm` pages; ADR-005 frontmatter is non-optional.
2. **GitNexus single-maintainer abandonment**. *Mitigation:* pin Docker image SHA; archive locally; existing OSS license keeps current version usable indefinitely.
3. **Operator authoring drift** (humans skip frontmatter, log.md). *Mitigation:* pre-commit hook is the gate; soft-fail with warning the first month, hard-fail after.

### Open Decisions (still need operator commitment)

These are *not* answered by the research; they require explicit choice in the first ADR-writing session:

| Decision | Options | Default if not answered |
|---|---|---|
| **ADR-004 architecture pick** | A / B / C | C (per §6 recommendation) |
| **Customer audience in-scope?** | Yes (Quartz) / No (skip Quartz) | No until a concrete customer audience exists |
| **Workspace-level wiki location** | `homelab-playbook/wiki/` / new top-level `wiki/` | `homelab-playbook/wiki/` (matches existing `wiki-query` skill) |
| **AzDO project for the wiki** | Existing Sparkle-CPS / new "homelab" project | New "homelab" project (separates concerns from CPS work) |
| **GitNexus regen cadence** | Every commit / Daily / Weekly / On-demand | Weekly (cron) + on-demand for full passes |
| **`obsidian-git` or filesystem-only?** | Plugin / pure git | Plugin (committed atomically per session) |

### Next Steps

1. **Read this document end-to-end once.** 30 min.
2. **Decide the open questions in the table above** in a 15-min ADR-writing session. Commit ADR-001 through ADR-010 as drafts.
3. **Execute Week 1 of §5.9** — schema split + frontmatter + log.md + JSON Schema. ~2 hours, fully reversible.
4. **Re-evaluate after Week 1** before proceeding. If the foundation feels solid, continue with Week 2; if not, the only sunk cost is ~2 hours.
5. **Schedule a 2-week checkpoint** (suggest using `/schedule` skill to remind in 14 days) to assess whether the loop is actually reducing maintenance burden, or if the LLM-Wiki pattern is producing more lint noise than value. Honest pivot point.

### Table of Contents

1. **Technical Research Scope Confirmation** — research goals, scope, methodology, confirmation
2. **Technology Stack Analysis (§A–C)** — current homelab audit; landscape survey (10 SSGs, formats, diagrams, adoption signals); consumption-layer comparison (DevOps wikis, Obsidian, "LLM-Wiki" investigation); Karpathy LLM-Wiki primary-source addendum; non-biased pattern comparison; Claude-Code-oriented OSS landscape; **GitNexus Code Wiki direct evaluation**
3. **Integration Patterns Analysis** — five trigger sources; source-flow topology; consumption fan-out; cross-tool schema; Claude Code hook lifecycle (verified 2026-04-27); conflict resolution; provenance/citation spec; failure modes; build-order
4. **Architectural Patterns and Design** — Diátaxis as IA spine; source-of-truth topology; concrete file/folder layouts (per-repo + workspace); finalized frontmatter spec; schema architecture (Astral + Cline); three architectures made implementation-ready; ADRs to draft; cross-cuts; NFRs
5. **Implementation Approaches** — bill of materials (concrete tools, license, cost); ADR drafts (3 fully drafted, 7 skeletons); hook script implementations; lint configs; mirror CI recipes; GitNexus integration; MCP doc server; llms.txt generator; 4-week migration plan; risk table
6. **Research Synthesis** — executive summary; key findings; architecture recommendation with fallback triggers; top recommendations; roadmap; critical risks; open decisions; next steps

### Methodology and Source Verification

**Subagent dispatches** (3): doc-system technology landscape; DevOps-wiki vs Obsidian vs LLM-wiki comparison; Claude-Code-oriented documentation OSS landscape. Each returned ≤2500-word structured reports with citations.

**Primary-source reviews** (1): Karpathy "LLM Wiki" gist (https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) — fetched verbatim, integrated as §C.6 with explicit bias-correction in §C.7.

**Direct CLI/system inspection**: GitNexus container CLI (`docker exec gitnexus`), local hook scripts, MCP config, `.claude/settings.json`, existing `/docs/` baseline.

**Web verifications** (selected): Claude Code hooks reference 2026-04-27, GitHub repo star counts and recency 2026-04-27, llms.txt spec, AzDO Wiki file structure docs, Diátaxis spec, MADR 4.0 ADR template.

**Cross-references to prior homelab research** (avoided re-treading):
- `technical-incremental-docs-autoresearch-2026-04-03.md`
- `technical-llm-knowledge-management-research-2026-04-11.md`
- `technical-graphify-evaluation-2026-04-25.md`
- `technical-memory-systems-evaluation-2026-04-25.md`
- (Auto-memory entries on PVE9 HA, Tailscale defaults, single-vendor preference, etc.)

**Confidence levels**: claims are tagged `[verified]` (multi-source), `[anecdotal]` (single source or pattern observation), `[vendor-claim]` (marketing copy, treat skeptically), `[2023-or-earlier]` (pre-current data, may be stale). The recommendation in §6 is grounded in `[verified]` claims; the architecture choice depends on `[anecdotal]` operator-cost projections that should be re-validated after Week 1.

**Limitations**:
- LLM cost projections (~$5–10/month) are extrapolated from per-call estimates × homelab volume; not measured. Re-baseline after first month of operation.
- Hallucination escape rates for the Karpathy LLM-Wiki pattern at homelab scale are anecdotal — no published case studies at this scale. Lint pass design is a hedge.
- GitNexus Code Wiki output quality on the homelab's specific repos has not been measured — §5.6 step is the test.

---

**Research Completion Date:** 2026-04-27
**Document Author:** tomamourette
**Workflow:** BMAD Technical Research v6.2.2
**Final Status:** Synthesis complete; six open decisions resolved 2026-04-27 (see "Architecture Decisions Locked" below).

---

## Architecture Decisions Locked (resolved 2026-04-27)

### Decision Record

| # | Decision | Resolution |
|---|---|---|
| **D1** | ADR-004 architecture pick | **Architecture C (hybrid)** |
| **D2** | Customer audience in-scope? | **Yes** — customer-facing surface is required |
| **D3** | Workspace-level wiki location | **`homelab-playbook/wiki/`** (operator/internal SoT, per default) |
| **D4** | Customer-facing wiki location | **Per-project conditional** (see below) |
| **D5** | GitNexus regen cadence | **Weekly + on-demand + on git PR/merge** |
| **D6** | Obsidian sync method | **`obsidian-git` plugin** |

### D4 Refinement — Two-layer wiki split (load-bearing)

The customer-facing wiki is **not the same surface** as the operator/internal wiki. Conditional rule:

- **For projects backed by an Azure DevOps tenant** (e.g., Sparkle-CPS): the customer wiki is the **AzDO Wiki repo** in that project's workspace (project-scoped, AAD-gated).
- **For projects without an AzDO tenant** (e.g., the homelab itself): the customer wiki is `/wiki/` at the **workspace root** (`/home/developer/workspace/homelab/wiki/`), **NOT nested in `homelab-playbook/`**.

The customer wiki is **synthesized from the operator wiki**, not authored directly. A new skill (call it `wiki-publish-audience` or `bmad-publish-customer-wiki`, name TBD in implementation) reads from `homelab-playbook/wiki/`, applies an audience filter (frontmatter `audience` field per §4.3.3), and writes to the customer surface. The skill is configurable per audience, enabling different tones / depths / redactions for PM vs customer vs public-marketing.

This **resolves the customer-audience gap** previously open in Architecture A (§C.5) without falling into the trap of letting customers/PM edit the SoT directly. The customer wiki is always derived; the operator wiki is always authoritative.

### Refined Source-of-Truth and Consumption Topology (post-decisions)

```
┌─────────────────────────────────────────────────────────────────┐
│  AUTHORITATIVE STORES (each fact-type has ONE home)             │
├─────────────────────────────────────────────────────────────────┤
│  Code / config       → git repo                                 │
│  Live code structure → GitNexus knowledge graph                 │
│  Temporal decisions  → Graphiti episodes/facts                  │
│  Operator learnings  → Claude auto-memory                       │
│  Formal artifacts    → BMAD outputs (_bmad-output/)             │
│  External sources    → /raw/                                    │
│                                                                 │
│  Operator/Internal   → homelab-playbook/wiki/  ◄── PRIMARY      │
│  WIKI (full content)                            wiki SoT        │
│                          per-repo /docs/  ◄── REPO-LOCAL SoT    │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼ (one-way fan-out, audience-filtered)
┌─────────────────────────────────────────────────────────────────┐
│  CUSTOMER / AUDIENCE-TUNED SURFACES (synthesized, NEVER write)  │
├─────────────────────────────────────────────────────────────────┤
│  homelab (no AzDO):       /wiki/  at workspace root             │
│  AzDO-backed projects:    AzDO Wiki repo in project's workspace │
│                                                                 │
│  Synthesis tool: wiki-publish-audience skill                    │
│    - Reads:   homelab-playbook/wiki/ (operator SoT)             │
│    - Filters: by frontmatter audience field                     │
│    - Writes:  customer surface (workspace /wiki/ OR AzDO Wiki)  │
│    - Config:  per-audience (customer / PM / public)             │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼ (additional read-only consumers, unchanged)
              ┌──────────────┼──────────────┬──────────────┐
              ▼              ▼              ▼              ▼
         Obsidian      Quartz site*    docs-mcp-server  llms.txt
         (operator)    (optional)      (Cursor/Cont.)   (LLM crawl)
         via obsidian-git                 (AI agents)
```

*Quartz now becomes optional — its job (public-readable static site) is partially absorbed by the customer-wiki skill writing to workspace `/wiki/`. Quartz still useful if a static-rendered HTML version is desired (then build from `/wiki/`, not from operator SoT).

### Updated Folder Layout (post-D4)

```
/home/developer/workspace/homelab/
├── CLAUDE.md                               # @AGENTS.md (Astral stub)
├── AGENTS.md                               # canonical schema (~80–120 lines)
├── llms.txt                                # site-root manifest
├── .claude/rules/                          # Cline split (lazy-loaded)
│   └── docs.md, general.md, security.md, ...
│
├── wiki/                                   # ◄── NEW: customer-facing wiki
│   ├── index.md                            # public-friendly entry
│   ├── tutorials/, how-to/, reference/...  # Diátaxis, audience-filtered subset
│   └── _meta/last-sync.json                # provenance: synthesized from playbook on <date>
│
├── homelab-playbook/
│   └── wiki/                               # ◄── operator/internal SoT
│       ├── _schema.md
│       ├── index.md
│       ├── log.md
│       ├── architecture/, decisions/, glossary/, projects/, runbooks/
│       └── raw/
│
├── homelab-infra/
│   └── docs/                               # repo-local Diátaxis /docs/
├── homelab-apps/
│   └── docs/
└── homelab-playbook/
    └── docs/                               # ditto
```

For an AzDO-backed project (e.g., Sparkle-CPS), the equivalent shape is:

```
<workspace>/
├── homelab-playbook-equivalent/wiki/       # operator SoT (still authoritative)
└── (AzDO Wiki repo in project, NOT in workspace tree)  # customer surface
```

The skill knows to push to AzDO Wiki via REST + git push to `wikiMaster` instead of writing to a local `/wiki/` folder.

### `wiki-publish-audience` Skill — design sketch (full impl in Step 5+)

Add to `.claude/skills/wiki-publish-audience/`:

```yaml
---
name: wiki-publish-audience
description: 'Synthesize an audience-tuned wiki from the operator playbook wiki. Use when the user says "publish customer wiki", "update customer wiki", "sync wiki for <audience>".'
---
```

Workflow:
1. Read `homelab-playbook/wiki/` recursively (or per-project equivalent).
2. Filter pages by frontmatter `audience` containing the target audience (e.g., `customer`, `pm`, `public`).
3. For each page, apply an audience-tuned transform (LLM call):
   - Strip operator-only sections (marked `audience: [operator]`).
   - Soften technical jargon for `customer` / `public`.
   - Remove credentials, internal hostnames, tailscale-only references.
   - Inject audience-appropriate intro / TOC.
4. Write to target surface:
   - Local: `<workspace>/wiki/` for non-AzDO projects.
   - AzDO Wiki: git push to `wikiMaster` branch for AzDO projects (uses existing AzDO REST/git auth).
5. Commit with a `wiki-publish: customer @ <SHA>` message; update `_meta/last-sync.json`.
6. Configurable via `.claude/rules/wiki-audience.md` — operator can fine-tune per audience without editing the skill.

The skill is **a single source-flow** (operator SoT → audience-filtered customer surface). It reuses the §3.7 frontmatter spec; the `audience: []` array drives every filtering decision.

### D5 Refinement — GitNexus regen on PR/merge

The original default (weekly + on-demand) is upgraded to also trigger on git PR open and merge. Implementation:

- **On PR open** (GitHub Action / AzDO Pipeline): trigger `gitnexus analyze` on the PR's HEAD commit; post a comment summarizing changed symbols and impacted wiki pages (using `mcp__gitnexus__detect_changes` + `impact`). Helps reviewers understand wiki-doc impact before merge.
- **On merge to main**: trigger `gitnexus analyze` + conditional `gitnexus wiki` regen (only if changed-symbol set crosses a delta threshold; full repo refresh on weekly cron).
- **Hook script**: extend the existing post-commit `gitnexus/post.sh` with a branch check — if the merge commit lands on `main` AND files in `<repo>/src` or `<repo>/terraform` changed, queue a `gitnexus wiki` regen via the same async runner used for SessionEnd ingest (§5.3.1).

This closes the "code merged but reference docs stale" gap.

### Implementation Roadmap Update (post-decisions)

Insert into the W3 row of §5.9:

| Week | Added task | Cost |
|---|---|---|
| **W3** | Build `wiki-publish-audience` skill (D4) — workflow.md + audience-config rules | 4–6 hrs |
| **W3** | Initialize empty `<workspace>/wiki/` with audience-filtered index | 30 min |
| **W3** | Wire on-PR + on-merge GitNexus regen (D5) into existing `gitnexus/post.sh` | 1–2 hrs |
| **W4** | First customer-wiki publish run; iterate audience filter quality | 2–3 hrs + LLM bill |
| **W4** | Cross-project test: dry-run the skill against a Sparkle-CPS-shaped layout (AzDO target) | 2 hrs |

Total added: ~10–15 hrs over W3–W4. Architecture C with customer audience is now ~40–55 hrs of operator effort total (vs original ~30–40).

### ADR-004 — drafted (architecture C with customer-wiki layer)

```markdown
# ADR-004: Adopt Architecture C (hybrid) with two-layer wiki split

- Status: accepted
- Date: 2026-04-27
- Deciders: tomamourette
- Supersedes: n/a

## Context

Multi-audience documentation (operator, dev, PM, PO, customer, AI agents) requires
either a single surface that serves all (lock-in / leak risk) or composed surfaces
sharing a single SoT. Three architectures considered (A: AzDO only; B: Obsidian
+ Quartz; C: hybrid). Customer audience is in scope (D2).

## Decision

Adopt Architecture C with a two-layer wiki split:

1. **Operator/Internal wiki** at `homelab-playbook/wiki/` is the canonical SoT
   for narrative/decisions/runbooks. Per-repo `/docs/` is the per-repo SoT.
2. **Customer-facing wiki** is synthesized from the operator wiki via the
   `wiki-publish-audience` skill. Target surface depends on project context:
   - Projects with AzDO tenant: push to AzDO Wiki repo (`wikiMaster` branch).
   - Projects without AzDO: write to `<workspace>/wiki/` at workspace root.
3. The customer wiki is never authored directly; only synthesized.
4. Operator surface = Obsidian via `obsidian-git` (D6).
5. AI-agent surface = `docs-mcp-server` over the operator wiki + `/docs/`.
6. GitNexus regen cadence: weekly + on-demand + on PR open + on merge to main (D5).

## Consequences

- Positive: every audience gets its native surface from a single SoT.
- Positive: customer surface can be tuned per audience without operator-wiki risk.
- Positive: AzDO-backed projects and pure-homelab projects share the same model
  with only the customer-target backend swapped.
- Negative: ~10–15 extra hours to build `wiki-publish-audience` skill; ~$2–4/month
  added LLM cost for audience-filter passes.
- Negative: 5+ surfaces means more failure-mode points; mitigated by §3.8 fallbacks
  and §5.10 risk register.
- Reversible: each surface can be disabled independently. Falling back to A or B
  is a deletion of the relevant CI job(s), not a rewrite.
```

### Open items still requiring action (none architectural; all execution)

1. Run Week 1 of §5.9 (foundation: schema split + frontmatter + log.md + JSON Schema) — ~2 hrs, fully reversible.
2. Then re-evaluate before W2 commits.
3. Decide skill name: `wiki-publish-audience` vs `bmad-publish-customer-wiki` vs alternative — at first implementation session.
