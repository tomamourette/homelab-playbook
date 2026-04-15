---
stepsCompleted: [1, 2, 3, 4, 5, 6]
inputDocuments: []
workflowType: 'research'
lastStep: 6
research_type: 'technical'
research_topic: 'Always-On AI Director for Parallel BMAD Development'
research_goals: 'Design an always-on director agent on the homelab project container that orchestrates parallel BMAD story development via Claude Code worktrees, with self-learning skill optimization, persistent shared memory, and crash-proof execution.'
user_name: 'tomamourette'
date: '2026-04-01'
web_research_enabled: true
source_verification: true
---

# Technical Research Report: Always-On AI Director for Parallel BMAD Development

**Date:** 2026-04-01
**Author:** tomamourette
**Research Type:** Technical

---

## 1. Executive Summary

### The Problem

Tom uses a Proxmox homelab with Claude Code via VS Code tunnel for BMAD-driven development. The current pain points:

1. **Session fragility** — VS Code tunnel + Claude Code terminals break on laptop restart
2. **Manual orchestration** — Manually managing which BMAD stories to run, in which terminal, in which order
3. **No learning** — BMAD skills don't improve over time from execution experience
4. **No shared context** — Parallel sessions don't share memory or coordinate
5. **No crash recovery** — If a session dies mid-story, progress is lost

### The Solution

An always-on director agent running on the project container that:
- Survives all disconnects (runs in tmux on the server)
- Knows BMAD methodology (loaded as skills)
- Spawns parallel Claude Code workers in git worktrees
- Uses shared persistent memory across all sessions (OMEGA Memory)
- Self-learns and optimizes BMAD skills (GEPA)
- Recovers from crashes (DBOS durable execution)
- Escalates to the user only when confidence is below 90%

### Research Evolution

This research started as an investigation into cloud ephemeral containers (Azure, Cloudflare, DevPod). The key finding was that **cloud containers are overkill** — git worktrees on the same project container are simpler, faster, and free. The real problems are orchestration, persistence, and learning. Cloud containers remain a valid option for future scale-out but are not the immediate path.

---

## 2. Architecture

```
PROJECT CONTAINER (Proxmox, always-on)
│
├── OMEGA Memory (MCP server + SQLite)          ← SHARED BRAIN
│   ├── Persistent memory across all sessions
│   ├── Auto-captures lessons/decisions (hooks)
│   ├── File/branch claims (prevents collision)
│   ├── Task queue with dependencies
│   └── Vector + FTS5 semantic search
│
├── DIRECTOR (Hermes Agent in tmux)             ← ORCHESTRATOR
│   ├── Knows BMAD methodology (loaded as skills)
│   ├── Self-learning: improves skills via GEPA
│   ├── Durable execution: checkpoints to Postgres (DBOS)
│   ├── Cron: automated sprint reviews, story creation
│   ├── Confidence escalation: < 90% → asks user
│   └── Connects to OMEGA via MCP
│
├── WORKER 1 (Claude Code in tmux + worktree feat/1-1)
│   ├── OMEGA hooks: auto-receives relevant context
│   ├── Runs: create-story → dev-story → code-review
│   ├── Claims files via OMEGA coordination
│   └── Learns: outcomes captured to shared memory
│
├── WORKER 2 (Claude Code in tmux + worktree feat/2-1)
│   └── Same — shared memory, isolated worktree
│
└── claude-tmux (TUI)                           ← MONITORING
    └── Real-time status of all sessions

YOU: Connect via VS Code tunnel or SSH from anywhere.
Laptop dies? Everything keeps running.
```

---

## 3. The BMAD Workflow (What Gets Parallelized)

### Standard Greenfield Flow

```
Phase 1: ANALYSIS      → Product brief, domain/market/tech research
Phase 2: PLANNING      → PRD, UX design, validation
Phase 3: SOLUTIONING   → Architecture, epics + stories, readiness check
Phase 4: IMPLEMENTATION → Sprint planning → [create-story → dev-story → code-review] loop
```

Phases 1-3 are inherently interactive — keep them manual with BMAD skills.
Phase 4 (the dev loop) is the parallelization target.

### The Per-Story Cycle

```
1. create-story  → Context engine: analyzes PRD, architecture, previous stories,
                    git history. Generates comprehensive story file.

2. dev-story     → Red-green-refactor TDD implementation.
                    Runs continuously until all tasks complete.
                    Status → "review"

3. code-review   → 3 parallel adversarial review agents:
                    - Blind Hunter (diff only, no context)
                    - Edge Case Hunter (diff + project access)
                    - Acceptance Auditor (diff + spec + context)
                    Triage → patch/defer/dismiss.
                    If issues → back to dev-story.
                    If clean → status = "done"
```

### Parallelization Rules

| Scenario | Parallel? | Why |
|----------|----------|-----|
| Stories across different epics | **Yes** | No code dependency between epics |
| Stories in same epic | **Conditional** | Earlier stories inform later context |
| dev-story + code-review (same story) | **No** | Sequential by design |
| Multiple story pipelines | **Yes** | Each in its own worktree/branch |

### Dependency Graph

```
DIRECTOR analyzes sprint-status.yaml + epics:

Epic 1: S1.1 → S1.2 → S1.3  (sequential within epic)
Epic 2: S2.1 → S2.2          (sequential within epic)
Epic 3: S3.1 → S3.2          (sequential within epic)

But: S1.1 ∥ S2.1 ∥ S3.1     (parallel across epics)
```

### Confidence-Based Escalation

```
Worker encounters a question:

  Confidence >= 90%  → Worker decides autonomously, logs in Dev Agent Record
  Confidence 70-89%  → Worker asks Director (has full project context)
  Confidence < 70%   → Director escalates to USER
                       Worker pauses until user responds
```

---

## 4. Tool Stack

### 4.1 OMEGA Memory — Shared Brain

**What:** Local-first persistent memory for AI coding agents. Runs as MCP server, stores in SQLite. No cloud, no API keys.

**GitHub:** [omega-memory/omega-memory](https://github.com/omega-memory/omega-memory)
**License:** Apache 2.0 (core). Pro: paid.

**Setup:**
```bash
pip install omega-memory[server]
omega setup     # Downloads 90MB ONNX embedding model
omega doctor    # Registers MCP server + installs Claude Code hooks
```

**Requirements:** Python 3.9+, ~337MB RAM after first query, SQLite (included)

**How it works:**
- **25 MCP tools** for storing, querying, managing memories
- **7 Claude Code hooks** auto-inject at lifecycle events:
  - `SessionStart` → Delivers welcome briefing with recent relevant memories
  - `UserPromptSubmit` → Auto-captures lessons and decisions
  - `PostToolUse` → Surfaces relevant memories during editing
  - `SessionStop` → Generates session summary
- **Multi-layered search:** 384-dim vector embeddings (sqlite-vec) + FTS5 full-text + type-weighted scoring + contextual re-ranking
- **Auto-deduplication:** SHA256 exact match + semantic similarity (0.85+ threshold)
- **Memory evolution:** Related content (55-95% similar) appends to existing memories
- **TTL policy:** Session summaries expire after 1 day; lessons persist indefinitely

**Pro tier adds (29 coordination tools):**
- File/branch locking (prevents parallel workers from colliding)
- Task queues with dependencies
- Agent-to-agent messaging
- Intelligent LLM routing
- Knowledge base ingestion (PDFs, markdown, web)

**Why it matters for your architecture:**
- Worker 1 learns "auth module needs specific import pattern" → Worker 2 automatically receives that context
- All workers share one memory pool — compound learning across the entire sprint
- File claims prevent two workers from editing the same file

**Limitations:**

| Limitation | Impact | Workaround |
|-----------|--------|------------|
| Coordination tools are pro (paid) | File locking, task queues need license | Core memory (free) + git worktree isolation handles most cases |
| 90MB embedding model download | One-time setup cost | Downloads automatically, runs locally |
| ~337MB RAM after first query | Memory footprint on container | Acceptable for a project container |
| No Hermes Agent native integration | Hermes uses own memory system | Hermes connects via MCP; or use OMEGA as the sole memory layer |
| Library-only mode saves RAM but loses MCP | CI/CD scenarios | Use server mode for Director/Workers |

---

### 4.2 Hermes Agent — Director / Orchestrator

**What:** Self-improving CLI agent with persistent memory, autonomous skill creation, subagent spawning, and cron scheduling.

**GitHub:** [NousResearch/hermes-agent](https://github.com/nousresearch/hermes-agent)
**License:** MIT
**Docs:** [hermes-agent.nousresearch.com](https://hermes-agent.nousresearch.com/docs/)

**Setup:**
```bash
# Prerequisites: git only. Installer handles Python 3.11, Node.js, uv
curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash
hermes setup    # Configuration wizard
hermes model    # Select LLM (Claude via Anthropic, OpenRouter, etc.)
hermes tools    # Enable/disable tool groups
hermes doctor   # Diagnose issues
```

**Requirements:** Linux/macOS/WSL2, git. Python 3.11 + Node.js auto-installed.

**Config structure:**
```
~/.hermes/
├── config.yaml          # Model, terminal, memory, tools, display
├── .env                 # API keys (ANTHROPIC_API_KEY, etc.)
├── SOUL.md              # Agent identity/personality
├── memories/
│   ├── MEMORY.md        # Agent notes (2,200 char limit)
│   └── USER.md          # User profile (1,375 char limit)
├── skills/              # Agent-created + installed skills
├── cron/                # Scheduled jobs
└── sessions/            # Conversation history (SQLite FTS5)
```

**Key capabilities:**

| Capability | Details |
|-----------|---------|
| **Skills system** | SKILL.md format (agentskills.io standard). Auto-creates after complex tasks. Self-improves during use. Progressive disclosure (3 tiers). 7 install sources including hub, GitHub, marketplace. |
| **Memory** | MEMORY.md + USER.md injected at session start (frozen snapshot). FTS5 search across all past sessions. Honcho dialectic user modeling (optional). |
| **Subagents** | Spawn isolated subagents with own conversation, terminal, toolset. Only summary returns. Configurable delegation model. |
| **Scheduling** | Built-in cron with delivery to any platform. Natural language schedule definitions. |
| **Terminal backends** | local, docker, ssh, modal, daytona, singularity |
| **MCP** | Connect any MCP server (including OMEGA Memory) |
| **Models** | Anthropic, OpenRouter (200+), OpenAI, Nous Portal, custom endpoints |
| **Compression** | Auto-compresses long conversations. Configurable threshold/target ratio. |

**Terminal config for your setup:**
```yaml
terminal:
  backend: local
  cwd: "/home/developer/workspace/homelab"
  timeout: 180
  persistent_shell: true

delegation:
  model: "anthropic/claude-sonnet-4-20250514"
  provider: "anthropic"

skills:
  external_dirs:
    - /home/developer/workspace/homelab/_bmad/bmm/4-implementation
```

**BMAD skills to create:**
```
~/.hermes/skills/
├── bmad-sprint-director/SKILL.md    # Reads sprint-status, identifies next stories
├── bmad-story-pipeline/SKILL.md     # Runs create-story → dev-story → code-review
├── bmad-escalation/SKILL.md         # Confidence-based question routing
└── bmad-worktree-manager/SKILL.md   # Creates/merges/cleans git worktrees
```

**Limitations:**

| Limitation | Impact | Workaround |
|-----------|--------|------------|
| Memory cap (2,200 + 1,375 chars) | Can't store full sprint context | Use OMEGA Memory for project context; Hermes memory for agent preferences |
| Memory snapshot frozen at session start | Mid-session changes invisible | Acceptable — BMAD state lives in files |
| 90 max turns per session | Long workflows hit limit | Break into subagent calls; use `/compress` |
| No built-in durable execution | Crash mid-workflow = lost progress | Add DBOS layer |
| No native git worktree management | Must build custom skill | Build `bmad-worktree-manager` skill |
| No native Claude Code tool integration | Can't invoke Claude Code's tools directly | Run `claude -p` via terminal backend |
| Subagent model limited to delegation config | Can't vary model per-subagent at runtime | Set delegation to Sonnet (good balance) |

**Cost:** Free (MIT). LLM API costs only: ~$0.50-5.00 per session depending on model and length.

---

### 4.3 GEPA — Self-Learning Skill Optimization

**What:** Evolutionary text optimization framework. Reads full execution traces to diagnose failures and propose targeted improvements. ICLR 2026 Oral.

**GitHub:** [gepa-ai/gepa](https://github.com/gepa-ai/gepa)
**License:** Open source

**Setup:**
```bash
pip install gepa
```

**Requirements:** Python 3.9+, LLM API access. No GPU, no database.

**How it works — the 5-step loop:**
```
1. SELECT candidate from Pareto frontier
2. EXECUTE on sample data, capture full execution traces
3. REFLECT: LLM reads traces, diagnoses WHY it failed
4. MUTATE: Generate improved variant using accumulated lessons
5. ACCEPT if improved; update Pareto front → REPEAT
```

The key innovation: **Actionable Side Information (ASI)** — instead of reducing outcomes to a score, GEPA feeds the full trace (errors, logs, timing) to a reflection LLM.

**For BMAD — concrete application:**
```python
from gepa.optimize_anything import optimize_anything, GEPAConfig, EngineConfig

# Load current BMAD skill
with open("_bmad/bmm/4-implementation/bmad-create-story/workflow.md") as f:
    seed_skill = f.read()

# Define evaluation function
def evaluate_skill(candidate_skill: str) -> float:
    # Run skill on test story, measure quality
    result = run_bmad_skill(candidate_skill, "2-1-api-setup")
    return (0.25 * result.story_completeness +
            0.25 * result.test_pass_rate +
            0.25 * (1.0 - result.review_findings / 10) +
            0.25 * result.time_score)

# Optimize
result = optimize_anything(
    seed_candidate=seed_skill,
    evaluator=evaluate_skill,
    objective="Produce better BMAD stories with fewer code review findings",
    config=GEPAConfig(engine=EngineConfig(max_metric_calls=200)),
)
```

**Proven results (gskill — GEPA's skill learner):**
- Mini-SWE-Agent on Bleve: 24% → 93% resolve rate
- Claude Haiku on Bleve: 79.3% → 98.3% pass rate (also faster: 173s → 142s)
- Skills learned on cheap models transfer to stronger ones

**Limitations:**

| Limitation | Impact | Workaround |
|-----------|--------|------------|
| Requires measurable metric | Must define quantitative evaluation | Composite score: story quality + test pass + review findings |
| 100-500 evaluations needed | Each = LLM API call | Use Haiku for evaluation, Sonnet for reflection |
| BMAD adapter doesn't exist | ~100 lines of Python to build | Follow adapter guide; reference DSPy adapter |
| Batch process, not real-time | Can't optimize during a sprint | Run overnight as scheduled job |
| Optimized skills may diverge | Could break other workflows | Validate on held-out test set; keep baseline |

**Cost:** ~$0.20-1.00 per optimization run (200 evals). Overnight batch for 5 BMAD skills: ~$1-5.

---

### 4.4 DBOS — Crash-Proof Workflow Execution

**What:** Open-source library that makes Python functions durable by checkpointing to Postgres. No orchestration server.

**GitHub:** [dbos-inc/dbos-transact-py](https://github.com/dbos-inc/dbos-transact-py)
**License:** Open source
**Docs:** [docs.dbos.dev](https://docs.dbos.dev)

**Setup:**
```bash
pip install dbos 'fastapi[standard]'
dbos init --template dbos-app-starter

# Set Postgres connection
export DBOS_SYSTEM_DATABASE_URL="postgresql://user:pass@localhost:5432/dbos"
```

**Requirements:** Python 3.9+, PostgreSQL (any version). SQLite for dev. No additional infrastructure.

**How it works:**
```python
from dbos import DBOS

@DBOS.workflow()
def story_pipeline(story_key: str):
    create_story(story_key)       # ← Checkpointed after completion
    dev_story(story_key)          # ← If crash here, resumes from this step
    result = code_review(story_key)
    if result.needs_fixes:
        dev_story(story_key)
    mark_done(story_key)

@DBOS.step()
def create_story(story_key: str):
    subprocess.run(["claude", "-p", f"Run /bmad-create-story {story_key}"])
```

**Crash recovery:**
1. Process dies mid-`dev_story`
2. Process restarts
3. DBOS checks Postgres: "story_pipeline for 2-1 was at step 2"
4. Skips `create_story` (already completed)
5. Re-runs `dev_story` from start of that step
6. Continues normally

**Human-in-the-loop (for escalation):**
```python
@DBOS.workflow()
def escalation_workflow(question: str):
    notify_user(question)                          # Send notification
    answer = DBOS.recv("user_answer")              # Wait indefinitely, durable
    return answer                                  # Resume when user responds
```

**Limitations:**

| Limitation | Impact | Workaround |
|-----------|--------|------------|
| Requires Postgres | Must run alongside container | Homelab likely has Postgres; or use SQLite for dev |
| Checkpoints at step boundaries | 2-hour step crashes at 1:59 = restart step | Break into smaller sub-steps |
| Conductor (distributed recovery) needs paid license | Single-process only for free | Single-process sufficient for your case |
| Steps must be idempotent | Re-running step must be safe | Check if output exists before re-running |
| Version mismatch on upgrade | Changing code while workflows in-flight | Keep old workers until in-flight workflows complete |

**Cost:** Free (open source). Only dependency is Postgres.

---

### 4.5 claude-tmux — Session Monitoring

**What:** Rust TUI for managing multiple Claude Code tmux sessions with real-time status, worktree support, and PR support.

**GitHub:** [nielsgroen/claude-tmux](https://github.com/nielsgroen/claude-tmux)

**Setup:**
```bash
cargo install claude-tmux
echo 'bind-key C-c display-popup -E -w 80 -h 30 "~/.cargo/bin/claude-tmux"' >> ~/.tmux.conf
tmux source-file ~/.tmux.conf
```

**Requirements:** tmux, Rust/Cargo (one-time build), optionally `gh` for PR features.

**Status indicators:** ● Working | ○ Idle | ◐ Waiting for input | ? Unknown

**What it gives you:** See all running sessions at a glance, switch between them with j/k + Enter, create/kill/rename from TUI, fuzzy search by name.

---

## 5. Best Practices from Production (2026)

Based on Addy Osmani's analysis, Anthropic's agentic coding trends report, and production at Stripe (1000+ agent PRs/week):

### The Factory Model

```
1. PLAN    — Write detailed specs with acceptance criteria (specs are leverage)
2. SPAWN   — Create team, assign agents to isolated worktrees
3. MONITOR — Check progress every 5-10 min (don't hover)
4. VERIFY  — Run tests and code review (verification is the bottleneck)
5. INTEGRATE — Merge branches, resolve conflicts
6. RETRO   — Update AGENTS.md/CLAUDE.md with new patterns
```

### Critical Rules

| Rule | Why |
|------|-----|
| **Never let 2 agents edit the same file** | Conflicts kill velocity. Worktree isolation + OMEGA file claims. |
| **3-5 agents is the sweet spot** | 3 focused > 5 scattered. Token costs scale linearly. |
| **5-6 tasks per agent** | Keeps agents productive without context overflow. |
| **Set MAX_ITERATIONS=8** | Force reflection before retry. Prevents stuck loops. |
| **Require plan approval for risky changes** | Catching flawed plan < fixing flawed code. |
| **Use hooks for quality gates** | Auto-run tests on task completion. Agent keeps working until green. |
| **Your spec is the leverage** | Vague specs multiply errors across parallel runs. BMAD's create-story solves this. |
| **Human-curated CLAUDE.md** | Research shows ~4% improvement. LLM-generated versions offer no benefit. |

### The Ralph Loop Pattern

```
Agent picks task → implements → validates →
  If passing: commits → resets context → picks next task
  If failing: reflects → retries (max 8) → escalates
```

Avoids context overflow by resetting between tasks while maintaining continuity via git history and shared OMEGA memory.

---

## 6. BMAD Workflow Adaptations

The current BMAD workflows are designed for single-session sequential execution. To support the Director architecture:

| Component | Current | Needed |
|-----------|---------|--------|
| **sprint-status.yaml** | Single writer | Director-only writes (workers update story files) |
| **create-story** | Reads previous story learnings | First story per epic doesn't need this; OMEGA provides cross-session context |
| **dev-story** | Updates sprint-status directly | Worker updates story file; Director syncs sprint-status |
| **code-review** | Interactive (halts for user input) | Autonomous mode: auto-apply patches, escalate via confidence |
| **File conflicts** | Not considered | OMEGA file claims + worktree isolation |
| **Learning** | None | OMEGA auto-captures; GEPA optimizes overnight |

### Autonomous Code Review Mode

```
1. Gather context (auto-detect: branch diff vs main)
2. Launch 3 parallel review agents (unchanged from BMAD)
3. Triage findings:
   - decision_needed + confident → apply as patch
   - decision_needed + not confident → escalate to Director
   - patch → auto-apply
   - defer → log and continue
   - dismiss → drop
4. All resolved → status = "done"
5. Unresolved → Director decides or escalates to user
```

---

## 7. Implementation Roadmap

### Phase 1: Persistent Sessions (Week 1)
- Install tmux + claude-tmux on project container
- Set up named tmux sessions for Claude Code work
- Test: laptop restart → sessions survive → reconnect and continue
- **Outcome:** No more lost work from disconnects

### Phase 2: Shared Memory (Week 1-2)
- Install OMEGA Memory on project container
- Configure hooks in Claude Code settings
- Test: start session → work on story → end session → start new session → verify context carries over
- **Outcome:** Sessions share context and learn from each other

### Phase 3: Director Proof of Concept (Week 2-3)
- Install Hermes Agent on project container
- Create BMAD Director skills:
  - `bmad-sprint-director` — reads sprint-status, identifies parallelizable stories
  - `bmad-story-pipeline` — orchestrates create-story → dev-story → code-review
  - `bmad-worktree-manager` — creates/merges/cleans worktrees
  - `bmad-escalation` — confidence-based routing
- Connect Hermes to OMEGA via MCP
- Test: Director runs one story end-to-end autonomously
- **Outcome:** Single-story automation works

### Phase 4: Parallel Workers (Week 3-4)
- Director spawns multiple Claude Code subagents in worktrees
- Each worker runs the story pipeline independently
- OMEGA coordinates file claims between workers
- Director manages sprint-status.yaml and merges results
- Test: 2-3 stories processed in parallel across epics
- **Outcome:** Parallel execution with coordination

### Phase 5: Self-Learning (Week 5-6)
- Install GEPA
- Build BMAD adapter (~100 lines Python)
- Set up scheduled optimization (Hermes cron)
- Test: run 200 evaluations on create-story skill → measure improvement
- **Outcome:** BMAD skills measurably improve over time

### Phase 6: Crash Recovery (Week 6-7)
- Install DBOS, connect to Postgres
- Wrap Director's workflow in `@DBOS.workflow()` / `@DBOS.step()`
- Test: kill Director mid-story → restart → resumes from last step
- **Outcome:** Crash-proof pipeline

---

## 8. Obsidian Integration — Reading BMAD Output & Wiki

### 8.1 The Use Case

BMAD outputs markdown files (PRDs, architecture docs, story files, sprint status) to `homelab-playbook/_bmad-output/`. You also have a wiki repo with project documentation. You want to read and navigate these from Obsidian with live updates as Claude Code and the Director produce new content.

### 8.2 Three Viable Approaches

#### Option A: Open the Repo as an Obsidian Vault (Recommended)

The simplest approach — point Obsidian directly at the project folder or a subfolder:

```
Obsidian vault = /home/developer/workspace/homelab/homelab-playbook/_bmad-output/
```

Or for broader access:
```
Obsidian vault = /home/developer/workspace/homelab/
```

**How to access from your laptop:**
Since the files live on the Proxmox container, you need a sync mechanism:

**Option A1: Obsidian Git Plugin** (best fit)
- Install [obsidian-git](https://github.com/Vinzent03/obsidian-git) plugin
- Point it at the git repo containing BMAD output
- Auto-pull every 1-5 minutes to get latest changes
- Read-only from Obsidian's perspective (Claude Code writes, you read)
- **Custom Base Path** setting: point to `homelab-playbook/_bmad-output/` subfolder if you only want BMAD output

```
Setup:
1. Clone the homelab repo to your laptop
2. Open the repo (or subfolder) as Obsidian vault
3. Install Obsidian Git plugin
4. Settings → Auto pull interval: 1 minute
5. Settings → Pull updates on startup: enabled
6. Settings → Custom base path: homelab-playbook/_bmad-output (optional)
```

**Pros:** Simple, uses existing git workflow, version history built-in, works offline
**Cons:** Not real-time (1-5 min delay), requires git push from container side

**Making it work with the Director:** Add a post-story hook that auto-commits and pushes BMAD output changes:
```bash
# In Hermes cron or Claude Code hook
cd /home/developer/workspace/homelab
git add homelab-playbook/_bmad-output/
git commit -m "Update BMAD output" --allow-empty
git push
```

**Option A2: Self-hosted LiveSync** (real-time, more setup)
- Uses CouchDB for real-time sync between devices
- Install CouchDB on your Proxmox homelab (Docker container)
- Install [obsidian-livesync](https://github.com/vrtmrz/obsidian-livesync) plugin
- Changes appear instantly on all connected devices

```bash
# CouchDB on homelab (Docker)
docker run -d --name couchdb \
  -e COUCHDB_USER=admin \
  -e COUCHDB_PASSWORD=<password> \
  -p 5984:5984 \
  couchdb:latest
```

**Pros:** True real-time sync, end-to-end encryption, conflict resolution, works across all devices including mobile
**Cons:** Extra infrastructure (CouchDB), more complex setup, separate from git

**Option A3: Remotely Save Plugin** (simple cloud sync)
- Uses WebDAV, S3, or other storage backends
- If you have a Nextcloud instance on your homelab, point it there via WebDAV

**Pros:** Easy setup with existing Nextcloud/WebDAV
**Cons:** Not real-time, separate from git, less reliable conflict handling

### 8.3 Recommended Setup

**For your workflow:**

```
┌─────────────────────────────────────────────────┐
│  PROJECT CONTAINER                              │
│  Claude Code / Director writes to:              │
│  homelab-playbook/_bmad-output/                 │
│          ↓ (git commit + push)                  │
│                                                 │
│  Git repo (homelab)                             │
└────────────────┬────────────────────────────────┘
                 │ git pull (auto, every 1 min)
                 ↓
┌─────────────────────────────────────────────────┐
│  YOUR LAPTOP                                    │
│  Obsidian vault = cloned repo                   │
│  Obsidian Git plugin: auto-pull every 1 min     │
│                                                 │
│  Reads:                                         │
│  ├── _bmad-output/planning-artifacts/           │
│  │   ├── prd.md                                 │
│  │   ├── architecture.md                        │
│  │   ├── epics.md                               │
│  │   └── research/                              │
│  ├── _bmad-output/implementation-artifacts/     │
│  │   ├── sprint-status.yaml                     │
│  │   ├── 1-1-user-auth.md                       │
│  │   └── 2-1-api-setup.md                       │
│  └── docs/ (wiki)                               │
└─────────────────────────────────────────────────┘
```

### 8.4 Useful Obsidian Plugins for BMAD Output

| Plugin | Purpose |
|--------|---------|
| **[Obsidian Git](https://github.com/Vinzent03/obsidian-git)** | Auto-sync with git repo |
| **[Dataview](https://github.com/blacksmithgu/obsidian-dataview)** | Query YAML frontmatter in story files (status, sprint, dates) |
| **[Kanban](https://github.com/mgmeyers/obsidian-kanban)** | Visualize sprint-status as kanban board |
| **[Tasks](https://github.com/obsidian-tasks-group/obsidian-tasks)** | Track task checkboxes across story files |
| **[Mermaid](https://mermaid.js.org/)** | Render architecture diagrams (built-in to Obsidian) |
| **[Folder Notes](https://github.com/LostPaul/obsidian-folder-notes)** | Auto-create index notes per folder |

### 8.5 Dataview Example — Sprint Dashboard

Create a file `Sprint Dashboard.md` in your vault:

```markdown
# Sprint Dashboard

## Stories by Status
```dataview
TABLE status, file.name as "Story"
FROM "implementation-artifacts"
WHERE contains(file.name, "-")
SORT status ASC
```

## Ready for Dev
```dataview
LIST
FROM "implementation-artifacts"
WHERE status = "ready-for-dev"
```

## In Progress
```dataview
LIST
FROM "implementation-artifacts"
WHERE status = "in-progress"
```
```

### 8.6 Limitations

| Limitation | Impact | Workaround |
|-----------|--------|------------|
| Git sync is not real-time | 1-5 min delay | Use LiveSync (CouchDB) if real-time is critical |
| Obsidian Git requires git on device | Mobile has limited git support | Use Remotely Save for mobile, Git for desktop |
| YAML frontmatter must be valid | Dataview breaks on malformed YAML | BMAD outputs valid frontmatter by design |
| Large vaults slow down Obsidian | If repo has many non-md files | Use `.obsidian/app.json` to exclude folders; or vault only the output subfolder |
| Write conflicts if editing in Obsidian | Could overwrite Claude Code output | Keep Obsidian read-only for BMAD output; only edit personal notes |

---

## 9. Cost Summary

| Component | License | Infra Cost | LLM Cost |
|-----------|---------|-----------|----------|
| **OMEGA Memory (core)** | Apache 2.0 (free) | ~337MB RAM | None (local embeddings) |
| **OMEGA Pro** | Paid | Same | None |
| **Hermes Agent** | MIT (free) | ~100MB RAM | ~$0.50-5/session |
| **GEPA** | Open source (free) | Negligible | ~$1-5/overnight batch |
| **DBOS** | Open source (free) | Postgres | None |
| **claude-tmux** | Open source (free) | Negligible | None |
| **Claude Code workers** | Anthropic subscription | Per worktree | Per session |

**Monthly estimate (3 parallel workers, 4h/day, 20 days):**
- Claude API costs: ~$50-150/mo (depending on model mix and session length)
- Infrastructure: $0 (runs on existing homelab hardware)
- Tools: $0 (all open source, except OMEGA Pro if you want coordination)

---

## 9. Cloud Scale-Out (Future Option)

If you later need more parallel capacity than your homelab can provide:

| Option | Cost (4 vCPU, 80h/mo) | Setup |
|--------|----------------------|-------|
| **DevPod + Azure B2ms** | ~$6.64/mo per worker | `devpod provider add azure` |
| **GitHub Codespaces** | ~$28.80/mo per worker | Zero config, free tier available |
| **DevPod + Hetzner** | ~$4-7/mo per worker | Cheapest EU option |

The architecture supports this: Director stays on homelab, workers can be local worktrees OR remote containers. The devcontainer.json standard makes this portable.

---

## 10. Conclusion

| Question | Answer |
|----------|--------|
| **Can BMAD stories run in parallel?** | Yes — across epics. Worktrees isolate each story. |
| **Best orchestrator?** | Hermes Agent (Director) + OMEGA Memory (shared brain) |
| **How do workers coordinate?** | OMEGA Memory file claims + git worktree isolation |
| **How do skills improve?** | GEPA overnight optimization (~$1-5/run) |
| **What if the Director crashes?** | DBOS checkpoints to Postgres, resumes from last step |
| **What if my laptop disconnects?** | Everything runs in tmux on the server. No impact. |
| **What's the first step?** | Phase 1: tmux + claude-tmux (immediate win, 1 day) |

---

## Sources

### Core Tools
- [OMEGA Memory](https://github.com/omega-memory/omega-memory) — Persistent memory MCP server for Claude Code
- [OMEGA Pro](https://omegamax.co/pro) — Multi-agent coordination add-on
- [Hermes Agent](https://github.com/nousresearch/hermes-agent) — Self-improving AI agent (Nous Research)
- [Hermes Agent Docs](https://hermes-agent.nousresearch.com/docs/)
- [Hermes Skills System](https://hermes-agent.nousresearch.com/docs/user-guide/features/skills/)
- [Hermes Memory System](https://hermes-agent.nousresearch.com/docs/user-guide/features/memory/)
- [Hermes Configuration](https://hermes-agent.nousresearch.com/docs/user-guide/configuration/)
- [awesome-hermes-agent](https://github.com/0xNyk/awesome-hermes-agent) — Community skills
- [GEPA — Reflective Text Evolution](https://github.com/gepa-ai/gepa) — Skill optimization
- [GEPA Paper — ICLR 2026 Oral](https://arxiv.org/abs/2507.19457)
- [gskill — Auto-Learning Skills for Coding Agents](https://gepa-ai.github.io/gepa/blog/2026/02/18/automatically-learning-skills-for-coding-agents/)
- [GEPA optimize_anything API](https://gepa-ai.github.io/gepa/blog/2026/02/18/introducing-optimize-anything/)
- [DBOS — Durable Execution](https://docs.dbos.dev) — Crash-proof workflows
- [DBOS Quickstart](https://docs.dbos.dev/quickstart)
- [DBOS + Pydantic AI](https://pydantic.dev/articles/pydantic-ai-dbos)
- [claude-tmux](https://github.com/nielsgroen/claude-tmux) — Session + worktree manager

### Multi-Agent Orchestration
- [Claude Code Agent Teams](https://code.claude.com/docs/en/agent-teams) — Native multi-agent (experimental)
- [Composio Agent Orchestrator](https://github.com/ComposioHQ/agent-orchestrator) — Production-grade parallel coding
- [The Code Agent Orchestra — Addy Osmani](https://addyosmani.com/blog/code-agent-orchestra/)
- [Claude Code Sub-Agent Best Practices](https://claudefa.st/blog/guide/agents/sub-agent-best-practices)
- [Claude Code Worktree Guide](https://claudefa.st/blog/guide/development/worktree-guide)
- [2026 Agentic Coding Trends Report — Anthropic](https://resources.anthropic.com/hubfs/2026%20Agentic%20Coding%20Trends%20Report.pdf)

### Session Persistence
- [Codeman — Claude Code tmux WebUI](https://github.com/Ark0N/Codeman)
- [cld-tmux — Persistent Claude Code Sessions](https://github.com/TerminalGravity/cld-tmux)
- [Google Always-On Memory Agent](https://github.com/GoogleCloudPlatform/generative-ai/tree/main/gemini/agents/always-on-memory-agent)

### BMAD Method
- [BMAD Method](https://github.com/bmad-code-org/BMAD-METHOD) — AI-driven agile development
- [agentskills.io](https://agentskills.io) — Open skill standard (Hermes-compatible)

### Obsidian Integration
- [Obsidian Git Plugin](https://github.com/Vinzent03/obsidian-git) — Git sync for vaults
- [Obsidian LiveSync](https://github.com/vrtmrz/obsidian-livesync) — Real-time CouchDB sync
- [Remotely Save Plugin](https://github.com/remotely-save/remotely-save) — S3/WebDAV/OneDrive sync
- [Dataview Plugin](https://github.com/blacksmithgu/obsidian-dataview) — Query YAML frontmatter
- [Obsidian Git + AI Collaboration Guide](https://docs.bswen.com/blog/2026-03-23-sync-obsidian-vault-git-ai-collaboration/)

### Cloud Scale-Out (Future Reference)
- [DevPod](https://devpod.sh/) — Open source dev environments
- [DevPod Azure Provider](https://github.com/loft-sh/devpod-provider-azure)
- [Claude Code Devcontainer Docs](https://code.claude.com/docs/en/devcontainer)
- [GitHub Codespaces Billing](https://docs.github.com/billing/managing-billing-for-github-codespaces/about-billing-for-github-codespaces)
- [Cloudflare Containers](https://github.com/cloudflare/containers) — Edge deployment, AI sandboxing
- [Cloudflare Sandbox SDK](https://developers.cloudflare.com/sandbox/) — Code execution for AI agents
