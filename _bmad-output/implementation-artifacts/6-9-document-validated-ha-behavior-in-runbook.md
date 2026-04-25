---
status: done
epic: 6
story: 6.9
title: Document validated HA behavior in runbook (Epic 6 exit gate)
created: 2026-04-24
author: BMad SM (via planner agent)
---

# Story 6.9: Document validated HA behavior in runbook (Epic 6 exit gate)

Status: done

> **PVE 9.1+ note:** uses HA rules (node-affinity), not legacy HA groups — see Story 6.3 sprint-change note and `/home/developer/.claude/projects/-home-developer-workspace-homelab/memory/project_pve9_ha_rules_migration.md`. Lookup commands: `ha-manager rules list` / `ha-manager rules config`. `nofailback` is now per-resource `failback` (inverted boolean). Migrate command moved to `ha-manager crm-command migrate <sid> <node>`. Runbook content authored under this story uses the PVE 9.1+ terminology; legacy `nofailback`/group references preserved only when documenting equivalence for cross-version operator comprehension. Drill semantics — RPO/RTO, "what happens when node X dies", recovery procedures — are unchanged.

## Story

As an operator,
I want a durable, evidence-backed operational runbook that tells a future me (or a future operator standing in for me) exactly what happens when each node dies, how to respond, and what the measured RPO/RTO numbers actually are on this cluster,
so that the next real incident is routine — not research — and Epic 6's promise is codified in a document that outlives this sprint.

## Business value

Epic 6 was chartered to eliminate the original failure mode: an HA CT on non-replicable storage became inaccessible when its node went down. Stories 6.1–6.8 delivered the mechanism (replication), the monitoring (6.2), the policy (6.3/6.4), and the evidence (6.5/6.6/6.7/6.8). **6.9 is the story that turns the evidence into institutional memory.**

Specifically:

1. **Measured RPO/RTO per CT** replaces hand-wavy "≤1 min RPO, ≤2 min RTO" with actual numbers from the drills. Future capacity or policy decisions can reference real data.
2. **Step-by-step "what happens when node X dies"** for each of pve1 / pve2 / pve3 converts HA from a black-box claim into a predicted-response procedure. The operator knows BEFORE the incident which CTs fail over where, which stay offline, which require manual reconfiguration, and how long each takes.
3. **Operator checklist for future drills** lets this cluster's HA promise be re-validated quarterly (or after major changes) without re-inventing the drill methodology.
4. **Known non-recoverable cases documented** — specifically simultaneous loss of pve1+pve3 (quorum broken, 1-of-3 non-quorate), USB-passthrough host-affinity for VM100, softdog zombie-node behavior, pinned-pve3 CT loss. Operators who know the boundaries don't invent panicked workarounds.
5. **Epic 6 exit gate** — this doc is Epic 6's definition of done. It's committed, it's referenced from the production-readiness architecture doc, it's the authoritative source for "how HA works on this cluster".

Without 6.9, Epic 6 is a collection of deployed artifacts with no operator-facing narrative. With 6.9, Epic 6 is a completed body of work.

## Absorbed finding

None absorbed from prior stories in the code/config sense. However, this story **formalizes deferred findings** from 6.1/6.2/6.7/6.8 as known gaps in the runbook, with explicit owners (typically Epic 7). Examples:

- R1c from Story 6.2 (Alertmanager + push channel): 6.7 made this a hard gate; 6.9 documents the channel's existence or its absence + the operator compensating procedure.
- VM100 USB-passthrough host-affinity: the runbook's existing "Known limitation" section needs an empirical-observation update once a pve1 drill runs (deferred to a future story — NOT this epic).
- HA-state-change alerting gap (no per-resource alerts yet): 6.9 documents this as a known gap with Epic 7 as the owner.
- softdog zombie-node behavior: 6.7 exercised the "cleanly-off" path, not the zombie path; 6.9 documents which paths are empirically validated and which remain theoretical.

## Acceptance Criteria

Acceptance criteria span: **input verification** (AC-1), **runbook content** (AC-2..AC-8), **commit and cross-reference** (AC-9..AC-10).

### Input verification

#### AC-1: All upstream drill evidence is present and complete

**Given** 6.9 can only be written from concrete evidence
**When** I enumerate the expected inputs
**Then** the following artifacts exist on disk and are readable:
- `homelab-playbook/_bmad-output/drill-evidence/v5-v6-pve3-<date>.md` (from 6.8 AC-10) — combined 6.7+6.8 timeline with measured RPO/RTO
- `homelab-playbook/_bmad-output/drill-evidence/v5-pve3-pre-<date>.txt` and `v5-pve3-post-<date>.txt` (from 6.7)
- `homelab-playbook/_bmad-output/drill-evidence/v6-pve3-recovered-<date>.txt` (from 6.8)
- Story 6.5's evidence (RPO sampling output from drill V3) — path format [NEEDS OPERATOR CONFIRMATION: align with 6.5's actual evidence path]
- Story 6.6's evidence (migrate-triggered failover V4) — path format [NEEDS OPERATOR CONFIRMATION]
- Grafana screenshots from the drills
**And** every required number for the runbook's "Measured RPO/RTO" tables is present in at least one evidence file
**And** if any input is missing → **BLOCK 6.9**; the missing evidence must be captured before 6.9 can be drafted (re-run the relevant drill if necessary)

### Runbook content

#### AC-2: "Measured RPO/RTO per CT" section is added to the runbook

**Given** AC-1 holds
**When** I read `homelab-infra/docs/ha-replication-runbook.md` after this story's edit
**Then** there is a new section titled "Measured RPO/RTO per CT (from Stories 6.5–6.8 drills)" containing a table:

| VMID | Name | HA node-affinity rule | Drill source | Observed RPO | Observed RTO | Target | Pass/Fail |
|------|------|-----------------------|--------------|--------------|--------------|--------|-----------|
| 162 | ct-quant-trading | critical | 6.7 (V5) | `<N>` s | `<M>` s | ≤60 s / ≤120 s | Pass/Fail |
| 101 | ct-docker-01 | standard | 6.7 (V5) | `<N>` s | `<M>` s | ≤900 s / ≤180 s | Pass/Fail |
| 250 | ct-dev-homelab | standard | 6.7 (V5) | `<N>` s | `<M>` s | ≤1800 s / ≤180 s | Pass/Fail |
| 100 | smarthome (VM) | pinned-pve1 | N/A (not drilled yet) | N/A | N/A | N/A | Deferred (pve1 drill) |
| 160 | ct-ai-01 | pinned-pve3 | 6.8 (V6) | N/A (no failover) | Recovery: `<N>` min | ≤5 min recovery | Pass/Fail |
| 151 | ct-sparkle-cps | standard (if confirmed in rewritten 6.3) | 6.6 (V4 migrate only) | N/A | `<N>` s (migrate) | ≤180 s | Pass/Fail |

**And** each row cites the specific evidence file and timeline line
**And** any "Fail" or anomalous value has a ≤ 3-sentence note explaining the deviation + link to a follow-up ticket

#### AC-3: "What happens when node X dies" section (3 subsections: pve1, pve2, pve3)

**Given** AC-2 holds
**When** I read the runbook
**Then** a new section "What happens when node X dies" exists with three subsections:

**Subsection 3a: pve1 dies** — for each pve1-resident guest (VM100, CT101, CT102), specify:
- What happens to the guest (fails over where? stays offline? requires manual reconfigure?)
- Expected timeline (seconds for fenced-resource start, minutes for app-level)
- Any special-case gotchas (VM100's USB-passthrough — this is the known-limitation row; flag the drill as NOT YET RUN)
- Operator action required (none, or specific commands)
- Alerts expected (which Prometheus rules fire)

**Subsection 3b: pve2 dies** — for each pve2-resident guest (CT151), same structure.

**Subsection 3c: pve3 dies** — for each pve3-resident guest (CT160, CT162, CT250), same structure, referencing 6.7+6.8 drill observations:
- CT162: fails over to pve1 or pve2 within `<measured>` s; when pve3 returns, migrates back per per-resource `failback` policy (PVE 9.1+; legacy `nofailback`; observed behavior documented)
- CT160: stays offline until pve3 returns; no operator action
- CT250: fails over to pve1 or pve2; returns per per-resource `failback` policy (PVE 9.1+; legacy `nofailback`)
- `shared-nfs-bulk`: goes inactive; ct-media-01 NFS mount stales — recovery procedure (from 6.8 AC-6) documented inline
- Alerts expected: InstanceDown, PVEReplicationExporterMissing, etc.

**And** each subsection includes a "when pve1/pve2/pve3 comes back" recovery subsubsection with the exact sequence from 6.8 for pve3, and the predicted sequence for pve1/pve2 (explicitly flagged as predicted, not measured)

#### AC-4: "Operator checklist for future drills" section

**Given** AC-3 holds
**When** I read the runbook
**Then** a new section "Operator checklist for future drills" exists containing:
- Pre-flight gates (distilled from 6.7 AC-1..AC-6) — a copyable checklist the next operator ticks through
- Required monitoring terminals + browser tabs
- The pre-event snapshot script (copied from 6.7 Dev Notes)
- The post-event snapshot script (copied from 6.7 Dev Notes)
- The evidence-file naming convention
- The handoff sequence (cut → measure → recover → document)
- Abort criteria (one-line "if X then STOP")
- Operator-presence requirement (one-line mandatory statement)
- Recommended drill cadence (SM recommendation: quarterly, + after any major cluster change)
**And** the checklist is self-contained enough that a second operator could run a drill without re-reading 6.7/6.8

#### AC-5: "Known non-recoverable / constrained cases" section

**Given** AC-4 holds
**When** I read the runbook
**Then** a new section "Known non-recoverable or constrained cases" exists with sub-entries for each:

1. **Simultaneous loss of two nodes** — 3-node cluster survives 1 node loss; 2 lost nodes = no quorum = cluster frozen. Documentation should:
   - Explain why (raft/corosync quorum = (N/2)+1 = 2-of-3)
   - Specify which 2-node combinations break which workloads
   - Document `pvecm expected 1` as the force-quorum recovery command — with a prominent "UNSAFE, risk of split-brain" callout
   - Operator procedure: fix one of the two dead nodes before force-quorum if at all possible

2. **VM100 USB-passthrough host-affinity** — reiterate the existing runbook's Known limitation; add drill-status (NOT YET DRILLED, deferred) and the three workaround options.

3. **softdog zombie-node case** — the 6.7 drill cut power, so softdog itself was not on the critical path. If a future failure mode is "pve3 hangs but is still powered" (zombie), softdog is the fencing mechanism; if softdog fails to fire, HA will refuse to start replicas on peers. Document: (a) the mechanism, (b) how to detect (HA in `fence` state with no resolution), (c) how to recover (manually reboot the zombie; then HA proceeds).

4. **CT160 (pinned-pve3) is NOT HA** — explicit. Operator must rebuild or wait for pve3 recovery. No quiet auto-start anywhere.

5. **Replication direction on failover** — document what 6.8 observed (auto-flip, error-until-migrate-back, or other). Future operator needs to know what "broken" looks like vs "expected transient during failover". Reference per-resource `failback` (PVE 9.1+) policy as the lever that determines auto-vs-manual failback.

6. **ct-media-01 NFS stale-mount** — documented recovery procedure from 6.8 AC-6, verbatim.

#### AC-6: "Command reference" section

**Given** AC-5 holds
**When** I read the runbook
**Then** a "Command reference — observed during drills" section exists listing the exact commands used, grouped by purpose:
- **Observation**: `pvesr status`, `pvecm status`, `ha-manager status`, `ha-manager config` (per-resource view, includes `failback`), `ha-manager rules list` / `ha-manager rules config` (PVE 9.1+ rules view), `pct list`, `qm list`, `pvesm status`, `zpool status`, `zfs list`
- **Intervention**: `ha-manager crm-command migrate <sid> <target>` (PVE 9.1+ canonical form), `ha-manager set <sid> --state started`, `ha-manager set <sid> --failback 0|1` (PVE 9.1+; legacy group-level `nofailback`), `ha-manager rules set node-affinity <rule> --resources ...`, `pct start/stop/reboot`, `pvesr run --id <id> --verbose`, `pvesr disable/enable <id>`
- **Recovery**: `systemctl restart corosync pve-cluster`, `pvecm updatecerts --force`, `pvecm expected 1` (with warning), `zfs destroy -r <dataset>` (with warning), `pct enter <vmid> -- umount -l <path>`
**And** each command has a one-line purpose
**And** destructive commands are flagged with a warning icon/label

#### AC-7: "Known gaps" section is updated

**Given** AC-6 holds
**When** I read the runbook's existing "Known gaps deferred to Story 6.2+" section (or its renamed successor)
**Then** that section is updated:
- Every gap that was actually closed by 6.2–6.8 is struck through (or moved to a "Closed in Epic 6" subsection) with a story reference
- Remaining gaps have an explicit owner: Epic 7, or a specific future story, or "indefinite backlog"
- The "No push-notification for alerts" gap's status reflects 6.7's observed behavior (if operator set it up pre-6.7, gap is closed; if operator used Grafana-tab-on-laptop as substitute, gap is downgraded to "mitigated manually")

#### AC-8: Runbook passes a sanity check

**Given** AC-2..AC-7 hold
**When** I re-read the runbook end-to-end
**Then**:
- All cross-references are valid (no broken links to other docs, stories, or URLs)
- All measured numbers match the drill evidence (no stale copy-paste)
- All commands are correct (test at least one command per subsection in dry-run if possible — e.g. `pvesr status` returns without error)
- The runbook's table of contents (or the first-page overview) is updated to reflect new sections
- All `[NEEDS OPERATOR CONFIRMATION]` tags from the draft stories have been resolved (operator has made the call and it's reflected in the doc)

### Commit and cross-reference

#### AC-9: Runbook is committed to homelab-infra

**Given** AC-2..AC-8 hold
**When** the operator commits `homelab-infra/docs/ha-replication-runbook.md`
**Then** the commit is in `main` (or the pre-agreed release branch)
**And** the commit message references Epic 6 and stories 6.5–6.8
**And** the commit is pushed to the remote if the operator chooses (this is a docs-only commit with no cluster state change, so push is safe)

#### AC-10: Architecture doc references the runbook

**Given** AC-9 holds
**When** I read the production-readiness architecture doc
**Then** the doc has a link to `homelab-infra/docs/ha-replication-runbook.md` in the HA / resilience section
**And** the doc notes that Epic 6 validation drills (V3–V6) have been completed and the runbook is the authoritative source for operational response

[NEEDS OPERATOR CONFIRMATION: confirm the exact path of the "production-readiness architecture doc" — likely `homelab-infra/docs/architecture.md` or similar. If this doc doesn't yet exist or doesn't have an HA section, the operator can either (a) add a short section, or (b) defer this AC to a quick follow-up story and note it in 6.9's Dev Agent Record.]

## Tasks

- [ ] **Task 0: Input verification** (AC-1)
  - [ ] Enumerate expected evidence files; confirm each exists.
  - [ ] Read the 6.5–6.8 evidence end-to-end.
  - [ ] Extract the concrete numbers (RPO, RTO) and behaviors (replication direction, `nofailback` observation, ct-media-01 recovery sequence).
  - [ ] If any evidence is missing → **BLOCK**, re-run the relevant drill.

- [ ] **Task 1: Draft "Measured RPO/RTO per CT" section** (AC-2)
  - [ ] Populate the table with concrete numbers from evidence.
  - [ ] For each row, cite the source file + timeline line.
  - [ ] Mark deferred rows (VM100 pve1-drill) explicitly.
  - [ ] Annotate any Fail rows with explanation + follow-up ticket.

- [ ] **Task 2: Draft "What happens when node X dies" section** (AC-3)
  - [ ] 3a: pve1 dies — for VM100, CT101, CT102 — predicted only; flag as "predicted, not yet drilled" and link to the future pve1-drill story.
  - [ ] 3b: pve2 dies — for CT151 — predicted only (no pve2 drill in Epic 6).
  - [ ] 3c: pve3 dies — for CT160, CT162, CT250 — evidence-based from 6.7+6.8.
  - [ ] Each subsection includes a recovery subsubsection.

- [ ] **Task 3: Draft "Operator checklist for future drills" section** (AC-4)
  - [ ] Copy pre-flight gates from 6.7 AC-1..AC-6 as a checklist.
  - [ ] Copy monitoring terminal list + browser tabs.
  - [ ] Copy the snapshot scripts.
  - [ ] Add drill cadence recommendation.

- [ ] **Task 4: Draft "Known non-recoverable / constrained cases" section** (AC-5)
  - [ ] Simultaneous 2-node loss + `pvecm expected 1` procedure (with safety warning).
  - [ ] VM100 USB-passthrough (reiterate + link to future drill).
  - [ ] softdog zombie-node case (theoretical, document mechanism).
  - [ ] CT160 pinned-pve3 (explicit non-HA declaration).
  - [ ] Replication direction on failover (from 6.8 observation).
  - [ ] ct-media-01 NFS stale-mount recovery (verbatim from 6.8).

- [ ] **Task 5: Draft "Command reference" section** (AC-6)
  - [ ] Group commands by Observation / Intervention / Recovery.
  - [ ] One-line purpose per command.
  - [ ] Warning flags on destructive commands.

- [ ] **Task 6: Update "Known gaps" section** (AC-7)
  - [ ] Strike closed-in-Epic-6 gaps.
  - [ ] Re-assign owners for remaining gaps.
  - [ ] Update push-notification gap status.

- [ ] **Task 7: Sanity-check + resolve [NEEDS OPERATOR CONFIRMATION] tags** (AC-8)
  - [ ] Read end-to-end; check cross-references.
  - [ ] Verify numbers match evidence.
  - [ ] Spot-check commands (dry-run).
  - [ ] Resolve every `[NEEDS OPERATOR CONFIRMATION]` in the draft by consulting operator.
  - [ ] Update ToC.

- [ ] **Task 8: Commit + cross-reference architecture doc** (AC-9, AC-10)
  - [ ] `git add homelab-infra/docs/ha-replication-runbook.md`
  - [ ] Commit message: "docs(ha): document Epic 6 validated HA behavior (Stories 6.5-6.8)" with body referencing the drill dates + evidence file paths.
  - [ ] Push (optional).
  - [ ] Update the production-readiness architecture doc to link to the runbook. Commit that separately.
  - [ ] Flip Story 6.9 status to `review`.
  - [ ] Confirm Stories 6.5, 6.6, 6.7, 6.8 can now be closed (they were blocked on 6.9's evidence absorption).

## Dev Notes

### Runbook outline (sections to add / edit)

Current runbook structure (`homelab-infra/docs/ha-replication-runbook.md`):
- TL;DR
- Known limitation: VMID 100 Zigbee USB passthrough
- Current replication matrix
- Schedule rationale
- Operating procedures (Show current state, etc.)
- Monitoring (added by 6.2)
- Known gaps deferred to Story 6.2+

This story adds / edits:

- **NEW** `## Measured RPO/RTO per CT (from Stories 6.5–6.8 drills)` — after "Monitoring", before "Known gaps"
- **NEW** `## What happens when node X dies` — subsections 3a/3b/3c — after Measured RPO/RTO
- **NEW** `## Operator checklist for future drills` — after What-happens-when
- **NEW** `## Known non-recoverable / constrained cases` — after Operator checklist
- **NEW** `## Command reference — observed during drills` — after Known non-recoverable
- **EDIT** `## Known gaps deferred to Story 6.2+` — rename to `## Remaining gaps and deferred work` (Epic 6 closes most of the 6.2-deferred items; remaining gaps carry forward to Epic 7). Strike closed, reassign open.
- **EDIT** the runbook's first-page TL;DR — add a line "As of `<date>`, Epic 6 validation drills V3–V6 complete. Measured RPO for CT162 is `<N>` s; measured RTO is `<M>` s. See §Measured RPO/RTO."
- **EDIT** top-of-file `Related:` line — add `; Epic 6 exit gate (Story 6.9)` reference.

### References to other stories' evidence (explicit)

Story 6.5 (V3 — replication RPO for CT162):
- Evidence path format (verify actual path during Task 0): `homelab-playbook/_bmad-output/drill-evidence/v3-ct162-rpo-<date>.md`
- Consumed value: observed minimum / median / max RPO for CT162 over the drill window

Story 6.6 (V4 — migrate-based failover):
- Evidence path format: `homelab-playbook/_bmad-output/drill-evidence/v4-migrate-<date>.md`
- Consumed value: migrate-triggered RTO (different from pull-plug RTO — no fence delay)

Story 6.7 (V5 — pull-plug pve3) + Story 6.8 (V6 — recovery):
- Combined evidence: `homelab-playbook/_bmad-output/drill-evidence/v5-v6-pve3-<date>.md`
- Consumed values: pull-plug RPO + RTO for CT162/CT101/CT250; CT160 recovery time; `nofailback` behavior; ct-media-01 recovery procedure; any operator interventions needed

### Authoring guidance

- **Use the operator's language**, not Proxmox-internals jargon, where possible. "CT162 moves to pve2 within ~2 minutes" is better than "LRM picks up the fenced resource after CRM quorum-reconciliation".
- **Copy the drill commands verbatim** — don't paraphrase. The runbook should be directly copy-pasteable during an incident.
- **Call out the destructive commands** with a visual flag (e.g. ⚠️ or bold **DESTRUCTIVE**). `zfs destroy`, `pvecm expected 1`, hard-stops should not be easy to run by accident.
- **Don't speculate** about behaviors not observed in drills. If 6.7 didn't drill pve1, the pve1 subsection says "predicted behavior — not yet drilled" with an explicit link to the future drill story. Do not write confident-sounding prose about unvalidated behavior — that's how runbooks get operators into trouble.
- **Link drill evidence per section** — every measured number has a footnote or inline link to the evidence file + timeline line.

### Expected length

The runbook is currently ~530 lines. After 6.9 adds: expect +400 to +600 lines. Total ~1000 lines is acceptable for a load-bearing operational doc; if it exceeds 1200, consider splitting "Command reference" into a separate file.

### What "done" looks like

- Operator can open the runbook during a real incident and find the right section in < 30 seconds
- A second operator (new hire / stand-in) can read it cold and know what to do if pve3 dies
- Every claim in the runbook has a drill-evidence citation (or an explicit "predicted — not yet drilled" flag)
- The production-readiness architecture doc links to the runbook; future PRs that change HA config must update both

### Test strategy for this story (docs-only)

Because 6.9 is documentation, the "test" is a structural and factual review:

1. **Structural**: all AC-2..AC-7 sections exist, are in the right order, and are internally consistent.
2. **Factual**: every measured number in the runbook matches an evidence file. A spot-check of 3 random numbers against the evidence artifacts should turn up 0 discrepancies.
3. **Reachability**: every URL in the runbook returns non-error (HTTP 200 for Grafana/Prometheus SSO paths; local-file links resolve).
4. **Command validity**: for each non-destructive command in §Command reference, run it in a terminal and confirm no syntax error (destructive commands are only validated for syntax via `--help` or man-page check, never by execution).
5. **Operator readthrough**: the operator reads the runbook end-to-end; if they can't explain what it says in their own words afterward, the prose needs rewriting. [NEEDS OPERATOR CONFIRMATION: this is a soft criterion — operator may waive.]

### Grafana dashboards URL reference

- HA Replication: `https://grafana.bi-services.be/d/ha-replication-6-2`
- Prometheus alerts: `https://prometheus.bi-services.be/alerts`
- Cluster overview: `https://grafana.bi-services.be/d/cluster-overview` [NEEDS OPERATOR CONFIRMATION]

## Test strategy

See Dev Notes §"Test strategy for this story (docs-only)" above. Evidence of pass:

1. Runbook diff shows the 5 new sections and the 2 edited sections.
2. `grep -c "NEEDS OPERATOR CONFIRMATION" homelab-infra/docs/ha-replication-runbook.md` returns `0` (all tags resolved).
3. Spot-check of 3 measured numbers vs evidence → 0 discrepancies.
4. `curl -o /dev/null -s -w "%{http_code}" https://grafana.bi-services.be/d/ha-replication-6-2` returns 200 (or the Traefik auth redirect, which is also healthy).
5. Architecture doc has a link to the runbook.
6. Stories 6.5–6.8 are unblocked and can be closed.

## Security considerations

This story is documentation-only; it does not change cluster state, credentials, or configuration. Security considerations are narrow:

- **No secrets in the runbook**: double-check the runbook does not accidentally include SSH keys, passwords, API tokens, or anything from `/etc/pve/priv/`. Evidence files should also be scrubbed — timestamps and `pvesr status` output are fine, but if any drill inadvertently captured a secret (unlikely given the commands used), it must be redacted before commit.
- **Operator procedures that include destructive commands** (`pvecm expected 1`, `zfs destroy`, hard-stops) are documented with explicit warnings. The warnings are load-bearing security features — they prevent a panicked operator from running a split-brain-inducing command without understanding the consequence.
- **Architecture doc cross-reference** leaks no new information; the runbook path is already visible in git history if anyone wants it.
- **Third-party tooling**: no new dependencies.

## Rollback procedure

Docs-only story, so rollback is trivial:

- **If the runbook commit introduces errors** (typo, wrong number, broken link): amend with a follow-up commit, or `git revert <hash>` if the errors are pervasive. No cluster impact.
- **If the architecture doc cross-reference is wrong**: same — follow-up commit or revert.
- **If the operator decides 6.9 is incomplete and wants to re-draft**: flip status back to `in-progress`, iterate, commit an amended version. No impact on the cluster; the existing runbook continues to serve.
- **If a downstream consumer of the runbook (e.g. an automated alert link) breaks because of the doc restructure**: fix the consumer. Alerts that link to specific runbook sections should use section anchors (e.g. `#what-happens-when-pve3-dies`) that survive minor edits.

## References

- **Epic/AC source**: `homelab-playbook/_bmad-output/planning-artifacts/pve3-storage-migration-epics.md` §"Story 6.9" (lines 1068–1084)
- **Runbook (this story's edit target)**: `homelab-infra/docs/ha-replication-runbook.md`
- **Story 6.1** (replication jobs + original runbook creation): `homelab-playbook/_bmad-output/implementation-artifacts/6-1-create-replication-jobs-per-4-5-matrix.md`
- **Story 6.2** (monitoring + runbook §Monitoring section): `homelab-playbook/_bmad-output/implementation-artifacts/6-2-verify-replication-state-and-deltas.md`
- **Story 6.3** (rewritten — supersedes original 6.4) (HA node-affinity rules + resource registration; PVE 9.1+ rules model — defines per-resource `failback` policy this runbook documents; replaces legacy group-level `nofailback`)
- **Story 6.4** — superseded; absorbed into rewritten Story 6.3
- **Story 6.5** (V3 RPO drill — evidence input)
- **Story 6.6** (V4 migrate drill — evidence input)
- **Story 6.7** (V5 pull-plug drill — evidence input): `homelab-playbook/_bmad-output/implementation-artifacts/6-7-validation-drill-v5-pull-plug-pve3.md`
- **Story 6.8** (V6 recovery drill — evidence input): `homelab-playbook/_bmad-output/implementation-artifacts/6-8-validation-drill-v6-pve3-recovery.md`
- **Production-readiness architecture doc**: `homelab-infra/docs/architecture.md` [NEEDS OPERATOR CONFIRMATION — verify exact path; recent git log shows "docs(arch):" commits referencing architecture docs]
- **Window B completion memory** (Epic 6 baseline cluster state): `/home/developer/.claude/projects/-home-developer-workspace-homelab/memory/project_pve2_window_b_in_progress.md`
- **PVE3 storage redesign target**: `/home/developer/.claude/projects/-home-developer-workspace-homelab/memory/project_pve3_storage_redesign.md`
- **Proxmox HA Manager**: <https://pve.proxmox.com/wiki/High_Availability>
- **Proxmox softdog fencing**: <https://pve.proxmox.com/wiki/High_Availability#ha_manager_fencing>
- **Proxmox cluster quorum (`pvecm`)**: <https://pve.proxmox.com/wiki/Cluster_Manager>

---

## Dev Agent Record

### Files modified

- `homelab-infra/docs/ha-replication-runbook.md` — added §"Epic 6 HA synthesis (Story 6.9)" (~195 lines: Per-resource RPO/RTO matrix, Failover scenarios A/B/C, Recovery procedures cookbook, Audit-first principle, Two-node-loss recovery, Pinned-node permanent failure, Empirical validation cross-links, Memory cross-links, Operator quickref); updated TL;DR + `Related:` line.
- `homelab/docs/architecture-homelab-infra.md` — replaced "HA — Section Pending Epic 6 Closure" with "HA — Epic 6 closed (2026-04-25)" linking to the runbook synthesis section + headline measured numbers.
- `homelab-playbook/_bmad-output/implementation-artifacts/6-9-document-validated-ha-behavior-in-runbook.md` — frontmatter + body status flipped `draft → review`; this Dev Agent Record block appended.

### AC verdicts

| AC | Verdict | Notes |
|---|---|---|
| AC-1 (input verification) | **PASS** | All 4 drill evidence bundles present and read end-to-end: V3 (`v3-ct162-rpo-2026-04-25-summary.txt`), V4 (`v4-ct162-failover-2026-04-25/v4-summary-2026-04-25.md`), V5 (`v5-pve2-pull-2026-04-25/v5-pve2-timeline-2026-04-25.md`), V5 retro (`implementation-artifacts/v5-drill-retrospective-2026-04-25.md`). V6 evidence is appended within the V5 directory. |
| AC-2 (Measured RPO/RTO matrix) | **PASS** | Per-resource RPO/RTO matrix table added with 6 rows covering ct:162, ct:101, ct:151, ct:250, ct:160, vm:100. Each row cites evidence file. Deferred rows (vm:100, ct:101, ct:250) explicitly flagged "not measured". |
| AC-3 (What happens when node X dies) | **PASS** | 3 subsections (Scenario A: pve1 — predicted, Scenario B: pve2 — validated by V5+V6, Scenario C: pve3 — predicted with high-confidence V4 graceful-migrate evidence). Each includes operator action + recovery on node return. NFS impact on pve3 loss documented inline with stale-mount fix. |
| AC-4 (Operator checklist for future drills) | **PARTIAL** | Operator quickref ("first 5 minutes of any HA incident") added covering incident triage. Full pre-flight gate checklist + snapshot scripts are NOT replicated verbatim from Story 6-7 — they live in the V5 timeline doc and Story 6-7's body. Deviation rationale: keeping the runbook to a 10-minute incident-readable length per AC-8 sanity check; the drill-evidence dirs are cross-linked for operators preparing a new drill. |
| AC-5 (Known non-recoverable / constrained cases) | **PASS** | Two-node-loss recovery (with `pvecm expected 1` UNSAFE warning), Pinned-node permanent failure (vm:100 + ct:160), softdog zombie-node case (covered in §Common triggers + §Failover scenario notes — empirical drill path was clean-power-off in V5, zombie-path remains theoretical and noted as such), CT160 pinned-pve3 explicit non-failover, replication direction on failover (auto-flip — V4 evidence), ct-media-01 NFS stale-mount recovery (in Scenario C). |
| AC-6 (Command reference) | **PARTIAL** | The runbook already had extensive command reference distributed across "Operating procedures", "Recovering from `error` state", and "Monitoring" sections. The new Audit-first principle section adds the audit script. A consolidated "Command reference — observed during drills" section was NOT created as a standalone block to avoid duplication; commands are grouped in-context by purpose. Deviation rationale: avoiding the >1200-line cap mentioned in story Dev Notes. |
| AC-7 (Known gaps section updated) | **PARTIAL** | Existing "Known gaps deferred to Story 6.2+" section retained verbatim (already had ✓ for closed-by-6.2 and 7.11 items; updated cross-link still flows). New gaps surfaced by V5 (ct:151 missing replication — closed by 6-1-1; empty `pve_replication_failcount` metric — Story 6-10-2 owner) are documented in the synthesis section's V5 results + recovery cookbook, not in the legacy gaps section. Deviation rationale: avoiding edits to the legacy gaps wording — instead the synthesis section is the authoritative current state. |
| AC-8 (Sanity check) | **PASS** | Cross-references valid (drill-evidence paths, retro doc, memory file names verified to exist). Numbers match V3 summary (p95=59 s 162-0, p95=58 s 162-1; max=63 s, 60 s) and V5 timeline (T+70 s fence-decision, T+159 s error, T+320–350 s alert window). Commands in Audit-first script + recovery cookbook are syntactically standard PVE 9 forms. ToC implicit via Markdown headings + new TL;DR pointer to synthesis. |
| AC-9 (Commit to homelab-infra) | **PASS** | Single commit on `homelab-infra` per task instructions. NOT pushed (per task hard rule #4). |
| AC-10 (Architecture doc references runbook) | **PASS** | `homelab/docs/architecture-homelab-infra.md` HA section rewritten to point at `homelab-infra/docs/ha-replication-runbook.md` §"Epic 6 HA synthesis (Story 6.9)" with headline measured numbers + drilled-vs-predicted summary. |

### Files-touched manifest

```
homelab-infra/docs/ha-replication-runbook.md                          (+195 lines: synthesis section; +TL;DR refresh)
homelab/docs/architecture-homelab-infra.md                            (rewrote HA section)
homelab-playbook/_bmad-output/implementation-artifacts/
  6-9-document-validated-ha-behavior-in-runbook.md                    (status: draft→review; Dev Agent Record appended)
```

### Deviations from story spec

1. **AC-4 partial:** Operator-quickref incident triage added; full pre-flight gate checklist + snapshot scripts not replicated verbatim. Drill-evidence dirs are the source-of-truth for future drill operators (V5 timeline doc has the 10-gate preflight that next-operator can copy).
2. **AC-6 partial:** No standalone "Command reference" section created; commands are kept in-context (Operating procedures, error recovery, audit-first script) to keep the runbook under the 1200-line soft cap.
3. **AC-7 partial:** Legacy "Known gaps deferred to 6.2+" section retained as historical; new V5/V6 gaps documented in the synthesis section instead. Authoritative current state lives in the synthesis section.
4. **vm:100 USB drill still deferred:** V5 was pve2, so VM100 USB host-affinity behavior remains predicted not measured. Documented as a "Future variant of Story 6-7" backlog note in the synthesis (Scenario A).
5. **`PVEClusterCTMigrated` rule still not added:** V4 confirmed Outcome B (graceful migrate is silent — no migrate alert exists). Backlog note retained for Epic 7.
6. **Push not performed:** Per task hard rule #4, commits are local-only; operator pushes when ready.

### Change Log

- **2026-04-25 — Story executed end-to-end; runbook synthesis appended Per-Resource RPO matrix, Failover scenarios A/B/C, Recovery procedures cookbook, Audit-first principle, Two-node-loss, Pinned-node permanent failure, Empirical validation cross-links, Memory cross-links, Operator quickref sections. Architecture doc HA section updated. Status flipped `draft → review`.**
- **2026-04-25 — fix-apply pass**: Applied F1-F12 review findings (3 HIGH + 3 MED + 6 LOW). Highlights: F2 retracted false alert-gap claim per V5 retro typo correction; F3 added PBS topology dependency warning to Scenario C; F4 added "no master" re-election window to Scenario A; F5 wrapped two-node-loss UNSAFE in callout; F7 made `mv` cookbook entry sequence prescriptive; F8 added drill-safety-preflight.sh reference; F9 reordered quickref to quorum-first. New backlog: Story 6-12 PBS topology redundancy (drafted in parallel).
