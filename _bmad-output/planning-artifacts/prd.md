---
stepsCompleted:
  - step-01-init
  - step-02-discovery
  - step-02b-vision
  - step-02c-executive-summary
  - step-03-success
  - step-04-journeys
  - step-05-domain-skipped
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
  - homelab-playbook/_bmad-output/planning-artifacts/product-brief-ai-dev-container.md
  - homelab-playbook/_bmad-output/planning-artifacts/product-brief-ai-dev-container-distillate.md
  - homelab-playbook/_bmad-output/planning-artifacts/research/technical-ephemeral-cloud-containers-research-2026-03-31.md
  - docs/index.md
  - docs/project-overview.md
  - docs/architecture-homelab-playbook.md
  - docs/integration-architecture.md
workflowType: 'prd'
documentCounts:
  briefs: 2
  research: 2
  projectDocs: 3
  projectContext: 0
lastEdited: '2026-04-11'
editHistory:
  - date: '2026-04-11'
    changes: 'Phase 2b Knowledge Management: added FR53-FR62 (LLM Wiki, Obsidian, MemPalace, Linear/Granola/Azure DevOps ingestion), Phase 2b success criteria, split Phase 2 into 2a (Growth) and 2b (Knowledge Management), updated MVP exclusions. Per SCP-knowledge-mgmt-2026-04-11.'
  - date: '2026-04-03'
    changes: 'Added BMAD Workflow Enhancements scope: FR43-FR52 (doc update skill, eval assertions, autoresearch), NFR-INT-5/6 (update-safety, independence), AT-6.1-6.8, updated MVP scope, executive summary, innovation section, installation architecture'
---

# Product Requirements Document - AI Dev Container

**Author:** tomamourette
**Date:** 2026-04-02

## Executive Summary

AI Dev Container is a reusable Proxmox LXC container template that provides an always-on AI development environment — a personal "Jarvis" for software projects. It solves a fundamental gap in the current AI-assisted development landscape: agents don't persist, don't remember, don't coordinate, and don't learn. The industry has focused on where agents run (cloud vs local); this project focuses on the agent lifecycle itself.

Built for a solo consultant running multiple client projects on a Proxmox homelab, the system eliminates three categories of waste: setup tax (hours re-installing tools per engagement), context loss (every session starts cold, every disconnect kills progress), and manual orchestration (the human becomes the bottleneck coordinating parallel agent work). The solution integrates five open-source tools into a single deployable unit: Hermes Agent as an always-on Director in tmux, OMEGA Memory as a persistent shared brain, Claude Code workers in isolated git worktrees, claude-tmux for real-time monitoring, and Ansible roles for reproducible provisioning.

The MVP (Phase 1) validates each service standalone on the existing homelab project container with a lightweight integration smoke test. As a prerequisite, the MVP also enhances the BMAD development workflow itself: an incremental documentation update skill keeps project docs current after each epic, eval assertions in story templates provide binary test criteria for implementation verification, and an autoresearch skill enables automated post-code-review fix loops. These workflow improvements are used during the MVP implementation and carry forward to all future projects. Phase 2 wires the AI dev tools together: the Director orchestrates full BMAD story pipelines, parallel workers coordinate via shared memory, and the system connects to information sources (Slack, email, Granola). The architecture is designed for compound learning — OMEGA Memory persists across projects, GEPA optimizes BMAD skills overnight, and each consulting engagement starts from a richer baseline than the last.

### What Makes This Special

**Always-on, not invoke-and-forget.** The Director runs 24/7 in tmux on the server. Queue a sprint before bed, review PRs over coffee. Laptop disconnects, SSH drops, browser closes — the system keeps working. No other solution in the market combines session persistence with agent orchestration and cross-project memory.

**Compound learning as a strategic asset.** Every session captures lessons, decisions, and patterns to OMEGA Memory. Every new session receives relevant briefings from accumulated knowledge. Skills self-optimize via GEPA's evolutionary prompt optimization. The system appreciates in value with every engagement — a proprietary knowledge graph that no competitor can replicate.

**Self-hosted and sovereign.** All memory, context, and coordination runs locally. No client code or project data leaves the infrastructure. This is not optional for consulting work with sensitive client codebases — it's a hard requirement that every cloud-hosted alternative (Cursor, Windsurf, memctl, OneContext) fails to meet.

**Infrastructure-as-code for the agent layer.** Codified as Terraform modules and Ansible roles that plug into the existing homelab provisioning pipeline. Same IaC principles already used for every other container, now applied to AI agent orchestration. New project = `terraform apply` + clone repos.

## Project Classification

- **Project Type:** Developer infrastructure (IaC + orchestration tooling)
- **Domain:** DevOps / AI-assisted development
- **Complexity:** Medium — no regulatory compliance, but significant integration complexity (5 independent upstream tools), upstream dependency risk, and architecturally novel compound learning system
- **Project Context:** Brownfield — extending existing 2-node Proxmox homelab (expanding to 3 nodes with N5 Pro as pve3; 4+ containers, 19 Docker stacks, 40+ services) with new AI development capabilities and local LLM inference

## Success Criteria

### User Success

- **Disconnect survival** — Close laptop mid-session, reconnect via SSH, and resume exactly where you left off. No context loss, no re-explanation. The "it just works" moment.
- **Memory recall** — Start a new Claude Code session and receive an automatic briefing with relevant context from previous sessions without prompting. "It remembers what I did yesterday."
- **Autonomous execution** — Issue a quick-dev task to the Director and walk away. Return to find the task completed, output committed, and a summary waiting. "It works while I'm away."
- **Zero setup tax** — Start a new consulting project by provisioning a container and cloning repos. All AI tooling is ready. No manual installation, no configuration, no troubleshooting. Under 15 minutes from `terraform apply` to first productive session.

### Business Success

- **Time to first productive session:** Current state: 2-4 hours of manual setup per engagement. Target: under 15 minutes.
- **Context re-establishment time:** Current state: 10-15 minutes re-explaining context at each session start. Target: under 1 minute (OMEGA auto-briefing).
- **No cost ceiling** — API costs ($50-150/mo estimated) are acceptable as long as the system delivers measurable productivity gains. Monitor but don't constrain.
- **6-month milestone:** 3 projects completed using the stack, OMEGA Memory contains 500+ entries, Director handles create-story tasks autonomously.
- **12-month milestone:** GEPA-optimized BMAD skills measurably outperform baseline, parallel workers run without daily intervention, template validated on 5+ fresh deployments.

### Knowledge Management Success (Phase 2b)

- **LLM Wiki adoption:** Wiki contains 50+ pages after 1 month of usage, with working cross-references and Obsidian graph view showing entity relationships.
- **MemPalace recall:** >90% recall on project-specific queries in raw mode.
- **Ticket triage latency:** Linear tickets triaged autonomously within 5 minutes of creation.
- **Meeting ingestion:** Granola meeting notes ingested into wiki within 30 minutes of meeting end.
- **Obsidian sync:** Wiki pages visible on laptop within 5 minutes of container change.
- **Query hierarchy:** Hermes consistently checks wiki before falling back to MemPalace, reducing token usage on repeat queries.

### Technical Success

- **Each service independently functional** — Every tool installs, configures, and passes its own acceptance tests before any integration work begins.
- **Idempotent provisioning** — Ansible roles can be re-run on the same container without side effects. Running the role twice produces the same result as running it once.
- **Integration smoke test passes** — Director triggers a task that reads from OMEGA Memory, confirming the services communicate correctly.
- **Reproducible on fresh container** — (Phase 2) Spin up a new LXC, run all Ansible roles, and pass all acceptance tests without manual intervention.

### Measurable Outcomes — Acceptance Tests

**AT-1: tmux + claude-tmux**

| Test | Procedure | Pass Criteria |
|------|-----------|---------------|
| AT-1.1: tmux session persistence | Start a Claude Code session in a named tmux session. Kill SSH connection. Reconnect via SSH. `tmux attach`. | Session is exactly as left. No output lost. Claude Code process still running. |
| AT-1.2: claude-tmux TUI | Launch claude-tmux TUI via keybinding (Ctrl-C in tmux). | TUI displays all active sessions with correct status indicators (Working/Idle/Waiting). |
| AT-1.3: Session switching | Create 3 named tmux sessions. Use claude-tmux to switch between them. | All sessions accessible via j/k navigation + Enter. Each session retains independent state. |
| AT-1.4: Laptop restart survival | Start a session, close laptop entirely, wait 5 minutes, reconnect. | tmux sessions still running. All processes intact. No zombie processes. |

**AT-2: OMEGA Memory**

| Test | Procedure | Pass Criteria |
|------|-----------|---------------|
| AT-2.1: Installation and health | Run `pip install omega-memory[server] && omega setup && omega doctor`. | Doctor reports all checks passing. MCP server starts. 90MB ONNX model downloaded. |
| AT-2.2: Claude Code hook integration | Verify hooks registered in Claude Code settings. Start a session. | SessionStart hook fires and delivers welcome briefing (or "no memories yet" for first run). |
| AT-2.3: Memory capture | Work on a task in Claude Code (e.g., edit a file, make a decision). End session. | SessionStop hook generates session summary. `omega search` returns the captured lesson/decision. |
| AT-2.4: Cross-session recall | Start a new Claude Code session in the same project. | SessionStart briefing includes relevant context from AT-2.3. No manual prompting required. |
| AT-2.5: Semantic search | Store 10+ memories across 3 sessions. Run `omega search --query "authentication patterns"`. | Returns semantically relevant results ranked by relevance. FTS5 + vector search both functional. |
| AT-2.6: Auto-deduplication | Store the same lesson twice with slightly different wording. | OMEGA detects semantic similarity (>0.85 threshold) and evolves the existing memory instead of creating a duplicate. |
| AT-2.7: TTL policy | Store a session summary. Wait >24 hours (or simulate). | Session summary expires per TTL policy. Lessons persist indefinitely. |
| AT-2.8: SQLite backup | Trigger the configured SQLite backup schedule. Verify backup file exists. | Backup file created at expected location. Restorable: copy backup over DB, restart, verify memories intact. |
| AT-2.9: Namespace isolation | Create memories in namespace "project-a" and "project-b". Search within "project-a". | Only project-a memories returned. No cross-namespace leakage. |

**AT-3: Hermes Agent**

| Test | Procedure | Pass Criteria |
|------|-----------|---------------|
| AT-3.1: Installation | Run Hermes installer. Run `hermes doctor`. | All checks pass. Python 3.11 + Node.js installed. Config at `~/.hermes/`. |
| AT-3.2: Configuration | Set terminal backend=local, cwd to project root, delegation model=claude-sonnet. Add ANTHROPIC_API_KEY to .env. | `hermes setup` completes. Config validated by doctor. |
| AT-3.3: MCP connection to OMEGA | Register OMEGA Memory as MCP server in Hermes config. | Hermes can query OMEGA via MCP tools. `hermes tools` shows OMEGA tools available. |
| AT-3.4: Basic conversation | Start a Hermes session. Ask it to describe the current project directory. | Hermes responds accurately using terminal backend to inspect the filesystem. |
| AT-3.5: Skill loading | Create a minimal test skill in `~/.hermes/skills/test-skill/SKILL.md`. Invoke it. | Skill loads and executes. Output matches expected behavior. |
| AT-3.6: Autonomous quick-dev task | Issue: "Write a short documentation page about Proxmox LXC container best practices." Do not intervene. | Hermes produces a markdown file, commits it, and reports completion. No human input after initial prompt. Output is coherent and accurate. |
| AT-3.7: tmux persistence | Start Hermes in a named tmux session. Disconnect SSH. Reconnect. | Hermes process still running. Session resumable. |
| AT-3.8: Subagent spawning | Ask Hermes to delegate a subtask to a subagent. | Subagent spawns, completes task, returns summary to parent. No context leakage between parent and subagent. |
| AT-3.9: Cron scheduling | Schedule a recurring task (e.g., "every hour, check git status"). Wait for one execution. | Cron fires on schedule. Output logged. Task completes without intervention. |
| AT-3.10: Anthropic Max Plan compatibility | Configure Hermes with Max Plan credentials. Execute a simple task. Spawn Claude Code worker via `claude -p`. | Hermes successfully calls Claude API. Claude Code worker completes task. No authentication errors. Rate limits (if any) documented. |

**AT-4: Integration Smoke Test**

| Test | Procedure | Pass Criteria |
|------|-----------|---------------|
| AT-4.1: Director uses OMEGA context | Store a memory in OMEGA ("This project uses Terraform for provisioning"). Ask Director to describe the project's provisioning approach. | Director's response incorporates the OMEGA memory, demonstrating MCP integration works end-to-end. |
| AT-4.2: Worker captures to OMEGA | Director spawns a Claude Code worker via `claude -p`. Worker completes a task. | OMEGA captures the worker's session output via hooks. New session shows the worker's learnings in briefing. |
| AT-4.3: Multi-session awareness | Run 2 tmux sessions simultaneously (Director + 1 worker). Worker stores a memory. | Director can query and retrieve the worker's memory via OMEGA MCP. No restart required. |

**AT-5: Ansible Roles**

| Test | Procedure | Pass Criteria |
|------|-----------|---------------|
| AT-5.1: Idempotency | Run the full Ansible playbook twice in sequence. | Second run reports 0 changed tasks (or only expected changed tasks like service restarts). No errors. |
| AT-5.2: Fresh install | Run Ansible roles on a clean container with only base packages. | All services install and pass AT-1 through AT-4 tests. No manual steps required. |
| AT-5.3: Service health after reboot | Reboot the container. Wait for all services to start. | tmux server starts automatically. OMEGA MCP server starts automatically. Hermes can be resumed from tmux. claude-tmux functional. |

**AT-6: BMAD Workflow Enhancements**

| Test | Procedure | Pass Criteria |
|------|-----------|---------------|
| AT-6.1: Doc update skill installation | Verify `bmad-update-project-docs` skill exists in `.claude/skills/` with SKILL.md, workflow.md, and supporting files. | Skill directory exists with all required files. `/update-project-docs` is invocable. |
| AT-6.2: Check mode | Run `/update-project-docs check` on a project with known recent changes. | Health report correctly identifies stale docs and lists the changed files that caused staleness. No files modified. |
| AT-6.3: Update mode | Make a known change (e.g., add an Ansible role), run `/update-project-docs`. | Skill detects the change, proposes updating the correct architecture doc, and after confirmation updates only the affected section. Unchanged sections are identical before/after. |
| AT-6.4: Full mode delegation | Run `/update-project-docs full`. | Skill delegates to `bmad-document-project` for full rescan. No errors. |
| AT-6.5: State tracking | Run update mode. Check `project-scan-report.json`. | State file contains `git_ref_at_last_update`, `last_incremental_update`, and `section_timestamps` fields with correct values. |
| AT-6.6: Eval assertions in story template | Create a story using `/bmad-create-story`. | Story output file contains an "Eval Assertions" section with binary test criteria derived from acceptance criteria. |
| AT-6.7: Autoresearch skill installed | Run `/autoresearch:fix --help` or equivalent. | Autoresearch skill responds. Available in Claude Code's skill list. |
| AT-6.8: BMAD update-safety | Verify that zero files in `.claude/skills/bmad-*/` have been modified by the workflow enhancements. | `git diff` on `.claude/skills/bmad-*/` shows no changes. All enhancements are in separate skill directories or user-controlled files. |

### Negative Tests — What the System Must NOT Do

**AT-N1: Data Isolation**

| Test | Procedure | Pass Criteria |
|------|-----------|---------------|
| AT-N1.1: Cross-namespace memory leakage | Store confidential memories in namespace "client-a". Search from namespace "client-b" with a query that would match. | Zero results returned from client-a. No cross-namespace leakage. |
| AT-N1.2: OMEGA global search exclusion | Store project-specific memories with namespaces. Run a global unscoped search. | Only returns memories from the current namespace or explicitly global memories. Never surfaces namespaced memories from other projects. |

**AT-N2: Resource Guardrails**

| Test | Procedure | Pass Criteria |
|------|-----------|---------------|
| AT-N2.1: Worker process limits | Attempt to spawn more workers than the configured maximum (e.g., 5). | System refuses to spawn beyond limit. Existing workers unaffected. Clear error message. |
| AT-N2.2: OMEGA RAM ceiling | Run OMEGA under load (100+ queries in rapid succession). Monitor RSS memory. | Memory stays within acceptable bounds (~337MB + buffer). No unbounded growth. No OOM kill. |
| AT-N2.3: Disk usage from OMEGA | Store 1000+ memories over multiple sessions. Check SQLite DB size. | DB size remains reasonable. TTL-expired entries are actually purged, not just marked. |
| AT-N2.4: Hermes turn limit behavior | Start a Hermes session. Push it past 90 turns (or close to the limit). | Hermes gracefully handles the limit — compresses or ends the session cleanly. Does NOT silently truncate context or produce degraded output without warning. |

**AT-N3: Git Safety**

| Test | Procedure | Pass Criteria |
|------|-----------|---------------|
| AT-N3.1: Concurrent worktree git operations | Create 2 worktrees. Run `git status` simultaneously in both. | No lock contention errors. No `.git/index.lock` conflicts. Both complete successfully. |
| AT-N3.2: Worktree cleanup on failure | Start a worker in a worktree. Kill the worker process mid-task. | Worktree is left in a recoverable state. Main branch is unaffected. No dangling locks. `git worktree prune` cleans up. |
| AT-N3.3: No force-push from workers | Worker completes a task and pushes. | Worker uses regular `git push`, never `--force`. If push is rejected, worker reports the conflict instead of overwriting. |

**AT-N4: Secret Safety**

| Test | Procedure | Pass Criteria |
|------|-----------|---------------|
| AT-N4.1: OMEGA does not store secrets | Work in a session where API keys or passwords are visible (e.g., in .env files). End session. Search OMEGA for the secret value. | OMEGA does NOT capture secrets in memory entries. Hooks should filter or the system should not ingest .env content. |
| AT-N4.2: Hermes .env not in git | Check that `~/.hermes/.env` (containing ANTHROPIC_API_KEY) is in `.gitignore` or equivalent. | .env file is never tracked by git. `git status` shows it as ignored. |
| AT-N4.3: Ansible vault for sensitive values | Inspect Ansible roles for any hardcoded credentials, API keys, or passwords. | All secrets referenced via Ansible vault variables or environment variables. Zero plaintext secrets in role files. |

**AT-N5: Autonomy Boundaries**

| Test | Procedure | Pass Criteria |
|------|-----------|---------------|
| AT-N5.1: Director does not merge without review | Director completes a story pipeline (Phase 2, but design for it now). | Director creates a PR or marks the worktree as "ready for review." Does NOT merge to main autonomously. |
| AT-N5.2: Director does not modify sprint-status without completing the story | Director encounters an error mid-story. | sprint-status.yaml is NOT updated to "done." Story status reflects the actual state (error/in-progress). |
| AT-N5.3: Hermes does not install packages without Ansible | Hermes decides it needs a missing tool during a task. | Hermes does NOT run `apt install` or `pip install` directly. It either uses what's available or reports the missing dependency. Package management stays in Ansible roles. |

## User Journeys

### Journey 1: Tom the Consultant — New Project Kickoff

**Opening Scene.** Tom lands a new consulting engagement on Monday morning. The client uses a FastAPI + PostgreSQL stack and needs three microservices built out. In the past, this meant: SSH to the homelab, create a container, install Python, Node, Claude Code, set up VS Code tunnel, configure BMAD skills, install memory tools — a half-day of yak-shaving before writing a single line of project code.

**Rising Action.** Tom runs `terraform apply -var="project=acme-api"` from his homelab-infra repo. A fresh LXC spins up on pve2 in 60 seconds. Ansible roles fire: tmux configured, OMEGA Memory installed with hooks, Hermes Agent set up with BMAD skills, claude-tmux ready. Tom clones the client's repos into the container. He opens VS Code Remote SSH, attaches to the tmux session, and runs `/bmad-product-brief`.

**Climax.** Within 15 minutes of `terraform apply`, Tom is in a productive BMAD session — not installing tools, not configuring hooks, not debugging setup issues. OMEGA's SessionStart hook fires and says: "No memories yet for this project. Ready to learn." The container is a blank slate with a full toolkit.

**Resolution.** The setup tax that used to consume half a day is now a 15-minute automation. Tom starts every engagement from the same solid foundation. The container remembers everything from this point forward — by week two, OMEGA is surfacing patterns like "the client's auth module uses a non-standard import path" across sessions automatically.

### Journey 2: Tom the Night Shift — Works While You Sleep

**Opening Scene.** It's Thursday evening. Tom has completed the analysis and planning phases for the Acme project. The sprint plan has 3 epics with 8 stories. Epics 1 and 2 are independent — their stories can run in parallel. Tom is tired and wants to review results fresh in the morning.

**Rising Action.** Tom opens the Director's tmux session and tells Hermes: "Run stories 1.1 and 2.1 in parallel." The Director reads the sprint-status.yaml, validates the dependency graph, creates two git worktrees (`feat/1-1` and `feat/2-1`), and spawns Claude Code workers in each. Tom checks claude-tmux — two sessions show "Working" status. He closes his laptop and goes to bed.

**Climax.** At 2 AM, the Director completes story 1.1. It runs the code review automatically (3 parallel review agents). Two minor findings are auto-patched. The story is marked "done" in the story file. The Director moves to story 1.2, creates a new worktree, and starts the next pipeline. Story 2.1 finishes at 3 AM — one finding needs human input (confidence below 70%). The Director logs the question and moves to the next available story.

**Resolution.** Tom opens his laptop Friday morning. claude-tmux shows: 3 stories done, 1 waiting for input. He reviews the PRs, answers the escalated question, and the Director resumes. A full day's worth of implementation happened overnight. OMEGA captured every decision, every lesson, every pattern — the afternoon stories benefit from the morning's context.

### Journey 3: Tom the Operator — Keeping the Lights On

**Opening Scene.** Tom notices his Claude API bill is higher than expected this month. He also realizes OMEGA Memory hasn't been backed up in a while, and he's not sure if the Hermes cron jobs are actually firing.

**Rising Action.** Tom SSHs into the container and runs a health check. He checks:
- `omega doctor` — OMEGA reports healthy, 847 memories, 142MB SQLite DB, last backup 3 days ago (should be daily — he spots the broken cron).
- `hermes doctor` — All checks pass, 4 skills loaded, 12 cron jobs scheduled.
- claude-tmux — Shows 1 idle session, no orphaned workers.
- Container resources — 2.1GB RAM used (OMEGA 337MB + Hermes 100MB + system), well within 8GB allocation.

**Climax.** Tom fixes the backup cron, verifies it fires, and checks the backup file is restorable. He reviews the API usage via Anthropic's dashboard — the spike was from a GEPA optimization run he forgot he'd scheduled. He adjusts the GEPA cron to run weekly instead of daily.

**Resolution.** The system is healthy. Tom updates the Ansible role to include the backup cron fix so future containers get it right from the start. He adds a mental note that he'll want a unified health-check script in Phase 2 — right now, checking each tool individually works but doesn't scale. OMEGA captures the lesson: "GEPA optimization runs consume significant tokens — schedule weekly, not daily."

### Journey 4: Tom the Debugger — Something Went Wrong

**Opening Scene.** Tom starts a new Claude Code session Monday morning. The OMEGA SessionStart hook fires but the briefing is empty — "No relevant memories found." He worked all last week on this project. Something is wrong.

**Rising Action.** Tom investigates:
1. `omega search --query "anything"` — returns results. The database isn't empty.
2. `omega search --namespace acme-project` — empty. Wrong namespace?
3. He checks the Claude Code hook config — the namespace is set to `acme-api`, but he'd been working in sessions configured as `acme-project`. Namespace mismatch.

**Climax.** Tom finds the root cause: when he set up the project, he used one namespace name in the OMEGA config and a different one in the Claude Code hooks. All memories were stored under `acme-api` but sessions were querying `acme-project`. No data lost — just misrouted.

**Resolution.** Tom fixes the namespace in the hook config to match. The next SessionStart briefing delivers a full week of accumulated context. He updates the Ansible role to derive the namespace from a single variable (the project name) so this mismatch can't happen again. OMEGA captures the debugging pattern for future reference.

### Journey Requirements Summary

| Journey | Capabilities Revealed |
|---------|----------------------|
| **New Project Kickoff** | Terraform module for LXC provisioning, Ansible roles for all 4 services, idempotent setup, zero manual configuration steps, OMEGA namespace auto-configuration per project |
| **Works While You Sleep** | Director story pipeline orchestration, git worktree management, parallel worker spawning, confidence-based escalation, sprint-status management, claude-tmux status monitoring |
| **Keeping the Lights On** | Per-service health checks (`omega doctor`, `hermes doctor`), SQLite backup cron, resource monitoring, API cost visibility, GEPA scheduling controls |
| **Something Went Wrong** | Namespace debugging tools, OMEGA search/query CLI, hook configuration inspection, clear error messages for misconfigurations, single-source-of-truth for project naming |

## Innovation & Novel Patterns

### Detected Innovation Areas

**1. Agent Lifecycle as the Core Problem.** The AI dev tooling industry has focused on compute location — cloud containers, local runtimes, IDE plugins. AI Dev Container reframes the problem entirely: the bottleneck isn't where agents run, it's that they don't persist, don't remember, don't coordinate, and don't learn. This is a paradigm shift from "better tools" to "better agent infrastructure."

**2. Two-Layer Compound Learning.** Per-project OMEGA Memory captures project-specific context, decisions, and patterns within each container — improving that project's workflow over sessions. A separate cross-project OMEGA instance (Phase 2+) distills generalizable patterns across engagements — feeding into GEPA skill optimization and methodology improvement. This two-layer design solves data isolation naturally: client data stays in its container, only anonymized methodology insights flow to the cross-project layer. The system compounds at both levels: each project gets smarter over its sessions, and the overall methodology gets smarter across projects.

**3. The "Jarvis" Pattern — Always-On Autonomous AI Assistant.** Distinct from "invoke a tool and wait for output," this is a persistent presence that maintains project momentum 24/7. The Director works while you sleep, escalates intelligently based on confidence, and captures every decision for future sessions. This is a new interaction model for developer tooling — not a CLI, not an IDE plugin, but an always-on project partner.

### Market Context & Competitive Landscape

Web research confirmed no existing product combines all four pillars (persistence, memory, orchestration, container templating). The competitive landscape is fragmented:
- **Persistence tools** (tmux-agents, cmux) lack memory and orchestration
- **Memory tools** (memctl, OneContext, UnifiedMemory.ai) are cloud SaaS with no orchestration
- **Orchestration tools** (Conductor, Composio) are desktop-only with no persistence or memory
- **Container tools** (DevContainer.ai) don't bundle agent infrastructure

The "Proxmox + AI dev environment as LXC template" intersection is essentially unoccupied.

**4. Autoresearch-Driven Workflow Improvement.** Adopting Karpathy's autoresearch pattern (March 2026, 21K+ GitHub stars) for BMAD skill quality. Eval assertions in story templates turn acceptance criteria into binary tests. The `/autoresearch:fix` loop iterates on code review findings automatically. The incremental documentation skill's `workflow.md` serves as the autoresearch `program.md` equivalent — editable instructions refined through measured iteration. This is the autoresearch pattern applied to development methodology, not just ML training.

### Validation Approach

- **Phase 1 (MVP):** Each component works standalone. Integration smoke test confirms they communicate. This validates the technical foundation.
- **Phase 2:** Full compound learning loop — Director orchestrates stories, per-project OMEGA captures learnings, GEPA optimizes skills. Cross-project OMEGA instance established for methodology-level insights.
- **6-month milestone:** 3 projects completed. Measurable comparison: does project 3 go faster than project 1? Does OMEGA recall reduce context re-establishment time? This validates compound learning.
- **Community signal:** If open-sourced Ansible roles attract adoption, the "Terraform for AI agents" framing resonates beyond the solo consultant use case.

### Risk Mitigation

- **If compound learning doesn't materialize:** The system still delivers immediate value via session persistence and zero setup tax. GEPA optimization is additive, not load-bearing.
- **If Hermes Agent is abandoned upstream:** The Director pattern can be reimplemented with Claude Code's native agent teams (experimental but evolving rapidly) or any MCP-compatible orchestrator. The architecture is designed for component swappability.
- **If the "Jarvis" autonomy isn't trustworthy:** Confidence-based escalation ensures the human stays in the loop. The threshold can be raised (e.g., escalate at 95% instead of 90%) until trust is established. Autonomy is a dial, not a switch.

## Developer Infrastructure Requirements

### Project-Type Overview

AI Dev Container is developer infrastructure delivered as IaC artifacts (Terraform module + Ansible roles). It is not a library, package, or application — it's a provisioning and configuration layer that installs, configures, and wires together five open-source tools into a functional AI development environment on a Proxmox LXC container.

### Technical Architecture Considerations

**Runtime Requirements:**

| Component | Python | Node.js | Rust/Cargo | Other |
|-----------|--------|---------|------------|-------|
| OMEGA Memory | 3.9+ | — | — | 90MB ONNX model, ~337MB RAM |
| Hermes Agent | 3.11+ | Yes (auto-installed) | — | git |
| claude-tmux | — | — | Yes (build from source) | tmux |
| DBOS (Phase 2) | 3.9+ | — | — | PostgreSQL |
| GEPA (Phase 2) | 3.9+ | — | — | LLM API access |

**Critical dependency:** Hermes Agent requires Python 3.11+. If the container base image ships Python 3.9 or 3.10, the `ai-dev-hermes` role must install Python 3.11 alongside the system Python (e.g., via deadsnakes PPA or pyenv). The `ai-dev-common` role should ensure Python 3.11+ is the default before other roles run.

**Anthropic subscription compatibility:** User has an Anthropic Max Plan subscription. Must verify:
- Whether Hermes Agent can authenticate via Max Plan credentials or requires a separate API console key
- Whether Claude Code CLI spawned programmatically by the Director (`claude -p`) works under Max Plan
- Whether OMEGA Memory features requiring LLM access (if any) are compatible
- Rate limits or usage caps that apply under Max Plan for programmatic/automated usage
- This is a blocking validation — if a separate API subscription is required, the cost model changes

### Installation Architecture

Follows the existing homelab-infra pattern: role-based Ansible with module-based Terraform.

**Terraform (MVP):** Uses existing `ct-debian` module to provision the target container (ct-dev-homelab, VMID 150, pve2, 2C/8GB). No new Terraform module needed for Phase 1. A dedicated `ct-ai-dev` module is Phase 2 scope for fresh project container provisioning.

**Baseline: existing `dev-host` role** (`ansible/roles/dev-host/`):
The existing dev-host role already provides: apt packages (git, tmux, build-essential, python3, pip, venv, SQLite/SSL dev libs), Node.js 20 LTS, Claude Code CLI (with auto-skip-permissions wrapper), ruflo CLI + MCP registration, pyenv (Python version management), Docker CE, VS Code tunnel service, Git config, SSH keys, BMAD Method installation, and project workspace structure. **No `ai-dev-common` role is needed — dev-host is the baseline.**

**New Ansible roles** (`ansible/roles/`), layered on top of `dev-host`:
- `ai-dev-tmux` — claude-tmux Rust build and install (using build-essential from dev-host), tmux keybindings for claude-tmux TUI, auto-start configuration on boot
- `ai-dev-omega-memory` — OMEGA Memory pip install (using pyenv Python 3.11+ from dev-host), ONNX model download, MCP server config, Claude Code hook registration, SQLite backup cron, namespace configuration per project
- `ai-dev-hermes` — Hermes Agent install (uses pyenv Python 3.11), config.yaml, SOUL.md, .env (vault-encrypted), MCP connection to OMEGA, BMAD skill stubs, cron jobs
- Each role is independently testable and idempotent
- Each role assumes `dev-host` has already run (declares dependency in role metadata)

**Playbook** (`ansible/playbooks/deploy-ai-dev-container.yml`):
- Composes: dev-host (baseline) -> ai-dev-tmux -> ai-dev-omega-memory -> ai-dev-hermes
- Parameterized: project name (drives OMEGA namespace, container hostname), API keys (vault), resource allocation
- Can be run standalone (all roles) or incrementally (only new ai-dev-* roles on existing dev container)

**BMAD Workflow Enhancements** (standalone Claude Code skills, not Ansible roles):
- `bmad-update-project-docs` skill — New Claude Code skill in `.claude/skills/bmad-update-project-docs/` with SKILL.md, workflow.md, templates, and references. Git-diff-aware incremental documentation updates with check/update/full modes.
- Story template modification — "Eval Assertions" section added to user-controlled story template in `_bmad-output/`. Binary test criteria derived from acceptance criteria.
- Autoresearch skill — Separately installed Claude Code skill (`/autoresearch:fix`). Post-code-review iteration loop for automated fix cycles.
- **Critical constraint:** Zero modifications to BMAD built-in skills in `.claude/skills/bmad-*/`. All enhancements are standalone or user-controlled.

### IDE Integration

- **VS Code Remote SSH** — Purely server-side. No VS Code extensions or settings required in the Ansible roles. User connects via SSH as with any other container.
- **Claude Code** — Installed as part of the base developer tooling. OMEGA hooks registered in Claude Code settings by the `ai-dev-omega-memory` role.

### Implementation Considerations

- All roles must be idempotent — rerunning produces the same result
- Secrets (ANTHROPIC_API_KEY, OMEGA config) managed via Ansible vault, never plaintext in roles
- Each role includes a `verify.yml` task file that runs the relevant acceptance tests (AT-1 through AT-5)
- The `ai-dev-common` role runs first and handles version conflicts (Python 3.11 alongside system Python if needed)
- claude-tmux requires a Rust compilation step (~2-5 min on first install); the role should cache the binary

## Project Scoping & Phased Development

### MVP Strategy & Philosophy

**MVP Approach:** Problem-solving MVP — prove each component installs, configures, and works on the existing `ct-dev-homelab` container (VMID 150, pve2). The minimum useful outcome: "I have tmux persistence, OMEGA memory across sessions, and Hermes can run a task autonomously — all provisioned by rerunnable Ansible roles."

**Resource Requirements:** Solo developer (Tom), existing homelab hardware, Anthropic Max Plan subscription. No additional infrastructure or team needed.

### MVP Feature Set (Phase 1)

**Core User Journeys Supported:**
- Journey 1 (New Project Kickoff) — partially: Ansible roles install the stack, but on the existing container, not a fresh one
- Journey 3 (Keeping the Lights On) — fully: per-service health checks, backup cron, resource monitoring

**Must-Have Capabilities:**

*Prerequisite — BMAD Workflow Enhancements (before infrastructure roles):*
- BMAD skill `bmad-update-project-docs`: incremental doc update with check/update/full modes
- Story template updated with "Eval Assertions" section for binary test criteria
- Autoresearch skill installed (`/autoresearch:fix`) for post-code-review iteration loops
- All enhancements BMAD-update-safe (standalone skills, no BMAD modifications)

*Infrastructure — AI Dev Stack:*
- Existing `dev-host` role as baseline (already provides Python, Node.js, pyenv, tmux, git, Claude Code, ruflo, BMAD)
- Ansible role `ai-dev-tmux`: claude-tmux build/install, keybindings, auto-start
- Ansible role `ai-dev-omega-memory`: OMEGA install, hooks, MCP server, backup cron, namespace config
- Ansible role `ai-dev-hermes`: Hermes install, config, OMEGA MCP connection, one test skill
- Playbook `deploy-ai-dev-container.yml` composing dev-host + ai-dev-* roles
- Acceptance tests AT-1 through AT-6 passing (29 + workflow enhancement tests)
- Negative tests AT-N1 through AT-N5 passing (14 negative tests)
- Anthropic Max Plan compatibility verified (AT-3.10)
- All roles idempotent and independently testable

**Explicitly NOT in MVP:**
- No new Terraform module — use existing `ct-dev-homelab` via `ct-debian` module
- No Director story pipeline orchestration
- No parallel workers
- No DBOS, GEPA, or information source integrations
- No fresh container provisioning
- No LLM Wiki, MemPalace, Obsidian, or knowledge ingestion pipelines (Phase 2b)

### Post-MVP Features

**Phase 2a (Growth) — "They work together":**
- Director orchestrates full BMAD story pipeline (create-story -> dev-story -> code-review)
- Parallel workers via git worktrees with OMEGA coordination
- DBOS crash recovery wrapping Director workflows
- GEPA scheduled optimization of BMAD skills
- Dedicated `ct-ai-dev` Terraform module for fresh project containers
- Fresh container validation: provision new LXC, run roles, pass all tests
- Supports Journey 2 (Night Shift) and Journey 4 (Debugger) fully

**Phase 2b (Knowledge Management) — "It knows and learns":**
- LLM Wiki: per-project structured markdown wiki maintained by Hermes, browsable via Obsidian (FR53-FR56)
- Obsidian integration: per-container vault with git sync to laptop, meta-vault for cross-project navigation (FR54)
- MemPalace: deep verbatim memory with 96.6% recall, 19 MCP tools, temporal knowledge graph per project (FR57-FR58)
- Query hierarchy: LLM Wiki (fast, pre-synthesized) → MemPalace (deep, raw) → OMEGA (cross-project) (FR59)
- Knowledge ingestion pipelines: Linear MCP for ticket triage, Granola MCP for meeting notes, Azure DevOps MCP for work items (FR60-FR62)
- Cross-project OMEGA instance for methodology-level insights
- Memory curation strategy: wiki as refined truth, MemPalace as raw memory, OMEGA as cross-project spine
- Shared user model across containers via Honcho memory provider or OMEGA profile

**Phase 3 (Vision) — "It's repeatable and improving":**
- Automated new-project workflow validated end-to-end: Terraform provisions LXC, Ansible configures stack, acceptance tests pass, ready for development — fully hands-off
- Cross-project knowledge graph as queryable strategic asset
- BMAD skills library optimized across dozens of engagements
- Open-source Ansible roles for community adoption

### Risk Mitigation Strategy

**Technical Risks:**
- *Most technically challenging:* Getting Hermes Agent to communicate with OMEGA via MCP reliably. Mitigated by: testing this connection as the first integration point (AT-4.1).
- *Riskiest assumption:* Anthropic Max Plan supports programmatic usage by Hermes and spawned Claude Code workers. Mitigated by: validating this in the first week of MVP (AT-3.10).
- *Python version conflict:* Hermes needs 3.11+, others need 3.9+. Mitigated by: `ai-dev-common` role ensures 3.11+ is installed first.

**Market Risks:**
- *Upstream tool abandonment:* Hermes, OMEGA, claude-tmux are community projects. Mitigated by: version pinning, component swappability design, and the Director pattern being reimplementable on other orchestrators.
- *Claude Code native features catching up:* Anthropic may add persistence and memory natively. Mitigated by: MVP delivers value immediately regardless; native features would complement, not replace, the container template approach.

**Resource Risks:**
- *Solo developer constraint:* Tom is the only user and developer. Mitigated by: tight MVP scope (4 Ansible roles), no Terraform work in Phase 1, and leveraging existing homelab patterns.
- *Absolute minimum:* If time is severely constrained, the minimum viable slice is `ai-dev-tmux` + `ai-dev-omega-memory` (session persistence + memory). Hermes can be added later.

## Functional Requirements

### Session Persistence

- **FR1:** User can run Claude Code sessions inside named tmux sessions on the server
- **FR2:** User can disconnect from SSH and reconnect to find all tmux sessions intact with no context loss
- **FR3:** User can view all active sessions and their status (Working/Idle/Waiting) via a TUI dashboard
- **FR4:** User can switch between active sessions from the TUI dashboard
- **FR5:** tmux server and key sessions can auto-start on container boot

### Persistent Memory

- **FR6:** Claude Code sessions can automatically capture lessons, decisions, and context to persistent storage via lifecycle hooks
- **FR7:** Claude Code sessions can receive an automatic briefing of relevant prior context at session start
- **FR8:** User can search stored memories using natural language queries with semantic relevance ranking
- **FR9:** System can detect and deduplicate semantically similar memories automatically
- **FR10:** System can evolve existing memories when related content is captured (append, not duplicate)
- **FR11:** System can expire transient memories (session summaries) via TTL while preserving persistent memories (lessons) indefinitely
- **FR12:** User can organize memories into project-scoped namespaces
- **FR13:** System can enforce namespace isolation — queries in one namespace never return results from another
- **FR14:** System can back up the memory database on a configurable schedule
- **FR15:** User can restore the memory database from a backup

### Agent Orchestration

- **FR16:** User can install and configure an always-on Director agent that runs in a tmux session
- **FR17:** Director can connect to the persistent memory system via MCP to query and store context
- **FR18:** Director can execute a quick-dev task end-to-end without human intervention after initial command
- **FR19:** Director can load and execute BMAD methodology skills
- **FR20:** Director can spawn subagents to delegate subtasks
- **FR21:** Director can schedule recurring tasks via cron
- **FR22:** User can verify Director health and configuration via a built-in diagnostic command

### Integration

- **FR23:** Director can query persistent memory and incorporate retrieved context into task execution
- **FR24:** Claude Code worker sessions can capture outputs to persistent memory via hooks, making them available to other sessions
- **FR25:** Multiple simultaneous tmux sessions can share memory — what one session stores, another can retrieve without restart
- **FR26:** User can verify end-to-end integration: Director triggers a task that uses memory context and produces a verifiable output

### Provisioning & Reproducibility

- **FR27:** User can provision the complete AI dev stack on a container by running a single Ansible playbook
- **FR28:** Ansible playbook can be re-run on the same container without side effects (idempotent)
- **FR29:** Each tool's Ansible role can be run and tested independently
- **FR30:** Ansible AI dev roles can leverage the existing `dev-host` role's runtime dependencies (Python via pyenv, Node.js, build-essential) without duplicating or conflicting with the baseline
- **FR31:** Ansible playbook can be parameterized per project (project name, OMEGA namespace, API keys via vault)
- **FR32:** Each Ansible role can run verification tasks that confirm the installed service is functional

### Operational Guardrails

- **FR33:** System can limit the maximum number of concurrent worker processes
- **FR34:** System can prevent memory queries from returning results across namespace boundaries
- **FR35:** System can prevent secrets (API keys, passwords) from being captured into persistent memory
- **FR36:** Workers can only use regular git push, never force-push
- **FR37:** All secrets are managed via Ansible vault — no plaintext credentials in roles or configuration files. Vault-managed secrets include: OpenRouter API key, Slack bot/app tokens, Home Assistant token, and optional provider keys (Google, FAL, Tinker, WandB). Anthropic API key is not vault-managed — Claude Code workers use Max Plan credential auto-discovery.
- **FR38:** Director does not merge code to main branches without human review
- **FR39:** Director does not install system packages directly — package management stays in Ansible roles

### LLM Provider & Subscription Compatibility

- **FR40:** Director authenticates to its configured LLM provider (OpenRouter by default) for coordination tasks, and spawns Claude Code workers that use Anthropic Max Plan credentials for implementation work
- **FR41:** Claude Code CLI can be spawned programmatically by the Director under the Max Plan subscription
- **FR42:** System can document any rate limits or usage constraints that apply under Max Plan for automated usage

### BMAD Workflow Enhancements

- **FR43:** User can run an incremental documentation update skill (`/update-project-docs`) that detects changed files since last doc update and updates only affected documentation sections
- **FR44:** The doc update skill can detect which files changed using git history (`git log --since`) and classify changes by impact to specific documentation files
- **FR45:** The doc update skill can present a change plan to the user showing which docs will be updated and why, requiring user confirmation before writing
- **FR46:** The doc update skill can update individual sections within a documentation file while preserving all unchanged sections exactly as-is
- **FR47:** The doc update skill can run in read-only check mode, producing a health report showing which docs are stale and what changed, without modifying any files
- **FR48:** The doc update skill can delegate to the existing `bmad-document-project` skill for full regeneration when requested
- **FR49:** The doc update skill can maintain a configurable file-to-doc mapping that maps source file patterns to specific documentation files and sections
- **FR50:** The doc update skill can track state (last update git ref, per-section timestamps) in the existing `project-scan-report.json` state file
- **FR51:** User can add an "Eval Assertions" section to story templates that defines binary test criteria derived from acceptance criteria, without modifying any BMAD built-in skill files
- **FR52:** User can install and use an autoresearch skill (`/autoresearch:fix`) separately from BMAD to run post-code-review iteration loops that automatically fix findings until all eval assertions pass

### Knowledge Management (Phase 2b)

- **FR53:** Hermes can maintain a structured LLM Wiki per project — markdown pages with entities, concepts, decisions, cross-references, index, and operation log — following the Karpathy LLM Wiki pattern
- **FR54:** User can browse project knowledge via an Obsidian vault per container, synced to a laptop meta-vault via git with auto-pull
- **FR55:** Hermes can ingest web articles into LLM Wiki via BMAD technical-research skill, triggered by user sending a URL via Slack or CLI
- **FR56:** Hermes can perform periodic wiki lint — detecting contradictions, orphaned pages, stale claims, and missing cross-references
- **FR57:** MemPalace is installed with its MCP server providing verbatim conversation storage and semantic search (96.6% recall, 19 MCP tools)
- **FR58:** MemPalace knowledge graph stores temporal entity-relationship facts per project with validity windows
- **FR59:** Hermes implements a query hierarchy: check LLM Wiki first (fast, pre-synthesized), fall back to MemPalace (deep, raw), then OMEGA (cross-project)
- **FR60:** Hermes polls Linear MCP for new tickets, classifies type (bug/feature/idea/suggestion), and routes to appropriate BMAD skill via Claude Code
- **FR61:** Hermes polls Granola MCP for new meetings and ingests transcripts/notes into LLM Wiki with entity extraction and action item tracking
- **FR62:** Hermes connects to Azure DevOps MCP for work item and PR context, conditional per project

## Non-Functional Requirements

### Reliability

- **NFR-REL-1:** tmux sessions must survive container reboots — tmux server auto-starts and named sessions are recoverable within 60 seconds of boot.
- **NFR-REL-2:** OMEGA Memory database must survive unexpected process termination without data corruption (SQLite WAL mode or equivalent).
- **NFR-REL-3:** Ansible roles must be rerunnable after partial failure — if a role fails mid-execution, rerunning it must recover to a correct state without manual cleanup.
- **NFR-REL-4:** OMEGA SQLite backups must run on schedule with no more than 24 hours of data loss in a worst-case failure scenario.
- **NFR-REL-5:** No single tool failure should render the entire stack unusable — tmux works without OMEGA, OMEGA works without Hermes, each tool degrades independently.

### Security

- **NFR-SEC-1:** All credentials (API keys, vault passwords) must be encrypted at rest via Ansible vault. Zero plaintext secrets in any repository file.
- **NFR-SEC-2:** OMEGA Memory must not capture or store content from files matching sensitive patterns (`.env`, `credentials.*`, `*secret*`, `*token*`).
- **NFR-SEC-3:** Namespace isolation must be enforced at the query layer — no configuration option or query parameter can bypass namespace boundaries.
- **NFR-SEC-4:** Hermes Agent `.env` and OMEGA database files must be excluded from git tracking via `.gitignore`.
- **NFR-SEC-5:** Workers must not have write access to the main/master branch — all work happens in feature branches or worktrees.

### Performance

- **NFR-PERF-1:** OMEGA semantic search must return results within 2 seconds for databases up to 5,000 memories.
- **NFR-PERF-2:** OMEGA SessionStart hook (welcome briefing) must complete within 5 seconds to avoid blocking the user's session start.
- **NFR-PERF-3:** Total RAM consumption of the AI dev stack (OMEGA + Hermes + tmux + claude-tmux) must stay under 2GB to leave headroom on an 8GB container.
- **NFR-PERF-4:** Ansible full playbook execution (all roles) must complete within 15 minutes on a fresh container.

### Integration

- **NFR-INT-1:** OMEGA Memory must expose a stable MCP interface that Hermes Agent can consume without version-specific coupling.
- **NFR-INT-2:** Claude Code hooks must be registered in the standard Claude Code settings location — no custom hook loaders or patches.
- **NFR-INT-3:** All tool versions must be pinned in Ansible roles with a documented compatibility matrix. Upgrades require explicit testing.
- **NFR-INT-4:** The system must function with Anthropic Max Plan subscription — no dependency on separate API console accounts or enterprise agreements.
- **NFR-INT-5:** All BMAD workflow enhancements (doc update skill, eval assertions, autoresearch) must be BMAD-update-safe — no modifications to BMAD built-in skill files in `.claude/skills/bmad-*/`. Enhancements use standalone skills, user-controlled templates, and separately-installed tools only.
- **NFR-INT-6:** The incremental doc update skill must be independent of the AI Dev Container infrastructure roles — it works on any BMAD project with a `docs/` folder, not just this one.
