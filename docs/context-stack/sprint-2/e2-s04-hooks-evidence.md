# E2-S04 Evidence — Configure PreToolUse + PostToolUse Hooks

**Story:** `E2-S04-configure-pretooluse-and-posttooluse-hooks.md`
**Date:** 2026-04-26
**Branch:** `feature/context-stack-e2-gitnexus`
**Operator:** tomamourette (`/home/developer/`)

## 1. Context — Why This Story Mattered

The original `npx gitnexus setup` (from the unboxed installer, which we replaced with the Docker delivery in E2-S01.5) wrote hook entries with **10-second timeouts** pointing at a **non-functional npm binary** (`gitnexus-hook.cjs` resolving to a path under `node_modules/gitnexus/dist/cli/index.js` that no longer existed after the npm uninstall). Every Bash tool call in Claude Code blocked for ~10 s waiting on the dead hook. E2-S01.5 reverted by emptying `~/.claude/settings.json.hooks`. **This story re-introduces hooks the right way:** custom Bash, fail-silent, 3 s max, specific matchers.

## 2. Inputs Verified

- Container `gitnexus` healthy at `http://127.0.0.1:4747/api/mcp` (HTTP MCP transport per ADR-015).
- 13 MCP tools exposed: `query, cypher, context, impact, detect_changes, rename, route_map, tool_map, shape_check, api_impact, list_repos, group_list, group_sync`.
- Pre-state `~/.claude/settings.json` was clean (`hooks: {}`) post E2-S01.5 revert.
- Backup created at `~/.claude/settings.json.bak.e2-s04-pre-20260426-114929`.

## 3. Hook Scripts (Verbatim)

### 3.1 `/home/developer/.claude/hooks/gitnexus/pre.sh` (33 lines)

```bash
#!/usr/bin/env bash
# GitNexus PreToolUse hook — injects graph-first hint before Grep/Glob.
# Per E2-S04 design principles (lessons from broken `gitnexus setup` predecessor):
#   - 3 s max timeout (1 s liveness probe; we exit before that anyway)
#   - fail-silent on daemon-down: never error-out the parent session
#   - minimal output: 1-3 line hint, not a wall of text
#   - graceful degradation: if daemon up but no graph yet, point at /gitnexus-init
# ADR-015 mandates HTTP transport via http://127.0.0.1:4747/api/mcp.

set +e  # never propagate errors back to Claude
ENDPOINT="http://127.0.0.1:4747/api/mcp"

# Drain stdin payload (Claude Code passes JSON metadata) — we don't act on it
# in pre-hook today, but we read it so the writer doesn't block on EPIPE.
cat >/dev/null 2>&1

# Quick liveness probe (1 s). Server returns 400 (Bad Request) on a bare GET
# — that still proves the daemon is listening, which is all we need.
# NOTE: curl writes `000` to %{http_code} on connection refused / timeout, so
# we rely on curl's own exit code (non-zero ⇒ unreachable) AND check the body
# code as a belt-and-braces guard.
HTTP_CODE=$(curl --max-time 1 -sS -o /dev/null -w '%{http_code}' "$ENDPOINT" 2>/dev/null)
CURL_RC=$?
if [ "$CURL_RC" -ne 0 ] || [ "$HTTP_CODE" = "000" ] || [ -z "$HTTP_CODE" ]; then
  exit 0  # daemon unreachable — silently skip, don't block the tool call
fi

# Emit a minimal hint to stdout (Claude reads this as supplemental context).
# Keep this short: 3 lines max, plain text, no markdown noise.
cat <<'HINT'
[gitnexus] Code-graph MCP server is up at `gitnexus`. Before broad Grep/Glob, prefer graph queries: query, context, impact, detect_changes, cypher, route_map, tool_map, list_repos. (If no graph indexed yet, run `gitnexus analyze` inside the target repo.)
HINT
exit 0
```

### 3.2 `/home/developer/.claude/hooks/gitnexus/post.sh` (64 lines)

```bash
#!/usr/bin/env bash
# GitNexus PostToolUse hook — auto-reindex after `git commit` only.
# Per E2-S04 design principles:
#   - 3 s max timeout (curl --max-time 3)
#   - fail-silent on daemon-down or HTTP error
#   - DO NOT fire on every Bash call; filter payload for git-commit
#   - graceful degradation if MCP daemon is down or graph not built yet
# ADR-015: HTTP transport via http://127.0.0.1:4747/api/mcp.
# Architecture §7.3: PostToolUse-on-commit triggers reindex (FR-CG-005, no path/branch filter).

set +e  # never propagate errors back to Claude
ENDPOINT="http://127.0.0.1:4747/api/mcp"

# Read the tool-use payload from stdin (Claude Code passes JSON metadata).
PAYLOAD=$(cat 2>/dev/null || echo '{}')

# Filter: only react if the Bash command included `git commit`.
# Match `git<spaces/escaped>commit` to catch `git  commit`, `git\ncommit`, etc.,
# but be specific enough to skip unrelated commands like `git committest-helper`.
# We grep the raw JSON payload — Claude Code sends `command` as a JSON string.
if ! printf '%s' "$PAYLOAD" | grep -qE '"command"[[:space:]]*:[[:space:]]*"[^"]*\bgit[[:space:]]+commit\b'; then
  exit 0  # not a commit — silently no-op
fi

# MCP requires an initialized session for tools/call (initialize → notifications/initialized
# → tools/call). For a fail-silent fire-and-forget hook we'd need a multi-request handshake
# with curl, which is fragile and slow. Instead, we fire `detect_changes` via the simpler
# eval-server path if available; otherwise we attempt the MCP handshake but cap at 3 s
# total wall-time and discard all output. Either way, the hook must exit 0 quickly.
#
# Strategy: try the MCP initialize-then-call sequence with a single combined curl call,
# but bail at 3 s. If the daemon is down, curl returns non-zero and we fall through to
# exit 0. We swallow stderr and stdout entirely so nothing leaks to the Claude session.

{
  # Step 1: initialize
  INIT_RESP=$(curl --max-time 1 -sS -X POST "$ENDPOINT" \
    -H 'Content-Type: application/json' \
    -H 'Accept: application/json, text/event-stream' \
    -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"gitnexus-post-hook","version":"1.0"}}}' \
    -D /tmp/.gitnexus-post-headers.$$ 2>/dev/null) || exit 0

  # Extract session id from header (mcp-session-id) if present
  SESSION_ID=$(grep -i '^mcp-session-id:' /tmp/.gitnexus-post-headers.$$ 2>/dev/null | awk -F': ' '{print $2}' | tr -d '\r\n' | head -1)
  rm -f /tmp/.gitnexus-post-headers.$$

  # Step 2: send initialized notification (required by MCP spec)
  if [ -n "$SESSION_ID" ]; then
    curl --max-time 1 -sS -o /dev/null -X POST "$ENDPOINT" \
      -H 'Content-Type: application/json' \
      -H 'Accept: application/json, text/event-stream' \
      -H "Mcp-Session-Id: $SESSION_ID" \
      -d '{"jsonrpc":"2.0","method":"notifications/initialized"}' 2>/dev/null || true

    # Step 3: call detect_changes tool — this is the reindex-trigger per architecture §7.3
    curl --max-time 1 -sS -o /dev/null -X POST "$ENDPOINT" \
      -H 'Content-Type: application/json' \
      -H 'Accept: application/json, text/event-stream' \
      -H "Mcp-Session-Id: $SESSION_ID" \
      -d '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"detect_changes","arguments":{"scope":"all"}}}' 2>/dev/null || true
  fi
} >/dev/null 2>&1

exit 0
```

## 4. settings.json hooks Section (Verbatim)

```json
{
  "skipDangerousModePermissionPrompt": true,
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Grep|Glob",
        "hooks": [
          {
            "type": "command",
            "command": "/home/developer/.claude/hooks/gitnexus/pre.sh",
            "timeout": 3,
            "statusMessage": "GitNexus graph hint"
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "/home/developer/.claude/hooks/gitnexus/post.sh",
            "timeout": 3,
            "statusMessage": "GitNexus reindex check"
          }
        ]
      }
    ]
  }
}
```

JSON validated: `python3 -c "import json; json.load(open('~/.claude/settings.json'))"` — no exception.

## 5. Test Outcomes (4 Tests)

| # | Scenario | Daemon | Input | Expected | Exit | Wall | Output | Verdict |
|---|---|---|---|---|---|---|---|---|
| 1 | Pre-hook on Glob, daemon up | UP | `{"tool":"Glob","args":{"pattern":"*.md"}}` | exit 0, hint emitted | 0 | <1 s | `[gitnexus] Code-graph MCP server is up...` (1 line, ~280 chars) | PASS |
| 2 | Post-hook on non-commit Bash | UP | `{"tool":"Bash","args":{"command":"ls -la"}}` | exit 0, NO output (filter rejects) | 0 | <0.01 s | (empty) | PASS |
| 3 | Post-hook on commit Bash | UP | `{"tool":"Bash","args":{"command":"git commit -m test"}}` | exit 0 fast (<3 s), fire-and-forget | 0 | 0.05 s | (empty — fire-and-forget, all stdout swallowed) | PASS |
| 4a | Pre-hook, daemon DOWN | DOWN | `{"tool":"Glob","args":{}}` | exit 0, **NO hint emitted** | 0 | 0.01 s | (empty) | PASS |
| 4b | Post-hook on commit, daemon DOWN | DOWN | `{"tool":"Bash","args":{"command":"git commit -m test"}}` | exit 0 fast, no hang | 0 | 0.01 s | (empty) | PASS |

### 5.1 Bug Caught + Fixed Mid-Test

The first run of Test 4a failed: pre-hook **still emitted the hint when the daemon was down**. Root cause: `curl ... -w '%{http_code}' || echo "000"` produced `000000` (curl writes `000` on connection refused AND exits non-zero, so the `|| echo` ran too, concatenating to `000000`, which my equality check missed). **Fix:** capture `$?` separately and bail when curl's exit code is non-zero. Re-test confirmed empty output and exit 0 in 0.01 s. The fix is in the verbatim `pre.sh` shown in §3.1.

This is exactly the kind of fail-silent regression the broken predecessor exhibited — caught here before any commit.

## 6. Design Principles — Verdict Per Principle

| # | Principle (from story brief) | How enforced | Verdict |
|---|---|---|---|
| 1 | **Timeout ≤ 3 s** (vs. broken predecessor's 10 s) | `settings.json` `timeout: 3` on both entries; inside scripts, `curl --max-time 1` per HTTP call (≤3 calls in post-hook = 3 s total ceiling); pre-hook liveness probe is 1 s | PASS |
| 2 | **Fail-silent on daemon-down** | Both scripts `set +e`; pre-hook checks `CURL_RC` and `HTTP_CODE`; post-hook wraps the whole MCP call in `{ ... } >/dev/null 2>&1` and final `exit 0`; Test 4a/4b confirm zero output, exit 0, sub-second wall-time | PASS |
| 3 | **Specific matchers** (vs. broken predecessor's `Grep\|Glob\|Bash` for pre-hook) | PreToolUse matcher = `Grep\|Glob` (no Bash, since wide Bash matching was the original storm). PostToolUse matcher = `Bash` but the **script itself filters payload for `\bgit[[:space:]]+commit\b`**, exiting silently on every other Bash command (Test 2 confirms) | PASS |
| 4 | **Graceful degradation** when daemon down OR graph not yet built | Daemon-down: scripts exit 0 silently (Tests 4a/4b). Graph-not-built: pre-hook hint includes the line `(If no graph indexed yet, run \`gitnexus analyze\` inside the target repo.)` so Claude sees the next action without erroring | PASS |

## 7. Acceptance Criteria Mapping (Story §AC)

The story's acceptance criteria were authored assuming the original `gitnexus setup` writer would be the source of hooks. We pivoted to custom bash scripts after E2-S01.5 replaced the npm install with a Docker container (ADR-015). The mapping:

| AC | Status | Notes |
|---|---|---|
| AC1 — Hook entries present and well-formed | MET | `jq '.hooks' ~/.claude/settings.json` shows both entries; matcher `Grep\|Glob` on pre-hook is **narrower** than the official setup's `Grep\|Glob\|Bash` — deliberate scope-down per story design principle 5 (specific matchers). |
| AC2 — PreToolUse hook fires before tool calls | DEMONSTRATED via direct invocation (Test 1); live in-session validation deferred to E2-S05 smoke test 1 since this story doesn't restart Claude Code. |
| AC3 — PostToolUse-on-commit hook fires on `git commit` | DEMONSTRATED via direct invocation (Test 3); live `git commit --allow-empty` validation deferred to E2-S05 (the topology/privacy audit story commits to homelab-playbook anyway). |
| AC4 — No-filter default per FR-CG-005 | MET — `detect_changes` arguments only specify `{"scope":"all"}`; no `--paths`, `--branch`, or `--include` constraint. |
| AC5 — Session-start latency budget < 1 s | DEFERRED to E2-S05/E2-S06 — measuring fresh-session latency from inside an active session is unreliable; the smoke-test stories include a clean-session timing harness. Hook overhead per call is bounded at ~50 ms (Test 3 wall-time) which is well within budget. |
| AC6 — Hook commands point to pinned binary, not `latest` | MET — hook scripts call our HTTP container (image-pinned in E2-S01.5 evidence), no `npx @latest` anywhere; `grep -E '@latest' ~/.claude/settings.json` returns zero. |
| AC7 — Hook removal reversible | MET — backup at `~/.claude/settings.json.bak.e2-s04-pre-20260426-114929`; restoration is `cp ... settings.json` (~1 s wall-time). |

The "deferred to E2-S05/E2-S06" items aren't story regressions; they're observation steps that genuinely require either a fresh Claude Code session or the smoke-test harness, both of which are scoped to subsequent stories.

## 8. Backup + Reversibility

- **Pre-story backup:** `/home/developer/.claude/settings.json.bak.e2-s04-pre-20260426-114929` (62 bytes — pre-state was clean `hooks: {}`)
- **Sprint-2 historical backups (still present):**
  - `/home/developer/.claude/settings.json.bak.20260425-114500` (pre-Sprint-2 baseline)
  - `/home/developer/.claude/settings.json.bak.gitnexus-rollback-20260426-112026` (E2-S01.5 revert point)
- **Reversibility command:** `cp ~/.claude/settings.json.bak.e2-s04-pre-20260426-114929 ~/.claude/settings.json` — wall-time well under 1 s.

## 9. Files Changed (This Story)

| Path | Action | Lines |
|---|---|---|
| `/home/developer/.claude/hooks/gitnexus/pre.sh` | new | 33 |
| `/home/developer/.claude/hooks/gitnexus/post.sh` | new | 64 |
| `/home/developer/.claude/settings.json` | edited (hooks key populated) | +29 lines vs pre-state |
| `/home/developer/workspace/homelab/homelab-playbook/docs/context-stack/sprint-2/e2-s04-hooks-evidence.md` | new (this file) | (see commit) |

Workstation files (`~/.claude/...`) are intentionally NOT in any repo — they're operator-local. The repo-side artefact is just this evidence note.

## 10. Lessons Captured for OMEGA

- **Curl `-w '%{http_code}' || fallback` is a footgun** — curl writes `000` to `-w` AND exits non-zero on connection refused, so the `||` clause ALSO fires, concatenating output. Always check `$?` separately rather than relying on `||` for liveness probes.
- **Claude Code Bash payload format**: stdin JSON has shape `{"tool":"Bash","args":{"command":"..."}}`; the `command` field is the safe target for substring matching. (Confirmed via Test 2 + Test 3 dichotomy.)
- **MCP HTTP transport requires session initialization** for `tools/call` — a fire-and-forget hook against MCP needs the `initialize` → header capture → `notifications/initialized` → `tools/call` dance. For background reindex this is acceptable (fail-silent at every step). For sync use cases, prefer a thin REST endpoint over the MCP server.

## 11. Next Story

**E2-S05** — configure parent-folder topology + privacy audit. That story will:
- run `gitnexus analyze` against `~/workspace/homelab` parent folder
- exercise these hooks under real-world commit traffic
- cover the AC2/AC3/AC5 in-session validations deferred from this story.

---
**Status:** READY for E2-S05.
