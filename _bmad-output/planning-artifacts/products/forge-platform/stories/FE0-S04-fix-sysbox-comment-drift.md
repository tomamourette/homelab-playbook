---
type: story
epic: FE0
id: FE0-S04
title: "Fix the sysbox comment drift in forge-platform code and docs"
size: S
priority: MUST
owner: dev
blocking: false
fr_refs: [FR-PRE-005]
nfr_refs: []
adr_refs: [ADR-004]
risk_refs: [R1]
status: done
date: 2026-09-09
---

# FE0-S04: Fix the sysbox comment drift in forge-platform code and docs

## User Story

As **tomamourette**, I want **every place in forge-platform's code and docs that claims workspaces run under sysbox (unprivileged DinD) corrected to state that they run `privileged = true`**, so that **an engineer — including a future me — reading the comments first does not port the wrong architecture, and the PoC's own documentation stops contradicting its own Terraform**.

## Background and Context

This is **R1** in the risk register: low severity individually, but high likelihood of wasted time, because the drift is pervasive rather than a single stale comment. Per the canon's verified fact table, `coder/templates/forge/main.tf:399-404` claims sysbox/unprivileged DinD **62 lines above** the actual `privileged = true` setting at `main.tf:566`, and `main.tf:559-566` itself carries the wrong rationale for why sysbox was rejected (blaming a Docker **version** incompatibility rather than the real cause established in E3 — the Docker 29.5.0 time-namespace default flip, fixable with a daemon flag). The same false claim persists in `docs/coder/setup.md:149-156` and across roughly nine sysbox mentions in `docs/coder/orchestration-adr.md`, including its "Current architecture (pilot)" section, and is repeated again in `workspace/Dockerfile`. The **only** place in the current tree that states the truth is `docs/coder/setup.md:141-146`.

This story exists so that FE1–FE4 dev work — and any future engineer generalizing Forge past this PoC — starts from documentation that matches the code, rather than discovering the mismatch mid-implementation the way this proposal's own analysis did. It is explicitly a documents-and-comments fix: it does **not** change `privileged = true` to anything else (that decision, and ADR-002's single-operator justification, is settled and out of scope here), and it does **not** attempt to solve sysbox (rejected per §3.3 — nestybox/sysbox#1011 is open with no maintainer response, sysbox-in-LXC is unsupported per the maintainer per nestybox/sysbox#860, and Debian 13 is absent from sysbox's distro-compatibility table).

## Acceptance Criteria

**AC1 — `main.tf:399-404` corrected.**
- **Given** the sysbox/unprivileged-DinD claim at `coder/templates/forge/main.tf:399-404`,
- **When** the dev rewrites the comment to state that the workspace container runs `privileged = true` (citing the line where that is set) and briefly notes why (ADR-002: single-operator, blast radius bounded by the LXC user namespace per E2),
- **Then** `grep -in sysbox coder/templates/forge/main.tf` no longer matches lines 399-404, and the comment accurately describes the actual runtime.

**AC2 — `main.tf:559-566` rationale corrected.**
- **Given** the wrong rationale ("sysbox 0.7.0 is incompatible with the host's Docker 29.6 … the alternative … risks the host runtime") at `main.tf:559-566`,
- **When** the dev rewrites it to state the real, narrower cause established in E3 (Docker 29.5.0's default-on private time namespaces, moby/moby#52326, fixable via `{"features":{"time-namespaces":false}}` in `daemon.json`) **and** the two independent reasons sysbox remains unavailable regardless of that flag (nestybox/sysbox#1011 open with no maintainer response; sysbox-in-LXC unsupported per nestybox/sysbox#860; Debian 13 absent from sysbox's compat table),
- **Then** the comment no longer attributes the rejection to a Docker version mismatch alone.

**AC3 — `docs/coder/setup.md:149-156` corrected.**
- **Given** the same wrong "downgrading host Docker+containerd … risks the host runtime" framing at `docs/coder/setup.md:149-156`,
- **When** the dev rewrites it consistently with AC2's corrected rationale,
- **Then** `docs/coder/setup.md:141-146` (the one place already stating the truth) and the corrected `:149-156` no longer contradict each other.

**AC4 — `docs/coder/orchestration-adr.md` sysbox mentions corrected.**
- **Given** approximately nine sysbox mentions in this file, including a "Current architecture (pilot)" section that describes sysbox as currently active,
- **When** the dev updates every mention to reflect that the workspace runs privileged, not under sysbox, and reframes "Current architecture (pilot)" to match reality,
- **Then** `grep -in sysbox docs/coder/orchestration-adr.md` shows only historical/rejected-alternative framing, none describing sysbox as the active runtime.

**AC5 — `workspace/Dockerfile` corrected.**
- **Given** the same sysbox claim repeated in `workspace/Dockerfile`,
- **When** the dev corrects the comment there to match AC1's framing,
- **Then** the Dockerfile's comments are consistent with `main.tf`.

## Implementation Notes

Reference ADR-004 (sysbox-rejected-and-the-docker-29-5-0-trap) for the exact corrected rationale text — this story's edits should be consistent with, and can quote from, that ADR once it exists. Reference E3 in the sprint-change-proposal for the underlying facts. This is a **documents-and-comments-only** change in forge-platform; it does not touch the `privileged = true` Terraform setting itself.

```bash
# Locate every sysbox mention across the affected files
grep -rn -i sysbox repos/forge-platform/coder/templates/forge/main.tf \
  repos/forge-platform/docs/coder/setup.md \
  repos/forge-platform/docs/coder/orchestration-adr.md \
  repos/forge-platform/workspace/Dockerfile

# After edits, confirm no stale "unprivileged DinD" claim remains near :399-404
sed -n '395,410p' repos/forge-platform/coder/templates/forge/main.tf
sed -n '555,570p' repos/forge-platform/coder/templates/forge/main.tf
```

## Test Plan

**Pre-state:** `grep -rn -i sysbox` across the four affected files returns the claims described in AC1–AC5, all asserting or implying sysbox/unprivileged DinD is the active runtime.

**Action sequence:**
1. Correct `main.tf:399-404` (AC1).
2. Correct `main.tf:559-566` (AC2).
3. Correct `docs/coder/setup.md:149-156` (AC3).
4. Correct `docs/coder/orchestration-adr.md`'s ~9 mentions (AC4).
5. Correct `workspace/Dockerfile` (AC5).
6. Re-run the grep sweep and manually review each remaining hit for correct framing (historical/rejected-alternative only).

**Post-state checks:**
- No file in the sweep claims sysbox is the active runtime.
- `docs/coder/setup.md:141-146` and the corrected `:149-156` agree.
- `terraform validate` in `coder/templates/forge/` still passes (comment-only changes should not affect this, but confirm).

**Rollback:** `git checkout -- <file>` per affected file on the forge-platform branch; this story touches no infrastructure state.

## Dependencies

- **Blocked by:** Nothing directly — proceeds independently of FE0-S01/S02.
- **Blocks:** Nothing hard-blocks on this, but per the canon's framing ("before anyone builds on it"), it should land before FE3-S01 (template branch work) so subsequent dev work isn't misled by the same stale comments while editing nearby code.

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Corrected comments drift again after this story, e.g. a future edit reintroduces sysbox language | Low | Low | None specific — acceptable residual risk for a PoC; a productisation phase (FE4-S05) could add a lint/grep check if this becomes a recurring pattern |
| Missing a sysbox mention outside the four files enumerated in this story | Low | Low | The `grep -rn -i sysbox` sweep in Implementation Notes is repo-wide within `forge-platform`, not limited to the four files, catching any the canon's spot-check missed |

## Definition of Done

- [ ] AC1–AC5 all green and evidenced.
- [ ] `grep -rn -i sysbox` across `forge-platform` shows only historical/rejected-alternative framing, none describing it as active.
- [ ] `terraform validate` still passes in `coder/templates/forge/`.
- [ ] Story status updated from `draft` to `done` in this file's frontmatter.
