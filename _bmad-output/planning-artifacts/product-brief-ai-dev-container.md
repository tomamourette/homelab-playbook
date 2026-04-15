---
title: "Product Brief: AI Dev Container"
status: "complete"
created: "2026-04-02"
updated: "2026-04-02"
inputs:
  - homelab-playbook/_bmad-output/planning-artifacts/research/technical-ephemeral-cloud-containers-research-2026-03-31.md
  - docs/project-overview.md
  - docs/architecture-homelab-playbook.md
  - docs/integration-architecture.md
---

# Product Brief: AI Dev Container

## Executive Summary

AI coding agents are powerful but stateless. Every session starts cold. Every disconnect kills context. Every new project means rebuilding the same infrastructure from scratch. The human becomes the bottleneck — manually orchestrating agents, re-explaining context, losing lessons between sessions.

AI Dev Container is infrastructure-as-code for the AI agent layer: a reusable Proxmox LXC template that comes pre-loaded with an always-on AI development stack. Hermes Agent runs as a persistent Director in tmux — it keeps working while you sleep, queuing results for your morning review. OMEGA Memory provides a shared brain across all sessions and projects. Claude Code workers execute in isolated git worktrees. claude-tmux gives you a dashboard. Spin up a container, clone your repos, and the full AI dev stack is ready. No setup tax.

Built for a solo consultant running multiple client projects on a Proxmox homelab. The immediate goal: eliminate the manual orchestration overhead of AI-assisted development. The long-term vision: a compound learning system where each project makes the next one faster — shared memory grows, skills optimize themselves, and the AI Director autonomously drives sprint implementation overnight while you focus on the analysis and planning that requires human judgment.

## The Problem

AI-assisted development with agents like Claude Code is powerful but fragile:

- **Session fragility.** VS Code tunnel + Claude Code terminals break on laptop restart. Hours of agent context vanish. You reconnect, re-explain, re-orient. Every disconnect is a cold start.
- **Manual orchestration.** Running parallel BMAD stories means manually managing terminals, worktrees, branches, and story order. The human becomes the bottleneck in a process designed to free them.
- **Stateless agents.** Each session starts blank. The agent that spent 30 minutes learning your auth module's import patterns forgets everything when the session ends. The next agent hits the same problems, wastes the same tokens, makes the same mistakes.
- **No coordination.** Two agents editing the same file. No shared awareness of what's been tried, what's been learned, what's been decided. Parallel work creates parallel confusion.
- **Setup tax per project.** Every new consulting engagement means re-installing tools, re-configuring agents, re-building the development environment from scratch.

Today, the alternatives are fragmented: Conductor (Mac-only, no persistence), cmux (Mac-only, no memory), memctl/OneContext (cloud SaaS, no orchestration), tmux-agents (glue scripts, no coordination). Each solves one piece. None stitch it together.

## The Solution

A Proxmox LXC container template that provides a complete, always-on AI development environment:

**Always-on sessions.** Everything runs in tmux on the server. Laptop dies, SSH drops, browser closes — the Director and all workers keep running. Reconnect from anywhere, anytime.

**Persistent shared memory.** OMEGA Memory runs as a local MCP server with SQLite storage. Every session automatically captures lessons, decisions, and context. Every new session receives relevant briefings from past work. Workers share one memory pool — what one learns, all benefit from.

**Intelligent Director that works while you sleep.** Hermes Agent runs as an always-on orchestrator that knows the BMAD methodology. It reads the sprint status, identifies parallelizable stories, spawns Claude Code workers in isolated git worktrees, and only escalates to the human when confidence drops below threshold. Queue up a sprint before bed — review the PRs over coffee. The Director maintains project momentum across disconnects, time zones, and overnight runs.

**Container-as-template.** Codified as a Terraform module + Ansible role in the existing homelab infrastructure. New project? `terraform apply` a fresh container, clone your repos, and the full AI dev stack is ready. No setup tax. Think of it as Terraform for AI agents — the same IaC principles you already use for infrastructure, applied to the agent orchestration layer.

## What Makes This Different

**Self-hosted and private.** All memory, all context, all agent coordination runs locally on your hardware. No client code or project data leaves your infrastructure — critical for consulting work.

**Compound learning across projects.** Unlike stateless tools that reset per session, OMEGA Memory persists across projects. Patterns learned on Project A inform Project B. Skills are optimized by GEPA (an evolutionary prompt optimization framework that analyzes execution traces to automatically refine BMAD skill prompts, improving success rates over time). The system gets better the more you use it.

**Integrated, not assembled.** Competitors solve individual pieces (tmux OR memory OR orchestration). This bundles all four pillars — persistence, memory, orchestration, and monitoring — into a single deployable unit, pre-wired and tested.

**Built on your existing pipeline.** Not a separate platform to maintain. It's a Terraform module and Ansible role that plugs into the same provisioning pipeline you already use for every other container in your homelab.

## Who This Serves

**Primary user:** Solo consultant / homelab operator who uses AI coding agents across multiple client projects and wants persistent, coordinated, always-on AI development infrastructure on their own hardware.

This person already runs Proxmox, already uses Terraform and Ansible for provisioning, and already works with Claude Code and BMAD or similar agent-driven methodologies. They're frustrated by the overhead of re-setting up agent infrastructure per project and losing context between sessions.

**Typical usage:** 2 active client projects, 3-5 BMAD stories per sprint per project, 4-6 hours of active development per day, 1-2 parallel workers. Container runs on a Proxmox LXC (2-4 vCPU, 8GB RAM) alongside existing homelab services.

## Success Criteria

**MVP (Phase 1) — "Each service works standalone":**
- tmux + claude-tmux installed and running; sessions survive laptop disconnect
- OMEGA Memory installed; context persists across Claude Code sessions (verify: start session, work, end, start new session, confirm prior context surfaces)
- Hermes Agent installed; can execute a simple quick-dev task (e.g., write Proxmox documentation) end-to-end without human intervention after initial command
- Each service independently functional on the homelab project container
- Setup codified as Ansible role(s) in homelab-infra/homelab-playbook
- Basic operational guardrails: SQLite backup schedule for OMEGA, process limits for workers

**Phase 2 — "They work together":**
- Director orchestrates a full BMAD story pipeline (create-story -> dev-story -> code-review)
- Parallel workers coordinate via OMEGA Memory + git worktrees
- DBOS crash recovery wraps the Director workflow
- GEPA scheduled optimization improves BMAD skills overnight
- Information source integration: Slack, email, MCPs (e.g., Granola for meeting transcripts) connected as context inputs
- Memory curation strategy across all tools (beyond OMEGA's built-in dedup/TTL)
- Fresh container validation: spin up a new LXC, run the Ansible roles, confirm the full stack works from scratch

## Scope

**In scope (MVP):**
- tmux + claude-tmux setup and configuration
- OMEGA Memory installation and Claude Code hook integration
- Hermes Agent installation and basic BMAD skill creation
- Ansible role(s) for reproducible setup
- Validation on the existing homelab project container
- Simple end-to-end test (quick-dev task, not full story pipeline)
- Lightweight integration smoke test: Director triggers a task that uses OMEGA Memory context, confirming the services can talk to each other

**Out of scope (MVP):**
- Full BMAD workflow integration (Director running story pipelines)
- Parallel worker orchestration
- GEPA self-learning optimization
- DBOS crash recovery
- Fresh container provisioning and validation
- Cloud scale-out (DevPod, Azure, Codespaces)

**Planned for Phase 2b (Knowledge Management):**
- LLM Wiki: per-project structured markdown wiki maintained by Hermes, browsable via Obsidian
- Obsidian integration: per-container vault with git sync, laptop meta-vault for cross-project navigation
- MemPalace: deep verbatim memory with semantic search and temporal knowledge graph
- Knowledge ingestion pipelines: Linear MCP (ticket triage), Granola MCP (meeting notes), Azure DevOps MCP (work items)
- Memory curation: query hierarchy across wiki, MemPalace, and OMEGA

## Known Risks

- **Upstream dependency fragility.** Hermes Agent, OMEGA Memory, and claude-tmux are community/niche projects. Abandonment or breaking changes could disrupt the stack. Mitigation: version-pin all dependencies, maintain a compatibility matrix, and design for component swappability.
- **API cost accumulation.** An always-on Director plus parallel workers consumes tokens continuously. Estimated monthly API cost: $50-150 depending on model mix and session length. Mitigation: token budget guardrails, model routing (Haiku for simple tasks, Sonnet/Opus for complex), and idle-mode for the Director.
- **Multi-client data isolation.** OMEGA Memory stores context from all projects. Without namespace isolation, a query from Project B could surface confidential context from Project A. Mitigation: per-project OMEGA namespaces, and for sensitive clients, per-project containers with separate OMEGA instances.
- **Git worktree concurrency.** Worktrees share the same .git directory. Concurrent git operations (rebase, gc) can cause lock contention. Mitigation: sequential git operations via the Director, worker-level locking, and limiting concurrent workers to 3-5.

## Vision

If this works, it becomes the foundation for every future project. Each consulting engagement starts from a container that already knows how you work, already has your methodology encoded as skills, and already has accumulated wisdom from past projects.

**6-month milestone:** 3 projects completed using the stack, OMEGA Memory contains 500+ entries, Director handles create-story tasks autonomously, setup time for new projects under 15 minutes.

**12-month milestone:** GEPA-optimized BMAD skills measurably outperform baseline, parallel worker orchestration runs without daily intervention, container template validated on 5+ fresh deployments.

**2-3 year vision:** A library of optimized BMAD skills, a rich shared memory spanning dozens of projects, and an AI Director that can autonomously drive entire sprint implementation phases while you focus on the analysis and planning that requires human judgment. The setup tax for any new project drops to zero. The quality floor rises with every engagement.
