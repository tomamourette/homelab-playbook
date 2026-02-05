# Homelab Playbook Management

**Project:** Homelab Infra & Apps Supervision  
**Framework:** BMAD Method (Breakthrough Method of Agile AI Driven Development)  
**Supervisor:** Claude (OpenClaw)  
**Executor:** Claude Code CLI  

> **📖 New here?** Read [ARCHITECTURE.md](../ARCHITECTURE.md) to understand the three-repo model and how homelab-playbook coordinates code generation.

## Overview

This folder contains project management artifacts using BMAD Method to organize homelab development, planning, and execution.

**Important:** homelab-playbook is an **orchestration layer**, not infrastructure code. Generated IaC lives in `homelab-infra` (Terraform/Ansible) and `homelab-apps` (Docker Compose).

### Structure

- **`/workflows/`** - BMAD workflow outputs (specs, PRDs, architecture)
- **`/stories/`** - Story development and status
- **`/logs/`** - Execution logs and decision records
- **`/docs/`** - Project documentation and decisions

## Current Status

🚀 **Phase:** Initial Setup  
📋 **Next:** Define project scope and create product brief

## How It Works

1. **You (Larry)** define requirements or identify work
2. **I (Supervisor)** coordinate and plan using BMAD workflows
3. **Claude Code CLI** executes coding/infrastructure tasks
4. **Documentation** flows into `/workflows/` and `/stories/`

## Quick Start

Run a BMAD workflow:
```bash
/bmad-help                # Get guidance
/product-brief            # Define problem & MVP
/quick-spec               # Fast technical spec
/dev-story                # Implement a story
```

---

Last Updated: 2026-02-05
