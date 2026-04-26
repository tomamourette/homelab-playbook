# E2-S02 Footprint Evidence

**Date:** 2026-04-26
**Story:** E2-S02 Verify GitNexus footprint < 500MB RSS
**Closes:** architecture AR1 (attempted; outcome below)
**Branch:** feature/context-stack-e2-gitnexus
**Operator:** tomamourette
**Workstation:** ai-dev container (Debian 12 bookworm, Node v20.20.0)

## Summary verdict

**AR1 cannot be closed by this story. Daemon will not start on the workstation OS baseline.**

The GitNexus daemon (`gitnexus mcp`) and indexer (`gitnexus analyze`) both fail at the
LadybugDB native-binding load step due to a missing libstdc++ symbol version. RSS
sampling is not possible because no daemon process exists to sample. This is a
different failure mode from the one AR1 anticipated (RSS overshoot); the architecture
risk is **not closed and is now joined by a new finding** about runtime prerequisites
that ADR-004 did not call out.

Recommendation: STOP and escalate before E2-S03.

## Daemon startup model discovered

```
$ gitnexus --help
Usage: gitnexus [options] [command]

GitNexus local CLI and MCP server

Commands:
  setup       One-time setup: configure MCP for Cursor, Claude Code, OpenCode, Codex
  analyze     Index a repository (full analysis)
  mcp         Start MCP server (stdio) — serves all indexed repos
  serve       Start local HTTP server for web UI connection
  ...

$ gitnexus mcp --help
Usage: gitnexus mcp [options]
Start MCP server (stdio) — serves all indexed repos
```

Story-spec note: the story Background references `npx gitnexus daemon`, but the
v1.6.3 CLI does not have a `daemon` subcommand — the stdio MCP server is started via
`gitnexus mcp`. Update the story Background or AC1 in a follow-up to use `mcp`.

## Setup performed (UNEXPECTED SIDE-EFFECTS — see below)

```
$ gitnexus setup
  Configured:
    + Claude Code
    + Claude Code skills (7 skills → ~/.claude/skills/)
    + Claude Code hooks (PreToolUse, PostToolUse)
  Skipped:
    - Cursor (not installed)
    - OpenCode (not installed)
    - Codex (not installed)
exit=0
```

**Unexpected side effects of `gitnexus setup`** — the story planned only a footprint
measurement, but `setup` is *not* a no-op. It performed the work intended for E2-S03
and parts of E2-S04 in one shot:

1. Installed 7 skill directories under `~/.claude/skills/gitnexus-*`:
   `gitnexus-cli`, `gitnexus-debugging`, `gitnexus-exploring`, `gitnexus-guide`,
   `gitnexus-impact-analysis`, `gitnexus-pr-review`, `gitnexus-refactoring`.
2. Installed `~/.claude/hooks/gitnexus/gitnexus-hook.cjs` plus
   `pre-tool-use.sh` and `session-start.sh`.
3. Modified `~/.claude/settings.json` to add PreToolUse and PostToolUse hook
   entries that invoke `gitnexus-hook.cjs` with a 10s timeout (statusMessage:
   "Enriching with GitNexus graph context..." and "Checking GitNexus index
   freshness...").

These artifacts have been **left in place** so the operator can decide whether to
revert them as part of the AR1 escalation, or roll them forward into E2-S03/S04 once
the runtime blocker is resolved. Note that with the daemon non-functional on this
host, the hooks will hit the 10s timeout on every PreToolUse/PostToolUse call, which
will be visible as latency in Claude Code until the daemon is running OR the hooks
are removed.

## Daemon startup attempt (FAILED — daemon never came up)

Both `gitnexus analyze .` (to index the scratch repo before measuring) and
`gitnexus mcp` (to start the stdio MCP server for measurement) terminate immediately
with the same error:

```
Error: /lib/x86_64-linux-gnu/libstdc++.so.6: version `GLIBCXX_3.4.32' not found
(required by /home/developer/.npm-global/lib/node_modules/gitnexus/node_modules/@ladybugdb/core/lbugjs.node)
    at Object.<anonymous> (.../@ladybugdb/core/lbug_native.js:16:11)
    at Module._compile (node:internal/modules/cjs/loader:1521:14)
    ...
  code: 'ERR_DLOPEN_FAILED'
```

`ldd` confirms two missing symbol versions on this binding:

```
$ ldd /home/developer/.npm-global/lib/node_modules/gitnexus/node_modules/@ladybugdb/core/lbugjs.node
.../lbugjs.node: /lib/x86_64-linux-gnu/libstdc++.so.6: version `GLIBCXX_3.4.32' not found
.../lbugjs.node: /lib/x86_64-linux-gnu/libstdc++.so.6: version `GLIBCXX_3.4.31' not found
```

System libstdc++ symbol coverage:

```
$ apt-cache policy libstdc++6
libstdc++6:
  Installed: 12.2.0-14+deb12u1
  Candidate: 12.2.0-14+deb12u1
  500 http://deb.debian.org/debian bookworm/main amd64 Packages

$ strings /lib/x86_64-linux-gnu/libstdc++.so.6 | grep '^GLIBCXX' | sort -V | tail -3
GLIBCXX_3.4.29
GLIBCXX_3.4.30
GLIBCXX_DEBUG_MESSAGE_LENGTH
```

System max is `GLIBCXX_3.4.30` (gcc-12 series). Required is `GLIBCXX_3.4.32`
(gcc-13+ series, ships with Debian Trixie/Sid). Bookworm-main has no path to a
newer libstdc++ without enabling backports/sid or shipping a vendored runtime.

There is no vendored libstdc++ inside the npm package (checked
`gitnexus/vendor/` and `node_modules/`); the binding hard-depends on the host's
`/lib/x86_64-linux-gnu/libstdc++.so.6`.

## Daemon process

- Command line attempted: `gitnexus mcp` (and previously `gitnexus analyze .`)
- PID: **none — process exits before backgrounding** (Node throws on
  module import inside `lbug_native.js`)
- Process tree: N/A

## RSS samples

**No samples collected — daemon would not start.** Sampling table is empty by
necessity; the 12-sample × 5s window described in the story cannot be executed
until the runtime blocker is resolved.

| Sample | Time | RSS (KB) | RSS (MB) |
|--------|------|----------|----------|
| —      | —    | —        | daemon never started |

## Statistics

- PEAK: N/A (daemon never running)
- MEAN: N/A
- P95:  N/A

## NFR-FOOTPRINT verdict

**Threshold: < 500 MB RSS**
**PEAK measured: not measurable**
**Verdict: BLOCKED — runtime prerequisite unmet (libstdc++ GLIBCXX_3.4.32 missing on Debian 12)**

## AR1 closure

**AR1: NOT CLOSED.**

Original AR1 wording: "verify GitNexus daemon footprint < 500MB RSS". This story
expected the risk to be either *closed* (PASS, RSS under threshold) or *blocked*
(FAIL, RSS over threshold). A third failure mode has surfaced that the architecture
did not anticipate: the LadybugDB native binding shipped in `gitnexus@1.6.3` is not
compatible with Debian 12's libstdc++ baseline, so the footprint cannot be measured
on the current ai-dev workstation at all.

This is a stronger blocker than an RSS overshoot would be — it means GitNexus is
not runnable on the current OS without either (a) upgrading the workstation to a
newer libstdc++ (Debian Trixie/Sid, or backports if available), (b) running
GitNexus in a container with a newer libstdc++ runtime, (c) requesting a build of
LadybugDB linked against an older libstdc++, or (d) invoking ADR-004's reversal
trigger (CodeGraphContext exit ramp).

Escalation note for architecture review:

> **AR1 status update — 2026-04-26:** Footprint not measured. New blocker:
> `@ladybugdb/core` v1.6.3 native binding requires `GLIBCXX_3.4.32`, system
> provides `GLIBCXX_3.4.30`. ADR-004 did not call out a libstdc++ baseline.
> Decide between (1) workstation libstdc++ upgrade, (2) containerised GitNexus,
> (3) request older LadybugDB build from upstream, (4) ADR-004 reversal to
> CodeGraphContext. Halt E2-S03 until decided.

## Cleanup

- Daemon stopped: yes (it never started; no orphan process present)
- Scratch dir removed: yes — `/tmp/gitnexus-footprint-test` deleted
- `gitnexus setup` artifacts: **left in place** (skills + hooks + settings.json
  edits) for operator review; revert is straightforward (`rm -rf
  ~/.claude/skills/gitnexus-* ~/.claude/hooks/gitnexus`, plus removing the
  `gitnexus-hook.cjs` PreToolUse/PostToolUse entries from
  `~/.claude/settings.json`) once the operator decides direction. Recommend
  reverting the hook entries promptly to avoid 10s timeout latency on every tool
  call while the daemon is non-functional.

## Story status

- AC1 (daemon starts, identifiable in `ps`): **FAIL**
- AC2..AC6: **N/A — gated on AC1**
- DoD: **NOT MET**
- Recommended next action: **STOP** — do not start E2-S03 (MCP wiring) until
  AR1 escalation has chosen a path forward.
