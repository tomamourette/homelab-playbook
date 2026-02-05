---
stepsCompleted: [1, 2, 3]
inputDocuments: []
date: 2026-02-05
author: Larry
---

# Product Brief: homelab-playbook

<!-- Content will be appended sequentially through collaborative workflow steps -->

## Executive Summary

homelab-playbook is an AI-agent-driven methodology for managing homelab infrastructure with production-grade engineering rigor. It applies the BMAD (Big-picture, Multi-Agent Design) framework to infrastructure-as-code, transforming ad-hoc "tinkering" into a structured product lifecycle — from Product Brief to deployed service. By leveraging AI agents as the execution layer for process discipline (requirements gathering, architecture planning, code generation, and PR-based review), homelab-playbook makes "doing it right" easier than "doing it quick," eliminating the configuration drift, integration debt, and upgrade paralysis that plague unstructured homelab projects.

---

## Core Vision

### Problem Statement

Homelab projects universally suffer from a lack of engineering rigor. What begins as productive tinkering quickly degrades into unmaintainable technical debt: configuration drift from live SSH fixes never backported to code, "zombie containers" running undocumented services, and half-baked deployments where Day 2 integration (ingress, auth, monitoring, backups) is perpetually skipped because it's tedious. The result is "upgrade paralysis" — fear of touching core infrastructure because the true system state is opaque and undocumented.

### Problem Impact

- **Configuration Drift**: Live fixes diverge from IaC repos, causing bugs to resurface on redeployment months later
- **Integration Debt**: Services are deployed quickly via Docker Compose but never fully integrated with Traefik ingress, Authentik authentication, Prometheus monitoring, or Restic backups
- **Knowledge Rot & Upgrade Paralysis**: The operator (Larry) cannot confidently upgrade Proxmox or core services because the current state is not fully understood, leading to weekends lost debugging failed upgrades
- **Compounding Effect**: These three failure modes reinforce each other — drift creates knowledge gaps, knowledge gaps create fear of change, fear of change creates more drift

### Why Existing Solutions Fall Short

Existing homelab automation projects (DockSTARTer, HomelabOS, Ansible-NAS) are "App Stores" — they provide pre-packaged, opinionated deployments of popular services. They solve the "what to deploy" problem but not the "how to manage it" problem. Meanwhile, IaC tools (Terraform, Ansible, Docker Compose) are powerful execution layers, but they are agnostic to process — they deploy spaghetti configuration just as efficiently as clean configuration. No existing solution addresses the **process gap**: the lack of structured requirements, architecture planning, and lifecycle management that prevents technical debt from accumulating in the first place.

### Proposed Solution

homelab-playbook is a "Factory," not an "App Store." It provides a structured, BMAD-driven methodology to deploy *any* service — including custom ones — with consistent rigor. The workflow is:

1. **Intent**: "I want service X" triggers a BMAD Product Brief workflow
2. **Requirements**: An AI agent interviews the operator to define integration requirements (ingress, auth, monitoring, backups)
3. **Architecture**: An AI agent plans the implementation as Epics and Stories against the existing infrastructure stack (Proxmox, Terraform, Ansible, Docker Compose)
4. **Implementation**: An AI Coder agent generates the IaC artifacts (Docker Compose files, Ansible roles, Terraform modules) and submits them as a Pull Request
5. **Review & Deploy**: The operator reviews the PR, merges, and deploys with confidence

The critical design principle is **low-friction discipline**: AI agents absorb the "process tax" of writing specs, planning integration, and generating code, making the structured path *easier* than the ad-hoc SSH-and-hack path.

### Key Differentiators

- **Methodology over Menu**: Not a pre-packaged app catalog, but a repeatable process for deploying any service with production-grade rigor
- **Product Management for SysAdmin**: Treats infrastructure as a product with a lifecycle — User Stories for Ansible roles, PRs for config changes, documentation as a first-class deliverable
- **AI as the Process Multiplier**: Enterprise-grade process discipline is only viable for a single-person homelab because AI agents handle the heavy lifting — without agents, this level of rigor would be absurd overkill; with agents, it becomes the path of least resistance
- **"Right Way = Easy Way" Philosophy**: By making structured deployment less effort than ad-hoc hacking, drift and debt are prevented at the source rather than detected after the fact

## Target Users

### Primary Users

**Persona: Larry — The Disciplined Homelabber**

- **Role**: Solo homelab operator managing a Proxmox-based infrastructure stack
- **Environment**: Multi-node homelab running Terraform, Ansible, and Docker Compose; works primarily from VS Code terminal
- **Motivation**: Wants production-grade reliability and documentation for personal infrastructure without the manual overhead of maintaining it
- **Core Tension**: Values engineering discipline (documentation, planning, code review) but lacks the time to enforce it manually across every service and change

**Three Operating Modes:**

1. **Planner Mode** ("I have an idea")
   - Creative, exploratory sessions — typically weekend deep dives
   - Wants to describe the desired end state ("block ads network-wide") without worrying about YAML syntax
   - UX: Terminal-first. Invokes BMAD workflows from VS Code terminal (e.g., `bmad plan "Block ads"`), agent interviews inline — no web UIs, no context switching
   - Interaction pattern: 1-2 hour focused sessions for new major services

2. **Reviewer Mode** ("Code Review")
   - Critical, quality-gate sessions — evaluating agent-generated changes against best practices
   - UX: PR-based. Agent submits standard Pull Requests (GitHub/Gitea) with exact YAML diffs. Larry reviews in VS Code or web UI. Can ask the agent to explain specific changes interactively
   - Interaction pattern: 15-30 minute review sessions, potentially asynchronous

3. **Operator Mode** ("Maintenance/Fix")
   - Urgent, reactive sessions — something is broken or needs updating, often evening maintenance
   - Needs the agent to have **topology awareness**: knows which services run on which nodes, where logs are mounted, relevant file paths — acts as an intelligent index of the system
   - UX: Quick commands ("Check Paperless logs") without needing to remember IP addresses or file paths
   - Critical design constraint: Evening maintenance must be **safe enough** that a quick fix at 10 PM doesn't spiral into a 3 AM debugging session

**Problem Experience:**
- Configuration drift from live fixes never backported to IaC
- Integration debt from skipping Day 2 work (auth, monitoring, backups)
- Upgrade paralysis from opaque system state

**Success Vision:**
- The "aha!" moment is the first failed deployment — Larry pushes a bad config, something breaks, and instead of panic, he runs `git revert` and redeploys the previous known-good state. The realization that "I can't permanently break this" is the victory condition.

### Secondary Users

**Family Members — Service Consumers**
- End users of deployed services (Plex, Home Assistant, etc.)
- Care about uptime and functionality, not the Git repo or deployment process
- Their needs are met indirectly: better-managed infrastructure = better uptime = happier family
- No direct interaction with homelab-playbook itself

**Future: BMAD-Enabled Homelabbers (Distant Secondary)**
- Potential open-source community of homelabbers who adopt the BMAD methodology
- Explicitly deprioritized: optimize for Larry's single-player workflow first
- May influence future decisions around documentation and generalization, but not MVP scope

### User Journey

**Discovery → Onboarding → Core Usage → Success Moment → Long-term**

1. **Discovery**: Larry (the creator) doesn't need to "discover" the product — he's building it to solve his own pain. Future users would discover it through homelab communities (r/homelab, r/selfhosted) or BMAD ecosystem documentation
2. **Onboarding**: Initialize the playbook repo, configure BMAD agents with infrastructure topology (node inventory, service registry), connect to existing IaC repos (`homelab-infra`, `homelab-apps`)
3. **Core Usage**: Cycles between three modes — weekend Planning sessions to add new services, Reviewer sessions to approve agent-generated PRs, and evening Operator sessions for maintenance and quick fixes
4. **Success Moment**: First `git revert` after a bad deploy. The realization that the entire infrastructure state is version-controlled, documented, and recoverable transforms the homelab from a source of anxiety into a source of confidence
5. **Long-term**: The playbook becomes the single source of truth for the homelab. Every service, every config change, every integration decision is captured. Upgrades become routine, not terrifying. The "Right Way" is now muscle memory because it's the easiest path
