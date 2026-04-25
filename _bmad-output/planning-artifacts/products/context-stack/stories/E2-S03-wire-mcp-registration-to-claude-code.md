---
type: story
epic: E2
id: E2-S03
title: "Wire GitNexus MCP server registration into Claude Code via npx gitnexus setup"
size: 0.5d
priority: MUST
fr_refs: [FR-CG-001]
nfr_refs: [NFR-AVAIL-001]
adr_refs: [ADR-004, ADR-005]
status: draft
date: 2026-04-25
---

# E2-S03: Wire GitNexus MCP server registration into Claude Code via npx gitnexus setup

## User Story

As **tomamourette**, I want **GitNexus registered as a stdio MCP server in Claude Code's config so its tool surface (`cypher`, `impact`, `context`, `reindex`) is discovered by the model**, so that **I close the OMEGA "tools not surfaced" failure mode (per ADR-005), and downstream stories can validate parent-folder indexing (E2-S05), hook firing (E2-S04), and smoke tests (E2-S06) against a model that actually sees the tools**.

## Background and Context

ADR-005 (MCP-first) is the architectural through-line: MCP-native tools are reliably called by Claude Code's model because the model is trained on standard manifest discovery. GitNexus ships with `npx gitnexus setup`, which is documented to write the MCP entry to `~/.claude/settings.json` (and PreToolUse + PostToolUse hooks — but those are validated separately in E2-S04 to keep this story tight). This story registers MCP only and verifies the model sees the tool surface; hook validation lives in E2-S04. Architecture §7.1 lists the expected GitNexus tool inventory; architecture §3 (Container Diagram) shows the MCP stdio transport.

## Acceptance Criteria

**AC1 — Pre-registration baseline captured.**
- **Given** the workstation post-E1 (clean baseline) + post-E2-S02 (footprint OK),
- **When** the operator runs `cp ~/.claude/settings.json ~/.claude/settings.json.pre-gitnexus.bak` AND `claude mcp list`,
- **Then** the backup file exists AND the `claude mcp list` output is captured (it should NOT contain `gitnexus`); both saved as evidence in `homelab-playbook/docs/decisions/gitnexus-mcp-registration-evidence.md`.

**AC2 — `npx gitnexus setup` runs cleanly and registers MCP.**
- **Given** AC1 has passed,
- **When** the operator runs `npx gitnexus setup` and answers any prompts (Claude Code only — decline Cursor / Codex if offered),
- **Then** the command exits 0 AND `~/.claude/settings.json` now contains a `mcpServers.gitnexus` entry with `transport: "stdio"` (or its equivalent JSON shape per current MCP spec) AND no other entries were modified (verified by diffing against the AC1 backup, scoped to non-`gitnexus` keys).

**AC3 — Claude Code discovers the server as healthy.**
- **Given** AC2 has passed AND a fresh `claude` invocation has run (in case the daemon caches config),
- **When** the operator runs `claude mcp list`,
- **Then** the output includes a line for `gitnexus` AND the status is `healthy` (or the equivalent ✓ / running marker per the current Claude Code CLI).

**AC4 — Tool surface advertised to the model (architecture §7.1).**
- **Given** AC3 has passed,
- **When** the operator starts a Claude Code session and prompts `list the MCP tools you have access to from gitnexus` (a deterministic introspection ask),
- **Then** the response enumerates at minimum `cypher`, `impact`, `context`, and `reindex` (the four documented in architecture §7.1; additional upstream tools are acceptable).

**AC5 — Stdio transport verified (no listening port).**
- **Given** AC3 has passed,
- **When** the operator runs `ss -tlnp | grep -i gitnexus` AND `lsof -p <gitnexus-pid> | grep -E 'TCP|LISTEN'`,
- **Then** there is **no** listening TCP socket attributable to gitnexus (consistent with stdio transport per architecture §3 "MCP transports: GitNexus = stdio (in-process, no network)"). Evidence appended to the registration evidence note.

**AC6 — Graceful-degradation pre-flight (NFR-AVAIL-001 baseline).**
- **Given** AC4 has passed,
- **When** the operator stops the gitnexus daemon (`pkill -f gitnexus` or equivalent), starts a Claude Code session, and asks a non-code question,
- **Then** the session completes successfully AND no tool-call from the session hangs > 3 s waiting for gitnexus AND `claude mcp list` reports gitnexus as unhealthy (expected). This is the smallest-possible degradation drill that confirms registration is reversible; the comprehensive drill is in E2-S06 scenario 6. The daemon is restarted after the test.

**AC7 — Registration captured in install script (continuation of FR-DEP-003).**
- **Given** E2-S01 created `homelab-playbook/scripts/install-gitnexus-workstation.sh`,
- **When** the operator appends an idempotent invocation of `npx gitnexus setup --noninteractive` (or, if non-interactive flag is unavailable, a guarded block that skips when `claude mcp list | grep -q '^gitnexus'`) to that script,
- **Then** the updated script remains idempotent AND a fresh-rebuild walkthrough on a scratch VM (or `mktemp -d` fake `$HOME` simulation) successfully reaches "MCP registered" with no manual prompts.

## Implementation Notes

**Reference architecture sections:** §3 Container Diagram (`MCP stdio: GitNexus`), §4.1 Code-graph layer (install + registration), §7.1 MCP servers — tool inventory (the `cypher`, `impact`, `context`, `reindex` set), §7.3 Hooks (note: hooks are added by `setup` too — but their validation is E2-S04, not here).

**Reference ADRs:** ADR-004 (the adoption decision), ADR-005 (the MCP-first stance — confirms the registration is structural, not optional).

**Concrete commands:**

```bash
# AC1 — baseline
cp ~/.claude/settings.json ~/.claude/settings.json.pre-gitnexus.bak
claude mcp list | tee ~/workspace/homelab/_export/claude-mcp-list-pre.txt

# AC2 — register
npx gitnexus setup
diff ~/.claude/settings.json.pre-gitnexus.bak ~/.claude/settings.json   # inspect

# AC3 — discovery
claude mcp list
claude mcp list | grep -E '^gitnexus.*healthy'

# AC4 — model-side discovery (run in a Claude Code session)
# prompt: "list the MCP tools you have access to from gitnexus"

# AC5 — stdio confirmation
GITNEXUS_PID=$(pgrep -f gitnexus | head -1)
ss -tlnp | grep -i gitnexus    # expect empty
lsof -p $GITNEXUS_PID 2>/dev/null | grep -E 'TCP|LISTEN' || echo "no listening sockets (stdio confirmed)"

# AC6 — degradation drill
pkill -f gitnexus
# start a Claude Code session, ask "what is 2+2"; expect normal completion, no hang
claude mcp list   # expect gitnexus unhealthy
# restart: claude reconnects on next session, OR run `npx gitnexus daemon` if needed

# AC7 — script append (idempotent guard)
# append to install-gitnexus-workstation.sh:
# if claude mcp list 2>/dev/null | grep -q '^gitnexus'; then echo "MCP already registered"; else npx gitnexus setup; fi
```

**Evidence note path:** `homelab-playbook/docs/decisions/gitnexus-mcp-registration-evidence.md`. Captures: pre-state `claude mcp list`, post-state, settings.json diff (scoped to gitnexus + hook keys), tool-surface introspection answer, stdio confirmation, degradation drill outcome.

**Hook scope:** `npx gitnexus setup` will likely write PreToolUse + PostToolUse hook entries too (per architecture §7.3). Verifying those entries fire correctly is **E2-S04**'s job; this story's scope is MCP-server registration only. If `setup` writes hooks, document their presence in the evidence file but do NOT exercise them here.

## Test Plan

**Pre-state:**
- E2-S01 + E2-S02 done.
- `claude mcp list` does NOT show `gitnexus`.
- `~/.claude/settings.json` is post-E1 clean.

**Action sequence:**
1. Backup settings.json + capture `claude mcp list` (AC1).
2. Run `npx gitnexus setup` (AC2).
3. Diff settings.json against backup; confirm only `gitnexus`-namespaced keys changed (AC2).
4. Re-run `claude mcp list`; confirm `gitnexus` appears healthy (AC3).
5. Open a Claude Code session; introspect tool surface (AC4).
6. `ss -tlnp | grep gitnexus` confirms no listening port (AC5).
7. Stop daemon; start Claude session; confirm graceful degradation (AC6).
8. Restart daemon; append idempotent invocation to install script (AC7); re-run script.
9. Update evidence note.

**Post-state checks:**
- `claude mcp list` shows `gitnexus healthy`.
- Tool-surface introspection lists ≥ 4 expected tools.
- No new TCP listening sockets attributable to gitnexus.
- Install script is idempotent.

**Rollback:**
- `claude mcp remove gitnexus` (or restore from `settings.json.pre-gitnexus.bak`) reverts the registration.
- Combined with E2-S01 rollback (`npm uninstall -g gitnexus`), workstation returns to post-E1 state.
- Rollback wall-time: < 5 minutes.

## Dependencies

- **Blocked by:** E2-S01 (binary present), E2-S02 (footprint not blocking).
- **Blocks:** E2-S04 (hooks need MCP registered — though `setup` may write both at once, hook *behaviour* validation depends on this story's success), E2-S05 (topology requires daemon running + MCP visible), E2-S06 (smoke tests use the tool surface).

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| `npx gitnexus setup` requires interactive prompts and stalls in CI / non-tty contexts. | Med | Low — manual run works, but install-script idempotency suffers. | AC7 has fallback guard (`if claude mcp list ... grep`); document the prompt sequence in evidence note for the next operator. |
| Setup writes hook entries this story doesn't exercise, and they fire on the very next Claude Code action. | Med | Med — could cause unexpected behaviour mid-story. | Keep evidence note open; if hooks fire, document and continue (E2-S04 will validate). If hooks misbehave, disable in settings.json and continue; flag for E2-S04. |
| `claude mcp list` output format changes between Claude Code releases, breaking the grep in AC7. | Low | Low — guard is loose. | Use `--json` output if available (`claude mcp list --json | jq -e '.servers[] | select(.name=="gitnexus")'`). |
| Setup writes to a non-default Claude config path (e.g., per-project `.claude/settings.json` instead of `~/.claude/`). | Low | Med — registration not picked up. | Run setup from `$HOME` (not from inside a repo); confirm via diff in AC2. |

## Definition of Done

- [ ] AC1–AC7 all green and evidenced.
- [ ] `homelab-playbook/docs/decisions/gitnexus-mcp-registration-evidence.md` committed.
- [ ] `claude mcp list` shows `gitnexus healthy`.
- [ ] `homelab-playbook/scripts/install-gitnexus-workstation.sh` extended with idempotent setup invocation.
- [ ] No regression in any non-GitNexus MCP server (Graphiti not yet present in E2; baseline tools unchanged).
- [ ] Story status updated to `done`; OMEGA `omega_store(...)` records the registration outcome.
