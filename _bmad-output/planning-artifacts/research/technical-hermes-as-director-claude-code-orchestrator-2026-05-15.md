---
stepsCompleted: [1, 2, 3, 4, 5, 6]
inputDocuments:
  - technical-hermes-agent-multi-provider-routing-2026-05-15.md
  - hermes-agent-manual-install-2026-04-08.md
workflowType: 'research'
lastStep: 6
research_type: 'technical'
research_topic: 'Hermes Agent as director orchestrating Claude Code (with BMAD + memory) for multi-agent crypto-quant work on ct-crypto-quant'
research_goals: 'Compare three Hermes→Claude integration patterns (CLI subprocess, Claude Agent SDK, MCP server). Director role = multi-agent orchestrator (Hermes runs a swarm of parallel Claude Code instances, e.g. one per BMAD agent: dev, QA, architect). Output = practical playbook with patterns, code/config examples, pitfalls, and a recommended starter architecture for the crypto-quant project.'
user_name: 'tomamourette'
date: '2026-05-15'
web_research_enabled: true
source_verification: true
---

# Hermes-as-Director: A Practical Playbook for Orchestrating Claude Code (BMAD + OMEGA) on ct-crypto-quant

**Date:** 2026-05-15
**Author:** tomamourette
**Research Type:** technical
**Subject:** Hermes Agent as director, Claude Code (BMAD + memory) as multi-agent worker swarm

---

## Executive Summary

You already run **Hermes Agent (Nous Research, v0.13.0 / 2026.5.7)** on `ct-crypto-quant`, calling LLM providers directly to do crypto-quant work. The goal of this research is to flip the topology: **let Hermes act as a director that delegates code-edit work to Claude Code workers** (each loaded with your BMAD methodology + OMEGA persistent memory), running one worker per BMAD persona (architect / dev / QA / scrum master).

Three integration mechanisms were evaluated end-to-end against current (May 2026) authoritative documentation:

| Pattern | What it is | Verdict for your setup |
|---|---|---|
| **A — CLI subprocess** | Hermes' built-in `delegate_task` shells out to `claude -p ... --output-format stream-json`, parses NDJSON events. | **Pick this for week 1.** Lowest friction; reuses your BMAD skills/personas as-is; Hermes' subagent system already does process isolation, allowed-toolset gating, and concurrency control. |
| **B — Claude Agent SDK** | A FastAPI service on ct-crypto-quant wraps `ClaudeSDKClient` per job, exposing per-tool gating via `can_use_tool`, in-process MCP servers, and structured event objects. | **Graduate here when** you need fine-grained, per-tool permission callbacks, multi-turn `resume=` continuity across delegated jobs, or in-process bindings for OMEGA / Graphiti. The Python SDK still spawns the `claude` binary internally — it's a richer harness around the same engine. |
| **C — MCP server** | A wrapper MCP server exposes `delegate_to_bmad_dev` / `delegate_to_bmad_qa` / `delegate_to_claude` tools. Hermes is a confirmed MCP client (stdio + Streamable HTTP). | **End-state target.** Cleanest, swappable, dynamically discoverable tool surface. Good once you've validated the loop with Pattern A and want to expose the same delegation primitives to other MCP hosts. |

**One non-negotiable cost note:** Anthropic announced that **starting 2026-06-15** (one month from today), Agent SDK and `claude -p` usage on Pro/Max subscriptions will draw from a **separate monthly Agent SDK credit pool**, not your interactive limits. For a 24/7 director loop, plan to bill workers via `ANTHROPIC_API_KEY` (per-token) rather than relying on subscription. (Source: [Claude Code headless docs](https://code.claude.com/docs/en/headless), accessed 2026-05-15.)

**Practical concurrency cap:** at Tier 1-2 Anthropic API limits, run **3-5 concurrent Claude workers** from one machine. Hermes' default `max_concurrent_subagents=3` is well-matched.

The recommended **starter architecture** (Section 8) uses Pattern A + a pipeline coordination pattern (architect → dev → QA), per-task git worktrees as filesystem state, OMEGA `[HANDOFF]` blocks as audit log, and an evaluator-optimizer loop wrapping the dev step with `/bmad-code-review`. A **build-it-tomorrow 4-day plan** is provided.

---

## Table of Contents

1. [Methodology](#1-methodology)
2. [Pattern A — Hermes → Claude Code CLI (subprocess)](#2-pattern-a--hermes--claude-code-cli-subprocess)
3. [Pattern B — Hermes → Claude Agent SDK](#3-pattern-b--hermes--claude-agent-sdk)
4. [Pattern C — Hermes → MCP server](#4-pattern-c--hermes--mcp-server)
5. [Hermes Agent Capabilities (verified)](#5-hermes-agent-capabilities-verified)
6. [Multi-Agent Orchestration: Cross-Cutting Concerns](#6-multi-agent-orchestration-cross-cutting-concerns)
7. [Cost, Rate Limits, Operational Concerns](#7-cost-rate-limits-operational-concerns)
8. [Recommended Starter Architecture & 4-Day Build Plan](#8-recommended-starter-architecture--4-day-build-plan)
9. [Comparison Matrix](#9-comparison-matrix)
10. [Consolidated Sources](#10-consolidated-sources)

---

## 1. Methodology

- **Research strategy:** four parallel research subagents, one per integration pattern (A/B/C) plus one for cross-cutting orchestration concerns. Each subagent ran independent live web research with WebSearch + WebFetch.
- **Source discipline:** Anthropic, Nous Research, and modelcontextprotocol.io are treated as authoritative. Every non-obvious claim cites a live URL and a confidence rating (HIGH / MEDIUM / LOW).
- **Date stamping:** today is **2026-05-15**; all "current" claims are anchored to that date.
- **Prior art reused:** `technical-hermes-agent-multi-provider-routing-2026-05-15.md` and `hermes-agent-manual-install-2026-04-08.md`.
- **Scope confirmation:** technical research scope confirmed with the user (architecture, integration patterns, implementation, performance/ops). Director role clarified as "multi-agent orchestrator running a swarm of parallel Claude Code workers, one per BMAD persona". Depth = practical playbook.

---

## 2. Pattern A — Hermes → Claude Code CLI (subprocess)

### 2.1 How it works

Hermes (long-running on `ct-crypto-quant`) spawns `claude -p "<prompt>" --output-format stream-json --verbose` per delegated task, reads NDJSON events line-by-line, parses, decides next move. Resumes follow-up turns via `--resume <session_id>`.

```
+----------------------+        spawn (PIPE stdin/stdout)        +-------------------------+
| Hermes Director      | --------------------------------------> |  claude -p ...          |
| (ct-crypto-quant)    |    NDJSON: system / stream_event /      |  (Claude Code CLI,      |
|  - planner loop      | <-- assistant / user / result --------- |   BMAD skills + memory) |
|  - parses ndjson     |                                         |  - tools under          |
|  - decides next step |    exit + final ResultMessage           |    --allowedTools       |
|  - persists session  |                                         |  - Anthropic API        |
+----------------------+                                         +-------------------------+
        |  resume with --resume <uuid>                                       |
        +--------------------------------------------------------------------+
```

### 2.2 Key CLI flags (verified against [code.claude.com/docs/en/cli-reference](https://code.claude.com/docs/en/cli-reference))

| Flag | Use |
|---|---|
| `-p`, `--print` | Headless mode, mandatory for scripted use. |
| `--output-format` | `text` / `json` / `stream-json` (NDJSON). |
| `--input-format` | `text` or `stream-json` for multi-turn over stdin. |
| `--include-partial-messages` | Token-level deltas in `stream-json`. |
| `--continue` / `--resume` / `--session-id` / `--fork-session` | Session lifecycle. Use `--session-id` so Hermes generates UUIDs upfront. |
| `--permission-mode` | `default` / `acceptEdits` / `plan` / `dontAsk` / `bypassPermissions`. **Headless: prefer `dontAsk` + tight `--allowedTools`** to avoid prompt deadlocks. |
| `--allowedTools` / `--disallowedTools` | Pattern-matched, e.g. `"Bash(pytest *)"`. |
| `--add-dir` | Extra read/write roots; does NOT load `.claude/` config from those dirs. |
| `--mcp-config` / `--strict-mcp-config` | Inject MCP servers per call. |
| `--model` | `sonnet`, `opus`, or full ID. |
| `--max-turns` / `--max-budget-usd` | Hard caps. **Always set both for an autonomous director.** |
| `--bare` | Skips auto-discovery of hooks/skills/plugins/MCP/CLAUDE.md; **requires `ANTHROPIC_API_KEY`**. Planned to become the default for `-p`. **If you want BMAD active, omit `--bare`.** |
| `--permission-prompt-tool` | Routes permission prompts to a designated MCP tool — the *supported* way to make Hermes itself the approver. |

Confidence: HIGH on all flags (verified verbatim from CLI reference).

### 2.3 Stream-JSON contract

NDJSON: one JSON object per line, terminated by `\n`. Top-level event types: `system`, `assistant`, `user`, `stream_event`, `result`. Never `json.loads` a chunk — always split on newline first.

Real-shape examples (verified from headless docs):

```json
// First event
{"type":"system","subtype":"init","session_id":"...","cwd":"...","permissionMode":"...","tools":[...],"mcp_servers":[...]}

// Token deltas
{"type":"stream_event","uuid":"...","session_id":"...","event":{"type":"content_block_delta","delta":{"type":"text_delta","text":"Hel"}}}

// Retry visibility
{"type":"system","subtype":"api_retry","attempt":1,"max_retries":5,"retry_delay_ms":2000,"error_status":429}

// Last event
{"type":"result","subtype":"success","is_error":false,"num_turns":3,"duration_ms":18421,"total_cost_usd":0.0421,"session_id":"...","result":"<final assistant text>"}
```

`subtype` on `result` can be `success` / `error_max_turns` / `error_during_execution`.

### 2.4 Concrete invocations

```bash
# 1. One-shot: implement an Ichimoku indicator, no prompts, capped spend
claude -p "Implement Ichimoku Cloud in indicators/ichimoku.py with pytest coverage" \
  --permission-mode acceptEdits \
  --allowedTools "Read,Edit,Write,Bash(pytest *),Bash(git diff *)" \
  --max-turns 25 --max-budget-usd 1.50 \
  --output-format stream-json --verbose --include-partial-messages

# 2. PR risk review piped in, structured JSON out
gh pr diff 142 | claude -p \
  --append-system-prompt "You are a quant-trading PR risk reviewer. Flag look-ahead bias, lookback leaks, position-sizing bugs." \
  --output-format json --max-turns 4 --model sonnet | jq -r '.result'

# 3. Multi-turn: Hermes generates UUID upfront, then resumes
SID=$(uuidgen)
claude -p "Plan refactor of strategy/ema_cross.py" --session-id "$SID" \
  --output-format json --max-turns 1 --permission-mode plan
claude -p "Now implement the plan" --resume "$SID" \
  --permission-mode acceptEdits --allowedTools "Read,Edit,Bash(pytest *)" \
  --output-format stream-json --verbose
```

### 2.5 Python (Hermes director-side snippet)

```python
import json, subprocess, uuid, os
sid = str(uuid.uuid4())
proc = subprocess.Popen(
    ["claude", "-p", "Implement Ichimoku indicator with tests",
     "--session-id", sid, "--output-format", "stream-json", "--verbose",
     "--include-partial-messages", "--permission-mode", "acceptEdits",
     "--allowedTools", "Read,Edit,Write,Bash(pytest *)",
     "--max-turns", "25", "--max-budget-usd", "1.50"],
    stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    text=True, bufsize=1, env={**os.environ},
    start_new_session=True)  # so SIGTERM can hit the process group

for line in proc.stdout:                     # line-buffered
    line = line.strip()
    if not line: continue
    try: evt = json.loads(line)
    except json.JSONDecodeError: continue    # tolerate noise
    t = evt.get("type")
    if t == "system" and evt.get("subtype") == "init":
        director.on_session_start(evt)
    elif t == "stream_event": director.on_delta(evt["event"])
    elif t == "assistant":    director.on_turn(evt)
    elif t == "result":       director.on_done(evt)  # has total_cost_usd, session_id
proc.wait(timeout=60)
```

### 2.6 Auth, env, ops on ct-crypto-quant

- **Two credential paths:** (a) `ANTHROPIC_API_KEY` env var → API billing per token; (b) `claude auth login` → OAuth, stored under `~/.claude/`. Headless without TTY: run `claude setup-token` once on a machine with a browser, copy the long-lived OAuth token.
- **`--bare` hardens scripted use** but skips BMAD/skills/CLAUDE.md/.mcp.json. Choose: leaner startup (`--bare` + API key) vs. BMAD active (omit `--bare`).
- **Subscription-vs-API split changes 2026-06-15** (separate Agent SDK credit pool on Pro/Max). Recommend API-key billing for the director.
- **TTY hang bug class** (issue #9026): mitigate with `dontAsk` + exhaustive `--allowedTools` + hard `proc.wait(timeout=…)`.

### 2.7 Pitfalls (Pattern A)

1. **Permission deadlock** without TTY → use `dontAsk` + tight allowlist, never `--dangerously-skip-permissions` for autonomous loops.
2. **Partial NDJSON** across PIPE reads → always split on `\n` first.
3. **10 MB stdin cap** (v2.1.128) → write large inputs to disk, pass paths.
4. **Cost runaway** in retry loops → set both `--max-turns` and `--max-budget-usd`, plus a director-side per-task ceiling.
5. **Stdout drain** required → never `proc.communicate()` on long runs; stream and drain.
6. **Signal handling** → spawn with `start_new_session=True`, send SIGTERM to the process group on cancel.
7. **Bare-mode surprises** → hooks/skills/memory/`.mcp.json` not loaded.
8. **`init` event ordering** → may be preceded by `system/plugin_install`. Don't assume strict ordering.
9. **Slash commands don't work in `-p`** → describe in prose.

### 2.8 When Pattern A is the right choice

When Hermes is the long-lived process and Claude Code work is bursty, you want OS-level isolation + per-call budget caps, you need BMAD/skills loaded inside Claude Code itself (omit `--bare`), and you don't need real-time mid-turn intervention.

---

## 3. Pattern B — Hermes → Claude Agent SDK

### 3.1 What the SDK is in 2026

Anthropic renamed `Claude Code SDK` → **Claude Agent SDK** in **September 2025** ([blog](https://claude.com/blog/building-agents-with-the-claude-agent-sdk)) to reflect that the same harness now powers research, support, and other non-coding agents.

- Python: [`anthropics/claude-agent-sdk-python`](https://github.com/anthropics/claude-agent-sdk-python), current **v0.2.82**.
- TypeScript: [`anthropics/claude-agent-sdk-typescript`](https://github.com/anthropics/claude-agent-sdk-typescript), v0.3.x.

**Breaking changes you must know:**

- `ClaudeCodeOptions` → `ClaudeAgentOptions`.
- `custom_system_prompt` + `append_system_prompt` merged into `system_prompt`.
- **`.claude/` settings/commands/subagents are no longer auto-loaded**; opt in via `system_prompt={"type":"preset","preset":"claude_code"}` and `setting_sources=["user","project","local"]`. **Easy way to silently lose your BMAD persona files.**

**Architecturally important:** the Python SDK does **not** call Anthropic's API directly. It spawns the bundled `claude` CLI as a subprocess and talks stdio JSONL. The TS SDK bundles a native binary as an optional dep. So Pattern B is a richer harness around the same engine as Pattern A — not a replacement for it.

### 3.2 How it slots in

```
┌─────────────────────────────┐         HTTPS POST /dispatch
│  Hermes Agent (Nous)        │  ───────────────────────────►  ┌──────────────────────────────┐
│  hermes-agent.nous...       │  ◄───── JSON: result+summary    │  ct-crypto-quant (.165)     │
│  "Director" LLM             │                                 │  FastAPI (uvicorn, asyncio)  │
└─────────────────────────────┘                                 │                              │
                                                                │  ┌────────────────────────┐  │
                                                                │  │ ClaudeSDKClient        │  │
                                                                │  │   system_prompt=BMAD-  │  │
                                                                │  │     dev persona        │  │
                                                                │  │   allowed_tools=[…]    │  │
                                                                │  │   can_use_tool=guard() │  │
                                                                │  │   mcp_servers={omega,  │  │
                                                                │  │     graphiti, …}       │  │
                                                                │  │   resume=<session_id>  │  │
                                                                │  └─────────┬──────────────┘  │
                                                                │            │ stdio JSONL     │
                                                                │  ┌─────────▼──────────────┐  │
                                                                │  │ bundled `claude` bin   │  │
                                                                │  │ → Anthropic API        │  │
                                                                │  └────────────────────────┘  │
                                                                └──────────────────────────────┘
```

### 3.3 Core SDK primitives

- **`query()`** — fire-and-forget single-shot, async generator (Python).
- **`ClaudeSDKClient`** (Python) / `query()` returning async-iterable + `input` stream (TS) — persistent multi-turn session, supports `interrupt()`, `set_permission_mode()`, `set_model()`, `rewind_files()`, `toggle_mcp_server()`. (Note: Python class kept the historical `ClaudeSDKClient` name; only options were renamed.)
- **`ClaudeAgentOptions`** — `system_prompt`, `model`, `fallback_model`, `allowed_tools`, `disallowed_tools`, `permission_mode`, `can_use_tool`, `mcp_servers`, `hooks`, `agents`, `max_turns`, `max_budget_usd`, `cwd`, `env`, `resume`, `fork_session`, `continue_conversation`, `setting_sources`, `cli_path`, `add_dirs`, `skills`, `plugins`, `sandbox`, `effort`, `thinking`, `include_partial_messages`, `stderr`.
- **Hooks** — `PreToolUse`, `PostToolUse`, `UserPromptSubmit`, `Stop`, `SubagentStop`, `SessionStart`, `SessionEnd`. Hook callbacks may return `{"hookSpecificOutput": {"permissionDecision": "deny", ...}}` to block tool use.
- **Programmatic subagents** — `agents={...}` dict of `AgentDefinition(description, prompt, tools, model, permissionMode, maxTurns, …)`. Invoked via the built-in `Agent` tool (must be in `allowed_tools`); subagent messages carry `parent_tool_use_id`.
- **Permission callback `can_use_tool(tool_name, input_data, ctx) → PermissionResultAllow | PermissionResultDeny`** — may rewrite `updated_input` (e.g. redirect a write into a sandbox) or deny with `interrupt=True`.
- **Sessions** — capture `session_id` from first `SystemMessage(subtype="init")`, then pass `resume=<id>` (optionally `fork_session=True`) to a later call.
- **In-process MCP** — `create_sdk_mcp_server` registers tools as ordinary Python functions; no subprocess, full type hints, easy to bind to OMEGA/Graphiti directly.

### 3.4 Worked example (FastAPI on ct-crypto-quant)

```python
# /srv/hermes-dispatcher/app.py
import os
from pathlib import Path
from fastapi import FastAPI
from pydantic import BaseModel
from claude_agent_sdk import (
    ClaudeSDKClient, ClaudeAgentOptions,
    AssistantMessage, TextBlock, ResultMessage, SystemMessage,
)
from claude_agent_sdk.types import (
    PermissionResultAllow, PermissionResultDeny, ToolPermissionContext,
)

PROJECT_ROOT = Path("/srv/projects").resolve()
BMAD_DEV = ("You are Amelia, the BMAD senior developer agent. Follow the story's "
            "acceptance criteria exactly. Edit only inside the project root. "
            "When done, emit a one-paragraph summary of files changed.")

app = FastAPI()
class Job(BaseModel):
    role: str; task: str; project: str; context: str = ""; resume: str | None = None

async def sandbox_guard(tool: str, inp: dict, ctx: ToolPermissionContext):
    if tool in {"Write", "Edit"}:
        target = Path(inp.get("file_path", "")).resolve()
        if not str(target).startswith(str(PROJECT_ROOT)):
            return PermissionResultDeny(message=f"path escapes sandbox: {target}",
                                        interrupt=True)
        return PermissionResultAllow(updated_input=inp)
    if tool == "Bash" and any(b in inp.get("command", "") for b in ("rm -rf /", "sudo")):
        return PermissionResultDeny(message="forbidden bash", interrupt=True)
    return PermissionResultAllow(updated_input=inp)

@app.post("/dispatch")
async def dispatch(job: Job):
    cwd = (PROJECT_ROOT / job.project).resolve()
    opts = ClaudeAgentOptions(
        system_prompt=BMAD_DEV,
        cwd=str(cwd),
        allowed_tools=["Read", "Write", "Edit", "Glob", "Grep", "Bash"],
        permission_mode="default",          # fall through to can_use_tool
        can_use_tool=sandbox_guard,
        max_turns=40,
        model="claude-sonnet-4-5",
        resume=job.resume,
        # IMPORTANT: opt back into BMAD personas/skills under v0.1.0+
        setting_sources=["project", "user", "local"],
        env={"ANTHROPIC_API_KEY": os.environ["ANTHROPIC_API_KEY"]},
    )
    summary, files, session_id = [], set(), None
    async with ClaudeSDKClient(options=opts) as c:
        await c.query(f"TASK: {job.task}\n\nCONTEXT:\n{job.context}")
        async for m in c.receive_response():
            if isinstance(m, SystemMessage) and m.subtype == "init":
                session_id = m.data["session_id"]
            elif isinstance(m, AssistantMessage):
                for b in m.content:
                    if isinstance(b, TextBlock): summary.append(b.text)
                    elif getattr(b, "name", None) in {"Write", "Edit"}:
                        files.add(b.input.get("file_path"))
            elif isinstance(m, ResultMessage):
                return {"session_id": session_id, "result": m.result,
                        "files_changed": sorted(files), "cost_usd": m.total_cost_usd,
                        "summary": "\n".join(summary)[-2000:]}
```

### 3.5 Why Pattern B beats Pattern A for an orchestrator

- Programmatic per-tool gating (no hanging interactive prompts).
- Typed event objects vs. NDJSON parsing.
- One process holds N concurrent `ClaudeSDKClient`s, each with its own `resume=` continuity.
- In-process MCP servers — bind OMEGA/Graphiti as native Python functions.
- Hooks as guardrails (PreToolUse policy, PostToolUse audit, Stop flush).
- Async-first, drops cleanly into FastAPI/uvicorn.

### 3.6 Pitfalls (Pattern B)

- **Still shells out to a `claude` binary.** Failure surface = `CLINotFoundError` / `ProcessError` / `CLIJSONDecodeError`. PATH/`cli_path` matters; container needs Node runtime for the bundled TS binary.
- **Subscription billing changes 2026-06-15** (separate Agent SDK credit pool). Plan API-key billing.
- **Settings no longer auto-load** post-rename — set `setting_sources=["project","user","local"]` or your BMAD personas vanish.
- **Context bloat over long sessions** — `resume=` rehydrates full JSONL history. Cap with `max_turns` / `max_budget_usd`; use `fork_session=True` to branch.
- **Subprocess env leakage** (issue #573) — `CLAUDECODE=1` can break SDK-from-hooks paths. Scrub env before spawning.
- **Anthropic 5xx** surfaces as `ProcessError` from the CLI subprocess, not a typed retry — wrap with tenacity.
- **TS↔Python class naming asymmetry** — TS exposes `query()` only; Python keeps `ClaudeSDKClient`.

### 3.7 When Pattern B is the right choice

When Hermes needs fine-grained per-tool gating it can't enforce itself; multi-turn continuity (`resume=`) across delegated jobs; structured parseable events for cost/audit telemetry; or in-process MCP bindings to homelab services (OMEGA, Graphiti, Proxmox).

---

## 4. Pattern C — Hermes → MCP server

### 4.1 What MCP is

The Model Context Protocol is an open JSON-RPC 2.0 protocol standardised by Anthropic for connecting LLM hosts (clients) to external servers exposing **tools**, **resources**, and **prompts**. Current spec revision: **2025-11-25**. Transports: **stdio** (local subprocess) and **Streamable HTTP** (single endpoint, POST + GET, optional SSE streams) — the latter superseded the older HTTP+SSE transport in spec 2025-03-26.

### 4.2 Two valid sub-patterns

- **C.2a "Wrap Claude Code" (recommended).** A single MCP server exposes coarse tools like `delegate_to_claude(role, task, context, allowed_paths)`. Each handler shells out to `claude -p`. Hermes is director; Claude Code remains the contractor that owns its own planning loop, file ops, and memory writes.
- **C.2b "Expose primitives".** The MCP server exposes `read_file`/`write_file`/`run_tests`/`git_commit` plus per-BMAD-skill triggers. Hermes drives the loop directly. **This isn't really "Hermes-as-director-of-Claude-Code" — Claude Code is bypassed and Hermes inherits responsibility for plan/execute/verify.** Loses BMAD's orchestration value.

**Choose C.2a** to preserve BMAD methodology and the persistent-memory contract that live inside Claude Code.

### 4.3 Hermes Agent supports MCP as a client (HIGH confidence)

Verified at [hermes-agent.nousresearch.com/docs/user-guide/features/mcp](https://hermes-agent.nousresearch.com/docs/user-guide/features/mcp) and v0.4.0 release notes:

- Config file: `~/.hermes/config.yaml` under `mcp_servers:`.
- Transports: **stdio** and **HTTP** (Streamable HTTP via `url:` + `headers:`). SSE-only servers are not supported — migrate to streamable-HTTP.
- Auth: env vars for stdio; bearer/custom headers for HTTP; **OAuth 2.1 PKCE** for servers that require it.
- Discovery: tools registered into Hermes's tool registry at startup; honours `notifications/tools/list_changed`; manual reload via `/reload-mcp`.
- Filtering: `tools.include` / `tools.exclude` per server.
- Implements `sampling/createMessage` — your MCP server can request inference back from Hermes.

Drop-in config for Tom:

```yaml
mcp_servers:
  claude-code-director:
    url: "http://ct-crypto-quant.local:8765/mcp"
    headers:
      Authorization: "Bearer ${CLAUDE_CODE_MCP_TOKEN}"
    tools:
      include: ["delegate_to_claude", "delegate_to_bmad_dev", "delegate_to_bmad_qa"]
```

### 4.4 Wrapper MCP server sketch (Python SDK)

```python
# /srv/claude-code-mcp/server.py
from mcp.server.fastmcp import FastMCP
import asyncio, json
mcp = FastMCP("claude-code-director")

async def _run_claude(role: str, task: str, ctx: str, paths: list[str]) -> str:
    prompt = f"You are the BMAD {role}. Context:\n{ctx}\n\nTask:\n{task}"
    args = ["claude", "-p", prompt, "--output-format", "stream-json", "--verbose",
            "--permission-mode", "dontAsk",
            "--allowedTools", "Read,Edit,Write,Bash"] \
           + sum([["--add-dir", p] for p in paths], [])
    proc = await asyncio.create_subprocess_exec(*args, stdout=asyncio.subprocess.PIPE)
    final = ""
    async for line in proc.stdout:
        ev = json.loads(line)
        if ev.get("type") == "result":
            final = ev.get("result", "")
    return final or "(no result)"

@mcp.tool()
async def delegate_to_claude(role: str, task: str, context: str = "",
                             allowed_paths: list[str] = []) -> str:
    """Delegate a coding task to Claude Code running BMAD persona `role`."""
    return await _run_claude(role, task, context, allowed_paths)

@mcp.tool()
async def delegate_to_bmad_dev(task: str, story_path: str) -> str:
    return await _run_claude("dev (Amelia)", f"/bmad-dev-story {story_path}", "", ["."])

@mcp.tool()
async def delegate_to_bmad_qa(feature: str) -> str:
    return await _run_claude("qa (Quinn)", f"/bmad-qa-generate-e2e-tests {feature}", "", ["."])

if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="0.0.0.0", port=8765)
```

One BMAD persona = one tool keeps Hermes's tool-selection prompt clean. Use `ctx.report_progress()` for live updates.

### 4.5 Architecture

```
   ct-crypto-quant (Hermes Agent host)
   ┌─────────────────────────────────────────┐
   │  Hermes Agent (MCP host + client)       │
   │     │                                   │
   │     │ stdio  (co-located, simplest)     │
   │     ▼                                   │
   │  wrapper-mcp.py  ──spawn──►  claude -p  │
   │                              (BMAD +    │
   │                               OMEGA)    │
   └─────────────────────────────────────────┘
                       OR (multi-host)
   Hermes (ct-crypto-quant) ──Streamable HTTP──►  ct-hermes-hub:8765
                                                  wrapper-mcp.py
                                                     │
                                                     ▼ spawn
                                                  claude -p (headless)
```

Both Hermes and Claude Code already live on `ct-crypto-quant`. **Start with stdio**; promote to streamable-HTTP only when adding a second worker host (e.g., ct-hermes-hub at .163).

### 4.6 Pros & cons vs A and B

- **Pros:** standardised, dynamically discoverable, swappable clients, tool-result streaming, capability negotiation, sampling callback, BMAD personas surface as named tools in Hermes UI.
- **Cons:** extra process/port; **transport debugging is the #1 footgun** (stdio buffering vs HTTP keepalives); spec churn (`2024-11-05 → 2025-03-26 → 2025-06-18 → 2025-11-25` in twelve months — pin SDK versions); HTTP-mode auth is your problem (bearer tokens, mTLS, or rely on Tailscale ACL); larger blast radius than direct Pattern A.

### 4.7 Pitfalls (Pattern C)

- **Transport mismatch.** If your server only speaks deprecated HTTP+SSE, Hermes fails silently or with a vague handshake error. Use `transport="streamable-http"`.
- **Tool-result size.** Truncate or summarise inside the wrapper before returning.
- **Long-running tools.** A `bmad-dev-story` run can take 10+ minutes — emit MCP `progress` notifications and configure Hermes' per-tool timeout, or Hermes reaps the call.
- **Permission/secret hygiene.** Don't leak `ANTHROPIC_API_KEY` via tool descriptions or error messages.
- **Bidirectional progress.** Hermes shows MCP progress events in its UI only if the server uses `ctx.report_progress()`.
- **OAuth scope creep.** For a Tailscale-internal homelab, a static bearer is simpler — don't over-engineer.
- **Spec churn.** Lock to spec 2025-11-25 + matching SDK; re-test on every Hermes minor.

### 4.8 When Pattern C is the right choice

When (a) Claude Code remains the agent that owns the code-edit loop, (b) you want Hermes' tool registry to *also* expose other MCP servers (GitHub, filesystem, browser), and (c) you're comfortable operating a second long-lived process. For one-shot shell-out without registry integration, Pattern A is lighter; if you need Hermes to reason over the same memory store Claude Code writes to, Pattern B (in-process MCP bindings) composes *with* Pattern C, not against it.

---

## 5. Hermes Agent Capabilities (verified)

Hermes Agent (NousResearch, **v0.13.0 / 2026.5.7**) is a long-lived autonomous agent server, not just the Hermes-4 model. Verified surface relevant to director use:

- **OpenAI-compatible** — exposes `/v1/chat/completions`; consumes any OpenAI-compatible upstream.
- **100+ providers**, including native Anthropic (API key, OAuth via Claude Max, *and* auto-detection of local Claude Code credentials), Ollama, vLLM, llama.cpp, OpenRouter, Nous Portal.
- **Subagent delegation via `delegate_task`** — spawns child AIAgent instances with isolated context, restricted toolsets (e.g. `["web"]`, `["terminal","file"]`), own terminal sessions. **Default cap: 3 concurrent subagents** (configurable). Leaf subagents get `delegation` toolset blocked unless `role="orchestrator"`, bounded by `max_spawn_depth`.
- **Parallel fan-out** — `delegate_task(tasks=[…])` accepts a list; tool execution uses a `ThreadPoolExecutor` (default 8 workers).
- **Terminal backends** — local, Docker, SSH, Daytona, Singularity, Modal. **A Hermes subagent can drive `claude` over SSH or in a sandbox.**
- **MCP client** — confirmed (Section 4.3).
- **Memory** — FTS5 cross-session recall + LLM summarisation + auto-generated skills.
- **Hermes-4 model** — 405B and 35B-A3B (MoE, 3B active), OpenAI-style tool-calling on OpenRouter, 128K context.

This means **Hermes can natively orchestrate Claude Code via Pattern A without any glue code beyond per-persona launcher scripts** — `delegate_task(toolsets=["terminal"], goal="...")` is the dispatch primitive.

---

## 6. Multi-Agent Orchestration: Cross-Cutting Concerns

### 6.1 What "director" means in 2025/2026

Anthropic's [**Building Effective Agents**](https://www.anthropic.com/research/building-effective-agents) (Dec 2024) crystallised five patterns: **prompt-chaining, routing, parallelization (voting + sectioning), orchestrator-workers, and evaluator-optimizer**. The **orchestrator-workers** pattern is the canonical match: a central LLM dynamically decomposes tasks, dispatches to workers, and synthesises — distinct from parallelization in that subtasks are *not* pre-defined.

[**How we built our multi-agent research system**](https://www.anthropic.com/engineering/multi-agent-research-system) (Anthropic, Jun 2025) is the most detailed published case study: a "lead agent" analyses the query, develops a strategy, spawns subagents in parallel as "intelligent filters". Lessons:

- Subagents need **explicit objective + output format + tool/source guidance + clear boundaries**.
- Agents systematically **under-judge effort** — bake scaling rules into prompts.
- **Small lead-agent prompt changes cause emergent behaviour shifts in workers** — change one thing at a time.

Framework taxonomy (2026): LangGraph = directed-graph supervisor-worker with checkpointed state, conditional edges, time-travel — production-grade. CrewAI = role-based hierarchical "crew", simpler mental model, weaker state. Teams typically prototype on CrewAI then migrate to LangGraph for durable state.

For your case: **you don't need either framework** — Hermes' built-in `delegate_task` is the dispatcher; BMAD's existing pipeline is the topology.

### 6.2 Coordination patterns

| Pattern | When |
|---|---|
| **Single dispatcher, sequential** | First 1-2 weeks — simplest, lowest cost, best for learning failure modes. |
| **Parallel fan-out / fan-in** | `delegate_task(tasks=[…])` for embarrassingly-parallel work (e.g., "scan these 5 strategy notebooks for data leakage" as 5 Read/Grep workers). |
| **Pipeline (architect → dev → QA)** | **Default for feature work** — matches your BMAD flow exactly. |
| **Debate / dual-Claude review** | High-blast-radius changes (anything touching strategies/risk) — two `dev` workers produce candidates, a third `reviewer` judges. Maps to evaluator-optimizer. |
| **GOAP / re-plan loop** | Hermes monitors test/lint/`/autoresearch:fix` exit codes; replans on failure. Maps cleanly onto your existing `/autoresearch:fix` skill. |

### 6.3 Shared state and memory

Three layers, in order of preference:

1. **Filesystem (source of truth).** BMAD `_bmad-output/` and story files are already SoT. Use **per-worker working directory** `/work/<task-id>/` plus shared read-only `_bmad-output/` to avoid races.
2. **OMEGA persistent memory.** Treat as **append-only audit log** during director runs: each worker writes a `[HANDOFF]` block on completion (your existing convention), Hermes reads them via OMEGA query before scheduling the next stage. Do **not** let Hermes and Claude both `omega_store` the same fact — Hermes writes plans/decisions, Claude workers write outcomes/handoffs.
3. **Message-passing only.** Hermes' `delegate_task` return value, for ephemeral results.

**Concurrency hazard:** two workers editing the same file. Mitigation: **per-task git worktrees** (`git worktree add /work/<task-id>`), with the merge step run by a single `reviewer` worker. Free undo as a bonus.

**Recommended convention:** *Filesystem = state, OMEGA = audit, `delegate_task` return = handshake.*

### 6.4 Verification / eval loops

Wire every worker output through a verifier before marking complete. Two cheap layers:

- **Hermes-side check** (free, fast): structural — does the output file exist, do tests pass, does `npm run lint` exit zero, does the BMAD story have all required sections.
- **Claude judge** (or Hermes-4 judge for cost): semantic — call `/bmad-code-review` on diffs, `/autoresearch:fix` on failures.

Anthropic's evaluator-optimizer pattern recommends a separate LLM call for evaluation when criteria are clear and iteration is valuable.

**Caveat:** 2026 LLM-as-judge literature shows judges are often **mis-calibrated and over-confident**. Run with prompt variation and use score variance as an uncertainty signal; route low-confidence verdicts to you.

You already have `/autoresearch:fix` and `/bmad-code-review` skills — they're the right primitives. Tie them in.

---

## 7. Cost, Rate Limits, Operational Concerns

### 7.1 Cost shape

- **Director turn (Hermes-4 on OpenRouter or Nous Portal):** ~2-5K tokens, cents. Negligible.
- **Worker turn (Claude Sonnet 4.5 / Opus):** a single "edit this file" assembles **50-150K tokens** of context. **$0.15-2.00 per worker turn.**
- **2026-06-15 change:** Agent SDK and `claude -p` on Pro/Max draw from a **separate monthly Agent SDK credit pool**. Plan **API-key billing** for the autonomous director; reserve subscription for your own interactive Claude Code use.

### 7.2 Rate limits (Anthropic API, May 2026 post-bump)

| Tier | RPM | ITPM | OTPM | Comfortable concurrent workers |
|---|---|---|---|---|
| 1 | 50 | ~20K | ~4K | ~2 |
| 2 | 1,000 | 40K | — | 3-5 |
| 3 | 2,000 | 80K | — | More |

Hermes' default `max_concurrent_subagents=3` is well-matched to Tier 1-2.

**Subscription side:** Pro/Max 5-hour limits doubled May 2026, peak-hours throttling removed. Steady solo use is now viable, but TOS still implies **no >1 concurrent `claude` session per seat** — for real parallelism you need API-key workers.

### 7.3 Operational concerns on ct-crypto-quant

- **Process lifecycle.** Hermes as systemd service. Workers via `delegate_task` with terminal backend = local — own shell + PID. Wrap each in `timeout 1800 claude -p …` as hard ceiling. Add `cancel_subagent(task_id)` flow.
- **Logging.** Pipe each worker's `stream-json` to `/var/log/hermes/<task-id>.jsonl`; ship to Loki via Promtail. Tag `worker=<bmad-persona>`, `task_id`, `parent=hermes`. Correlate Hermes' "thoughts" log against worker tool-uses by `task_id`.
- **Safety / blast radius.** Per worker: `--permission-mode dontAsk`, explicit `--allowedTools` (e.g. `Read,Grep,Edit` for `dev`; `Read,Grep,Bash(pytest:*)` for `qa`). `--add-dir` to scope filesystem access. Kill-switch: `systemctl stop hermes` + guarded `pkill -f "claude -p"`.
- **Dry-run.** A Hermes flag that swaps `claude` for a Hermes-4 worker with the same prompt for plan-only output, then human-approve before real Claude run.
- **Crypto-quant specific.** Workers must NOT touch `live_trading/` or `~/.config/exchange-keys/`. Belt-and-braces:
  - (a) run each worker as unprivileged user `hermes-worker` whose primary group has no read on those paths;
  - (b) `--add-dir` only the safe subtree;
  - (c) a deny-list pre-edit hook on `live_trading/**` that exits non-zero.

---

## 8. Recommended Starter Architecture & 4-Day Build Plan

### 8.1 Recommendation

**Pattern A** (Hermes' built-in `delegate_task` with `terminal=local` shelling out to `claude -p ... --output-format stream-json`) as the integration mechanism.

**Coordination = pipeline (architect → dev → QA) as default**, with `delegate_task(tasks=[…])` parallel fan-out for research/scouting stages, and an evaluator-optimizer loop wrapping the dev step via `/bmad-code-review`.

**State convention =** filesystem-as-SoT (per-task git worktrees), OMEGA as audit log via `[HANDOFF]` blocks, `delegate_task` return as handshake.

**Why Pattern A first, not B or C:**

- Reuses your BMAD skills/personas as-is — they live inside Claude Code where `--bare` is omitted.
- Hermes' subagent system already does process isolation, allowed-toolset gating, concurrency cap.
- No FastAPI service, no MCP transport debugging, no SDK version pinning.
- Move to Pattern B once you genuinely need `can_use_tool` callbacks or `resume=` continuity across delegated jobs.
- Move to Pattern C once you want a swappable, MCP-host-agnostic delegation surface.

### 8.2 4-Day Build Plan

**Day 1 — Wire Hermes to Anthropic.** Install/reconfigure Hermes on ct-crypto-quant: director loop = Nous Portal key (your existing setup); worker calls = `ANTHROPIC_API_KEY` (separate). Smoke test: `delegate_task(goal="run pytest", toolsets=["terminal"])` that just shells out.

**Day 2 — BMAD persona launchers.** Write 4 launcher scripts under `/srv/hermes/launchers/`:

```bash
# /srv/hermes/launchers/worker-dev.sh
#!/usr/bin/env bash
exec claude -p "$1" \
  --permission-mode dontAsk \
  --allowedTools "Read,Edit,Write,Bash(pytest *),Bash(git diff *)" \
  --add-dir "${WORKTREE:-$PWD}" \
  --max-turns 25 --max-budget-usd 1.50 \
  --output-format stream-json --verbose
```

Mirror for `worker-architect.sh`, `worker-qa.sh`, `worker-sm.sh` with persona-specific tool sets and a system-prompt prefix injecting the BMAD role description.

**Day 3 — Hermes pipeline skill.** Write one Hermes auto-skill `bmad_pipeline(story_id)` that:

1. Calls the four launcher scripts in sequence via `delegate_task`.
2. Parses each worker's `stream-json` `result` event for cost + summary.
3. Writes a `[HANDOFF]` block to OMEGA between stages.
4. Bails if any worker returns non-zero.
5. **Wraps the dev step in a 2-iteration evaluator-optimizer** using `/bmad-code-review` — if the reviewer flags blocking issues, re-dispatch dev with the review notes appended; max 2 retries.

**Day 4 — Pilot run.** Pick one **low-risk** crypto-quant story (a doc update or a backtest harness tweak — **not strategy code**). Run end-to-end. Inspect logs. Tighten allowed-tools. Then expand.

**Hard guardrails to land before the first run:**

- Run each worker as `hermes-worker` (UID without read on `live_trading/`, `~/.config/exchange-keys/`).
- `pre-edit` hook on `live_trading/**` exiting non-zero.
- Per-worker `timeout 1800`.
- `max_concurrent_subagents=3`.
- Total budget cap on the pipeline (e.g. `--max-budget-usd 5.00` accumulated across stages).

### 8.3 Migration triggers (when to graduate)

- → **Pattern B** when: you need `can_use_tool` redirects (sandbox file paths), `resume=` across delegated jobs, or want OMEGA / Graphiti as in-process MCP tools.
- → **Pattern C** when: you want the same delegation surface usable by other MCP hosts (Cline, Cursor, Roo, Continue, Goose), or need to expose worker delegation across hosts (e.g., from ct-hermes-hub to a Claude worker on ct-crypto-quant).
- → **Hybrid (B + C)** when: in-process MCP tools (B) plus a public MCP wrapper (C) on top of the FastAPI service.

---

## 9. Comparison Matrix

| Dimension | Pattern A (CLI) | Pattern B (Agent SDK) | Pattern C (MCP) |
|---|---|---|---|
| Setup effort | Lowest (4 shell scripts) | Medium (FastAPI service) | Medium (MCP server + Hermes config) |
| Reuses BMAD skills | Yes (omit `--bare`) | Yes (set `setting_sources`) | Yes (handler shells out to `claude -p`) |
| Per-tool gating | All-or-nothing via `--permission-mode` + `--allowedTools` | **Programmatic `can_use_tool`** | Inherits the wrapper's CLI flags |
| Mid-turn intervention | `--input-format stream-json` only | Yes (interrupt, set_permission_mode) | Limited |
| Multi-turn `resume=` | Yes via `--resume` | Yes via `resume=` option | Yes (handler manages session IDs) |
| Structured event types | NDJSON parsing | Typed Python objects | Tool-call args + result strings |
| In-process MCP | No | **Yes (`create_sdk_mcp_server`)** | Out-of-process by definition |
| Hooks for guardrails | Static (in `.claude/`) | **Programmatic (`hooks={…}`)** | In wrapper handler |
| Operates a second long-lived process | No | Yes (uvicorn) | Yes (MCP server) |
| Dynamic tool discovery in Hermes UI | No | No | **Yes (registered as tools)** |
| Spec/version churn risk | Low | Medium (SDK rename, settings auto-load change) | High (MCP spec moved 4× in 2025) |
| Best for | Starter / week 1 | Programmatic guardrails + multi-turn | Standardised, swappable surface |

---

## 10. Consolidated Sources

All accessed 2026-05-15.

### Anthropic — Claude Code & Agent SDK

- [Run Claude Code programmatically (headless)](https://code.claude.com/docs/en/headless) — canonical headless reference, `--bare`, `-p`, output formats, retry/init event shapes, June 15 2026 Agent SDK credit notice. **HIGH**
- [CLI reference](https://code.claude.com/docs/en/cli-reference) — every flag verbatim including `--session-id`, `--permission-mode`, `--max-budget-usd`, `--permission-prompt-tool`, `setup-token`. **HIGH**
- [Agent SDK overview](https://code.claude.com/docs/en/agent-sdk/overview) and [Python reference](https://code.claude.com/docs/en/agent-sdk/python) — full options, hooks, permissions, sessions, subagents, MCP, June 2026 billing change. **HIGH**
- [Configure permissions](https://platform.claude.com/docs/en/agent-sdk/permissions) — `can_use_tool` semantics. **HIGH**
- [Stream responses in real-time (Agent SDK)](https://code.claude.com/docs/en/agent-sdk/streaming-output) — message flow diagram, `StreamEvent` shape, content_block_delta semantics. **HIGH**
- [API streaming event types](https://platform.claude.com/docs/en/build-with-claude/streaming) — inner schema referenced by stream-json deltas. **HIGH**
- [API rate limits](https://platform.claude.com/docs/en/api/rate-limits). **HIGH**
- [Building agents with the Claude Agent SDK (blog)](https://claude.com/blog/building-agents-with-the-claude-agent-sdk) — rename announcement, agent-loop architecture. **HIGH**
- [`anthropics/claude-agent-sdk-python` README](https://github.com/anthropics/claude-agent-sdk-python) and [CHANGELOG.md](https://github.com/anthropics/claude-agent-sdk-python/blob/main/CHANGELOG.md) — current v0.2.82, breaking changes in v0.1.0. **HIGH**
- [`anthropics/claude-agent-sdk-typescript`](https://github.com/anthropics/claude-agent-sdk-typescript) — TS package v0.3.x, bundles native binary. **HIGH**
- [Inside the Claude Agent SDK: stdin/stdout](https://buildwithaws.substack.com/p/inside-the-claude-agent-sdk-from) — confirms Python SDK spawns the `claude` CLI subprocess. **HIGH**
- [GitHub issue #24596](https://github.com/anthropics/claude-code/issues/24596) — top-level event type enumeration. **MEDIUM**
- [GitHub issue #9026](https://github.com/anthropics/claude-code/issues/9026) — known no-TTY hang bug class. **MEDIUM**
- [Higher usage limits + SpaceX compute deal (May 6 2026)](https://letsdatascience.com/news/anthropic-increases-claude-code-and-api-usage-limits-735fd0ac). **MEDIUM**

### Anthropic — Multi-Agent Research

- [Building Effective Agents (Dec 2024)](https://www.anthropic.com/research/building-effective-agents) — five canonical patterns (chain / route / parallelize / orchestrator-workers / evaluator-optimizer). **HIGH**
- [How we built our multi-agent research system (Jun 2025)](https://www.anthropic.com/engineering/multi-agent-research-system) — lead agent + intelligent-filter subagents; lessons on prompt sensitivity. **HIGH**
- [Simon Willison's annotated notes](https://simonwillison.net/2025/Jun/14/multi-agent-research-system/) — third-party synthesis. **MEDIUM**

### Hermes Agent (Nous Research)

- [Hermes Agent — Home](https://hermes-agent.nousresearch.com). **HIGH**
- [Docs index](https://hermes-agent.nousresearch.com/docs/). **HIGH**
- [AI Providers](https://hermes-agent.nousresearch.com/docs/integrations/providers) — 100+ providers incl. native Anthropic. **HIGH**
- [Subagent Delegation](https://hermes-agent.nousresearch.com/docs/user-guide/features/delegation) — `delegate_task`, isolated context, restricted toolsets, default 3 concurrent. **HIGH**
- [Delegation & Parallel Work patterns](https://hermes-agent.nousresearch.com/docs/guides/delegation-patterns). **HIGH**
- [MCP feature docs](https://hermes-agent.nousresearch.com/docs/user-guide/features/mcp) — confirms stdio + Streamable HTTP client support, OAuth 2.1 PKCE. **HIGH**
- [v0.4.0 release notes (v2026.3.23)](https://github.com/NousResearch/hermes-agent/releases/tag/v2026.3.23) — MCP feature additions. **HIGH**
- [GitHub repo](https://github.com/NousResearch/hermes-agent). **HIGH**
- [DeepWiki on Subagent Delegation](https://deepwiki.com/NousResearch/hermes-agent/5.7-subagent-delegation). **MEDIUM**
- [delegate_tool.py source](https://github.com/NousResearch/hermes-agent/blob/main/tools/delegate_tool.py). **HIGH**
- [Hermes-4 405B on OpenRouter](https://openrouter.ai/nousresearch/hermes-4-405b). **MEDIUM**

### Model Context Protocol

- [Spec (revision 2025-11-25)](https://modelcontextprotocol.io/specification). **HIGH**
- [Transports (2025-03-26 — Streamable HTTP)](https://modelcontextprotocol.io/specification/2025-03-26/basic/transports). **HIGH**
- [Auth0 — Why MCP moved away from SSE to Streamable HTTP](https://auth0.com/blog/mcp-streamable-http/). **MEDIUM**
- [fka.dev — Why MCP deprecated SSE (2025-06-06)](https://blog.fka.dev/blog/2025-06-06-why-mcp-deprecated-sse-and-go-with-streamable-http/). **MEDIUM**

### Multi-Agent Frameworks & Eval

- [Background Claude — stream-json blog](https://backgroundclaude.com/blog/stream-json) — NDJSON, retry visibility, session_id replay. **HIGH**
- [Arize — Orchestrator-Worker Agents framework comparison](https://arize.com/blog/orchestrator-worker-agents-a-practical-comparison-of-common-agent-frameworks/). **MEDIUM**
- [Agent-as-a-Judge survey (arXiv 2508.02994)](https://arxiv.org/html/2508.02994v1) — judge mis-calibration. **HIGH**
- [Evidently — LLM-as-a-judge complete guide](https://www.evidentlyai.com/llm-guide/llm-as-a-judge). **MEDIUM**
- [Hermes-4 local-agent overview (PopularAITools)](https://popularaitools.ai/blog/hermes-4-local-agent-model-2026). **LOW**

---

**Scope Confirmed:** 2026-05-15
**Document Completed:** 2026-05-15
**Methodology:** 4 parallel research subagents (Pattern A / Pattern B / Pattern C / cross-cutting orchestration) + director synthesis. All major claims cite live URLs accessed 2026-05-15 with HIGH/MEDIUM/LOW confidence labels.
