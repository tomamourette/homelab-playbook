---
title: "Product Brief Distillate: AI Dev Container"
type: llm-distillate
source: "product-brief-ai-dev-container.md"
created: "2026-04-02"
purpose: "Token-efficient context for downstream PRD creation"
---

# Product Brief Distillate: AI Dev Container

## Rejected Ideas

- **Cloud ephemeral containers (Azure, Cloudflare, DevPod) for worker isolation** — Research concluded local git worktrees are simpler, faster, and free. Cloud containers deferred to future scale-out option only if homelab capacity is exceeded.
- **OpenClaw as orchestrator** — General-purpose AI assistant platform deployed on Proxmox LXC, not optimized for coding workflows, no git worktree orchestration, no cross-project persistent developer memory. Hermes Agent selected instead for its skills system, cron scheduling, subagent spawning, and MCP support.
- **Cloud-hosted memory (memctl, OneContext, UnifiedMemory.ai)** — SaaS models incompatible with consulting data sovereignty requirements. OMEGA Memory selected for local-first SQLite+MCP approach with no cloud dependency.
- **OMEGA Pro for MVP coordination** — File/branch locking and task queues are Pro-only features. Free tier + git worktree isolation should suffice for MVP. Revisit in Phase 2 if collision issues arise.
- **DBOS crash recovery in MVP** — Deferred to Phase 2. MVP focuses on proving each service works standalone before adding durable execution complexity.
- **GEPA self-learning in MVP** — Deferred to Phase 2. Requires measurable evaluation metrics and ~100 lines of Python adapter code. Batch optimization runs overnight.

## Requirements Hints

- Each tool must be installable and testable independently before integration
- Ansible role(s) must be idempotent and rerunnable for reproducible setup
- MVP needs a lightweight integration smoke test: Director triggers a task that uses OMEGA Memory context
- Hermes Agent quick-dev task (e.g., write Proxmox documentation) must complete end-to-end without human intervention after initial command
- OMEGA Memory must demonstrate context persistence: start session, work, end, start new session, confirm prior context surfaces automatically
- tmux sessions must survive laptop disconnect and SSH drop — verify by killing connection mid-session
- SQLite backup schedule for OMEGA Memory database required from day one
- Process limits for workers to prevent runaway spawning
- Per-project OMEGA namespaces for multi-client data isolation
- Phase 2: Slack, email, and MCP integrations (e.g., Granola for meeting transcripts) as information source inputs to the Director
- Phase 2: Memory curation strategy across all tools beyond OMEGA's built-in dedup/TTL
- Phase 2: Fresh container validation — spin up new LXC, run Ansible roles, confirm full stack works from scratch

## Technical Context

### Target Environment
- Proxmox homelab: 2-node cluster (pve1: N305/48GB, pve2: N100/48GB), 4 containers, 19 Docker stacks, 40+ services
- Target container: similar to ct-dev-homelab (VMID 150, 2C/8GB) on pve2
- Provisioned via Terraform + Ansible; three-repo model: homelab-infra, homelab-apps, homelab-playbook
- Existing services available: PostgreSQL (n8n), CouchDB (Obsidian sync), full observability stack (Prometheus, Grafana, Loki)

### Tool Stack — Setup and Requirements

**OMEGA Memory (shared brain)**
- Python 3.9+, ~337MB RAM at runtime, 90MB ONNX embedding model (one-time download)
- Setup: `pip install omega-memory[server] && omega setup && omega doctor`
- 25 MCP tools, 7 Claude Code hooks (SessionStart briefing, UserPromptSubmit capture, PostToolUse memory surfacing, SessionStop summary)
- Multi-layered search: 384-dim vector embeddings (sqlite-vec) + FTS5 + type-weighted scoring + contextual re-ranking
- Auto-deduplication: SHA256 exact match + semantic similarity (0.85+ threshold)
- Memory evolution: related content (55-95% similar) appends to existing memories
- TTL policy: session summaries expire after 1 day; lessons persist indefinitely

**Hermes Agent (Director/orchestrator)**
- Requires git only; installer handles Python 3.11 + Node.js
- Setup: `curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash && hermes setup`
- Config: `~/.hermes/` with config.yaml, .env, SOUL.md, memories/, skills/, cron/, sessions/
- Hard limits: 2,200 char MEMORY.md, 1,375 char USER.md, 90 max turns per session
- Terminal config: backend=local, cwd=/home/developer/workspace/homelab, timeout=180, persistent_shell=true
- Delegation model: claude-sonnet via Anthropic
- External skill dirs: point to BMAD implementation folder
- Skills to create: bmad-sprint-director, bmad-story-pipeline, bmad-escalation, bmad-worktree-manager

**claude-tmux (monitoring TUI)**
- Rust/Cargo build: `cargo install claude-tmux`
- tmux keybinding: `bind-key C-c display-popup -E -w 80 -h 30 "~/.cargo/bin/claude-tmux"`
- Status indicators: filled circle=Working, empty=Idle, half=Waiting, question=Unknown

**DBOS (Phase 2 — crash recovery)**
- Python 3.9+ and PostgreSQL
- Setup: `pip install dbos 'fastapi[standard]' && dbos init`
- Wraps functions with @DBOS.workflow()/@DBOS.step() for checkpoint-based recovery
- Human-in-the-loop: DBOS.recv() waits durably for user response, survives restarts

**GEPA (Phase 2 — skill optimization)**
- Python 3.9+ and LLM API access, no GPU
- Setup: `pip install gepa`
- 5-step loop: SELECT candidate -> EXECUTE on sample -> REFLECT (LLM reads traces) -> MUTATE improved variant -> ACCEPT if improved
- BMAD adapter: ~100 lines Python, composite score (story completeness + test pass rate + review findings + time)
- Proven: 24% -> 93% resolve rate on coding benchmarks; skills learned on cheap models transfer to stronger ones
- Cost: ~$0.20-1.00 per optimization run (200 evals)

### Architecture Patterns
- Confidence-based escalation: >=90% worker decides autonomously, 70-89% worker asks Director, <70% Director escalates to user (threshold is heuristic, needs calibration in Phase 2)
- Parallelization: stories across different epics=parallel, stories in same epic=conditional, dev-story+code-review=always sequential
- Ralph Loop pattern: implement -> validate -> commit -> reset context -> next task (avoids context overflow)
- 3-5 agents sweet spot, 5-6 tasks per agent, MAX_ITERATIONS=8 before forced reflection
- Git worktree isolation: each worker gets own worktree (feat/1-1, feat/2-1 etc.), OMEGA coordinates file claims
- sprint-status.yaml: Director-only writes, workers update story files, Director syncs status

## Competitive Intelligence

### Direct Competitors (all have gaps)
- **Conductor** — Mac desktop app for parallel Claude Code agents with visual dashboard. Gaps: Mac-only, no server-side persistence, no shared memory across projects, no LXC/homelab support, no always-on capability.
- **cmux** — 7,700 GitHub stars in first month (Feb 2026). Mac-only tmux-based multi-agent workflows. Gaps: no session restore, no memory layer, no container templating.
- **Parallel Code / Composio Agent Orchestrator** — Desktop/CLI tools giving each agent its own git worktree. Gaps: ephemeral sessions, no persistent memory, no server-side operation.
- **tmux-agents / NTM** — Scripts to spawn AI agents in tmux sessions. Gaps: no integrated memory, no container templating, no cross-project learning, manual setup per machine.

### Memory-Only Competitors
- **memctl** — Shared memory for AI coding agents scoped by org/project/branch, synced via MCP. Cloud-hosted SaaS.
- **OneContext** — Persistent context layer for AI coding agents. Cloud-hosted.
- **UnifiedMemory.ai** — Persistent memory for coding agents. Cloud-hosted.
- All cloud SaaS with no self-hosted option, memory-only (no orchestration or session persistence).

### Adjacent Market
- VS Code 1.109 (Feb 2026) branded itself "the home for multi-agent development" — mainstream IDE adoption of multi-agent orchestration
- DevContainer.ai auto-generates devcontainer.json from repo analysis but doesn't bundle agent orchestration or persistent memory
- Cloud AI IDEs (Cursor, Windsurf, GitHub Copilot Workspace) are the budget competitors — positioned against them on data sovereignty, full customization, no vendor lock-in

### Market Signals
- No existing product combines all four pillars (always-on director, persistent cross-project memory, container templating, multi-agent coding orchestration)
- "Proxmox + AI dev environment as LXC template" intersection is essentially unoccupied
- Strong user demand for "code while you sleep" workflows and persistent sessions
- Self-hosted alternative fills gap for consultants handling client code with data sovereignty requirements

## Reviewer Findings Worth Preserving

### Skeptic (risks to address in PRD)
- Upstream tool abandonment risk is HIGH — Hermes, OMEGA, claude-tmux are community projects
- Context window saturation risk — injecting OMEGA context + BMAD methodology + project context could crowd the window and degrade output quality
- Git worktree concurrency — shared .git directory can cause lock contention under concurrent operations
- MVP-Phase 2 gap — MVP proves parts work but doesn't validate the integrated system solves the stated problem (mitigated by adding lightweight integration smoke test)
- Compound learning is aspirational — no mechanism described for pruning stale knowledge or measuring recall accuracy improvement (deferred to Phase 2 memory curation)

### Opportunity (value to capture in PRD)
- Cross-project knowledge graph becomes a proprietary asset over time — queryable anonymized patterns, architecture decisions, failure modes
- "Terraform for AI agents" framing resonates with IaC community
- Open-sourcing the Ansible roles could drive community adoption while keeping proprietary memory/skills private
- BMAD methodology integration creates a natural adoption funnel — every BMAD user needs this container
- Offline-first positioning unlocks premium consulting markets (defense, healthcare, finance with strict data residency)

### Developer Experience (friction to plan for)
- 5 separate tools with different config formats (YAML, TOML, .env, Rust build) — setup complexity is real
- Debugging multi-tool stack failures requires understanding each tool's internals — consider unified health check
- Value curve varies by component: tmux=immediate, OMEGA=after few sessions, Director=after skills are written

## Scope Signals

### Definitely MVP
- tmux + claude-tmux (immediate value, simplest to set up)
- OMEGA Memory with Claude Code hooks (core differentiator)
- Hermes Agent basic installation and config
- One quick-dev end-to-end test
- Ansible role(s) for reproducibility
- Lightweight integration smoke test

### Definitely Phase 2
- Full BMAD story pipeline orchestration
- Parallel worker coordination
- DBOS crash recovery
- GEPA skill optimization
- Slack/email/Granola MCP integrations
- Memory curation beyond OMEGA built-ins
- Fresh container validation
- Obsidian integration

### Definitely Later / Out of Scope
- Cloud scale-out (DevPod, Azure, Codespaces)
- Container marketplace / template sharing
- Multi-user / team support

## Open Questions

- What is the exact confidence threshold for the Director's escalation model, and how will it be calibrated? (Research states 90% but has no empirical basis)
- Should OMEGA Pro be purchased for file/branch locking, or is free tier + worktree isolation sufficient? (Test in MVP, decide for Phase 2)
- What is the minimum container spec (CPU/RAM/disk) for running the full stack? (Needs benchmarking during MVP)
- How should the Director handle Hermes Agent's 90 max turn limit during long workflows? (Subagent calls + /compress as workarounds per research)
- What happens when upstream tools ship breaking changes? (Version pinning strategy needed in PRD)

## Cost Model

- Monthly API estimate: $50-150 (3 parallel workers, 4h/day, 20 days, model mix)
- Infrastructure: $0 (runs on existing homelab hardware)
- Tools: $0 (all open source; OMEGA Pro optional)
- GEPA overnight optimization: ~$1-5 per run
- One-time setup: ~337MB RAM for OMEGA, ~100MB for Hermes, Rust build for claude-tmux
