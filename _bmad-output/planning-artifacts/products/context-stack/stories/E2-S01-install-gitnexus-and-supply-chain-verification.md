---
type: story
epic: E2
id: E2-S01
title: "Install GitNexus v1.6.3 via npm with supply-chain verification and capture install in workstation role"
size: 1d
priority: MUST
fr_refs: [FR-CG-001, FR-DEP-003]
nfr_refs: [NFR-SUPP-001]
adr_refs: [ADR-004, ADR-005]
status: draft
date: 2026-04-25
---

# E2-S01: Install GitNexus v1.6.3 via npm with supply-chain verification and capture install in workstation role

## User Story

As **tomamourette**, I want **GitNexus v1.6.3 installed on my workstation through a verified, repeatable, supply-chain-checked procedure captured in version control**, so that **the code-graph tier exists, is reproducible across rebuilds, and the abandonment / typosquat risks called out in brief §10.1 R1 and architecture §5.3 are mitigated before any further GitNexus work begins**.

## Background and Context

This is the first story of Epic E2 (GitNexus Pilot, Sprint 2). E1 (Decommission) merged with tag `phase-1-decommission-complete`; the workstation has a clean `~/.claude/settings.json` baseline with no OMEGA hook entries. GitNexus is a young, single-maintainer npm-distributed Node.js MCP server (LadybugDB-backed, tree-sitter parsing) per ADR-004. Architecture §11 AR4 and brief §10.1 R1 require an explicit upstream-activity check at adoption (NFR-SUPP-001: ≥ 3 months commit activity). Architecture §5.3 calls out the npm typosquat lesson (the `graphify` vs `graphifyy` story) so the install must verify package name, maintainer, and pinned version. Per FR-DEP-003 the install must be captured in a workstation-side script or Ansible role so a workstation rebuild reproduces the state.

## Acceptance Criteria

**AC1 — Pre-flight clean baseline.**
- **Given** the workstation post-E1 (tag `phase-1-decommission-complete` is reachable from `git log`),
- **When** the operator runs `grep -rE 'mempalace|omega' ~/.claude/settings.json` and `which gitnexus`,
- **Then** the grep exits with no matches AND `which gitnexus` returns "no gitnexus in $PATH" (clean slate confirmed before install).

**AC2 — Supply-chain verification (NFR-SUPP-001 + typosquat guard).**
- **Given** the GitNexus repo is `https://github.com/abhigyanpatwari/GitNexus` (canonical per ADR-004 References),
- **When** the operator runs `npm view gitnexus@1.6.3 maintainers repository.url dist.shasum dist.integrity` and `gh api repos/abhigyanpatwari/GitNexus/commits --paginate -q '.[].commit.committer.date' | head -1` and `gh api repos/abhigyanpatwari/GitNexus/commits --paginate -q '.[].commit.committer.date' | tail -1`,
- **Then** all of:
  - The npm `repository.url` resolves to `github.com/abhigyanpatwari/GitNexus` (no typo / fork);
  - At least one maintainer matches `abhigyanpatwari` (or a documented co-maintainer);
  - The most recent commit date is within the last 90 days AND the gap between the oldest and newest of the latest 100 commits spans ≥ 90 days (NFR-SUPP-001 ≥ 3 months activity);
  - The `dist.shasum` and `dist.integrity` (SRI) values are recorded verbatim into `homelab-playbook/docs/decisions/gitnexus-v1.6.3-supply-chain-evidence.md` for future-rebuild verification.

**AC3 — Pinned global install succeeds.**
- **Given** AC2 has passed and the evidence file is committed,
- **When** the operator runs `npm install -g gitnexus@1.6.3` (exact pin, NOT `@latest`),
- **Then** `gitnexus --version` prints `1.6.3` AND `which gitnexus` resolves to a path under the global npm prefix AND `npm ls -g --depth=0 gitnexus` lists `gitnexus@1.6.3` with no UNMET PEER DEPENDENCY warnings.

**AC4 — CLI surface available for downstream stories.**
- **Given** AC3 has passed,
- **When** the operator runs `npx gitnexus --help` and `npx gitnexus@1.6.3 mcp --help`,
- **Then** both commands exit 0 AND the output references the `setup`, `cypher`, `impact`, `context`, and `reindex` subcommands or tools (the surface E2-S03 and E2-S06 will exercise; satisfies architecture §7.1 GitNexus tool inventory).

**AC5 — Install captured in repeatable artifact (FR-DEP-003).**
- **Given** AC3 has passed,
- **When** the operator opens the new file `homelab-playbook/scripts/install-gitnexus-workstation.sh` (or, equivalently, the `homelab-playbook/roles/ai-dev-workstation/tasks/gitnexus.yml` snippet of an existing role),
- **Then** the file contains: the exact pinned install command, the SRI integrity hash from AC2, a comment block referencing ADR-004 + this story ID, AND a mode-755 shebang OR a valid Ansible task block; AND the script/role can be re-run idempotently (re-running it on an already-installed workstation completes ≤ 5 s and exits 0 without reinstalling).

**AC6 — Telemetry / network audit at install time.**
- **Given** GitNexus has no documented telemetry per architecture §5.3,
- **When** the operator runs `strace -f -e trace=network -o /tmp/gitnexus-strace.log gitnexus --version` (or runs the install behind a transient `iptables` deny-egress rule and confirms it succeeds — npm install itself is the only network step expected),
- **Then** `gitnexus --version` makes zero outbound TCP connections (the install-time telemetry-off check, distinct from the reindex-time check in E2-S05); evidence appended to the supply-chain evidence file.

## Implementation Notes

**Reference architecture sections:** §4.1 Code-graph layer (install command verbatim), §5.3 Security (typosquat lesson), §11 AR1 + AR4 (footprint + abandonment risks), §8.1 Workstation install commands.

**Reference ADRs:** ADR-004 (GitNexus adoption rationale + reversal trigger), ADR-005 (MCP-first stance — confirms why we install GitNexus at all instead of a skill-only alternative).

**Concrete commands:**

```bash
# AC1 — clean-baseline check
grep -rE 'mempalace|omega' ~/.claude/settings.json && echo "DIRTY" || echo "CLEAN"
which gitnexus || echo "absent (expected)"

# AC2 — supply-chain verification
npm view gitnexus@1.6.3 maintainers repository.url dist.shasum dist.integrity
gh api repos/abhigyanpatwari/GitNexus/commits --paginate -q '.[].commit.committer.date' | head -1
gh api repos/abhigyanpatwari/GitNexus/commits --paginate -q '.[].commit.committer.date' | sed -n '100p'

# AC3 — install (pinned)
npm install -g gitnexus@1.6.3
gitnexus --version
npm ls -g --depth=0 gitnexus

# AC4 — surface check
npx gitnexus --help
npx gitnexus@1.6.3 mcp --help

# AC6 — install-time network audit
strace -f -e trace=network -o /tmp/gitnexus-strace.log gitnexus --version
grep -E 'connect|sendto' /tmp/gitnexus-strace.log | grep -vE '127\.0\.0\.1|::1|AF_LOCAL' | wc -l   # expect 0
```

**Evidence file path:** `homelab-playbook/docs/decisions/gitnexus-v1.6.3-supply-chain-evidence.md` — capture maintainer list, SRI hash, commit-activity dates, strace summary, install date.

**Install-capture file path:** `homelab-playbook/scripts/install-gitnexus-workstation.sh` (preferred shape per existing repo pattern; no Ansible role added yet for the workstation since dev_hosts pattern is container-side). Idempotency check: leading guard `if gitnexus --version 2>/dev/null | grep -q '^1\.6\.3$'; then echo "already installed"; exit 0; fi`.

## Test Plan

**Pre-state:**
- `git log --oneline | grep phase-1-decommission-complete` resolves (E1 merged).
- `which gitnexus` returns nothing.
- `~/.claude/settings.json` has no `mempalace`/`omega` entries.

**Action sequence:**
1. Run pre-flight grep + which (AC1).
2. Run supply-chain verification commands (AC2); copy evidence into the evidence file.
3. Run `npm install -g gitnexus@1.6.3` (AC3).
4. Run `gitnexus --version` and CLI surface checks (AC3, AC4).
5. Run strace-based install-time network audit (AC6).
6. Author and commit `install-gitnexus-workstation.sh` (AC5); re-run it; confirm idempotent.

**Post-state checks:**
- `gitnexus --version` returns `1.6.3`.
- `npm ls -g --depth=0 gitnexus` lists `gitnexus@1.6.3`.
- Evidence file committed under `homelab-playbook/docs/decisions/`.
- Install script committed under `homelab-playbook/scripts/`.
- Re-running install script exits 0 in ≤ 5 s without modifying anything.

**Rollback:**
- `npm uninstall -g gitnexus` returns the workstation to pre-AC3 state (≤ 30 s).
- `git revert <commit>` removes the evidence + install-script files from the playbook.
- Removal does not affect `~/.claude/settings.json` (no MCP/hook wiring yet — that's E2-S03 / E2-S04).

## Dependencies

- **Blocked by:** E1 (entire epic) — settings.json must be clean of OMEGA before any new MCP wiring is anywhere near it.
- **Blocks:** E2-S02 (footprint check needs the binary present), E2-S03 (MCP registration needs the CLI), E2-S04 (hooks need MCP registered), E2-S05–E2-S08 (everything downstream).

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| GitNexus v1.6.3 was yanked from npm between architecture phase and Sprint 2. | Low | High — re-pin needed; potentially re-spike. | AC2 explicitly fetches `npm view`; if 1.6.3 is gone, story HALTS and ADR-004 is amended with a new pin before story restarts. |
| Maintainer changed / package transferred (typosquat-by-takeover). | Low | High — supply-chain compromise. | AC2 maintainer check; if unfamiliar, story HALTS. |
| Node.js global install blocked by workstation policy or PATH issue. | Low | Med — install fails. | Verify `npm prefix -g` is on PATH; if not, configure once and document in install script. |
| Strace not available on workstation. | Low | Low — alt audit needed. | Fallback to `tcpdump -i any -n 'tcp and not (host 127.0.0.1)' &` while running `gitnexus --version`; achieves same evidence. |

## Definition of Done

- [ ] AC1–AC6 all green and evidenced.
- [ ] `homelab-playbook/docs/decisions/gitnexus-v1.6.3-supply-chain-evidence.md` committed with the maintainer list, SRI hash, commit-activity dates, and strace summary.
- [ ] `homelab-playbook/scripts/install-gitnexus-workstation.sh` committed, mode 755, idempotent.
- [ ] `gitnexus --version` returns `1.6.3` on the workstation.
- [ ] Story status updated from `draft` to `done` in this file's frontmatter; PR linked.
- [ ] Story result captured in OMEGA via `omega_store(...)` per CLAUDE.md memory rule.
