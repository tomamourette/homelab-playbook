---
type: story
epic: FE1
id: FE1-S03
title: "HA replication to both peers and standard node-affinity rule membership for ct:167"
size: S
priority: MUST
owner: dev
blocking: false
fr_refs: [FR-SUB-005]
nfr_refs: [NFR-IAC-001]
adr_refs: []
risk_refs: [R6]
gate_refs: [k]
status: done
date: 2026-09-09
---

# FE1-S03: HA replication to both peers and standard node-affinity rule membership for ct:167

> **~~BLOCKED — do not start.~~ BLOCKER LIFTED 2026-09-09 — banner retained for the record.**
> Both §5.4 prerequisites now exist and were verified on the facts, not waived:
> `vault_forge_github_client_id` (20 chars) and `vault_forge_github_client_secret` (40) satisfy
> FE0-S01, and `vault_cloudflare_api_token` (53) + `vault_cloudflare_zone_id` satisfy FE0-S02 —
> all four present in `ansible/inventories/homelab/group_vars/vault.yml`. Lengths are of the
> **unquoted** values; no secret value was read or printed. See FE2-S06's banner for the full
> verification note. The original banner text follows unchanged:
>
> **BLOCKED — do not start.** Per §5.4 of the approved proposal, nothing in FE1–FE4 begins
> before **both** operator prerequisites exist:
> 1. **GitHub OAuth App** → `CODER_EXTERNAL_AUTH_0_ID/TYPE/CLIENT_ID/CLIENT_SECRET` (FE0-S01).
>    The only non-optional external credential in the whole PoC. Without it the workspace build
>    **fails** — `data "coder_external_auth" "github"` (`coder/templates/forge/main.tf:25-27`) has
>    no `optional = true` — and even if it did not, `forge-sync.sh` sources its token from
>    `coder external-auth access-token github` and **silently skips its entire clone block**, so
>    agentic-ai never lands and gates (b)–(e) are untestable.
> 2. **Cloudflare API token**, DNS-edit scope, zone `bi-services.be` (FE0-S02). Required for
>    **any** browser-trusted certificate — the homelab has no inbound `:80`/`:443`, so HTTP-01 is
>    impossible, not merely inconvenient. Wildcard scope is optional; the token is not.
>    **REVERSED 2026-09-09 — a wildcard IS required.** The token sentence still holds and the
>    token needs no re-scoping; only the "wildcard scope is optional" clause is dead. See the
>    amendment at the top of [ADR-005](../adrs/ADR-005-dns-01-wildcard-over-public-ingress.md).

## User Story

As **tomamourette**, I want **CT 167 replicated to both pve1 and pve2 and added to the `standard` node-affinity rule, entirely via the `pve-ha-replication` and `pve-ha-rules` Ansible roles**, so that **`ct-forge-01` is HA-eligible the same way every other project container is, without the live-state drift that direct `ha-manager`/`pvesr` calls have caused before**.

## Background and Context

Evidence **E7** and runbook §4 are unambiguous: HA is managed via the `pve-ha-rules` and `pve-ha-replication` Ansible roles, **not** direct `ha-manager` / `pvesr` invocation, which is reserved for break-glass recovery only. This is not a stylistic preference — bypassing the roles is **exactly how `ct:163` and `ct:164` drifted out of IaC** until they were backfilled on 2026-05-14, a concrete, dated incident this story exists to avoid repeating. NFR-IAC-001 restates this as a standing estate-wide rule.

The runbook's **Pitfall §5** states the failure mode a single replication job produces: "a single replication job is enough for 'data is safe' but not enough for 'HA failover succeeds'" — the `standard` rule spans `pve1,pve2,pve3`, so a CT on pve3 must replicate to **both** pve1 and pve2, at `*/15`, as jobs `167-0` (pve3→pve1) and `167-1` (pve3→pve2). This is the **ct:151 lesson**, cited directly by gate (k): "`ha-manager status` shows `ct:167 (pve3, started)` **and** `/etc/pve/replication.cfg` has **both** `167-0` and `167-1`."

**R6 is an open question this story surfaces but does not close.** pve1 carries a recorded, unresolved hard-hang crash-loop history (per operator memory `project_pve1_crash_loop.md`), and pve2 was measured at ~12 GB free on 2026-07-30 — neither node is an unconditionally reassuring failover target on a 3-node `standard` rule. Separately, whether `ct:167` should register `state: started` (always-on, fails over automatically) or `state: stopped` (replicates but stays stopped on a peer at failover) per the Project-CT HA Policy memory is **explicitly an operator call, made at this story, not decided by this document.** Replication to both peers is non-negotiable regardless of which `state` is chosen; the `state` choice only affects run-state behavior, not data safety.

## Acceptance Criteria

**AC1 — Two replication jobs added via the role's defaults, not direct CLI.**
- **Given** CT 167 exists (FE1-S02 done),
- **When** the dev edits `homelab-infra/ansible/roles/pve-ha-replication/defaults/main.yml` to append `167-0` (`source: pve3, target: pve1, schedule: "*/15"`) and `167-1` (`source: pve3, target: pve2, schedule: "*/15"`) to `ha_replication_jobs`,
- **Then** the edit is the only change made — no `pvesr create` or equivalent CLI command is run directly.

**AC2 — `standard` rule membership added via the role's defaults.**
- **Given** AC1's edit,
- **When** the dev appends `ct:167` to `homelab-infra/ansible/roles/pve-ha-rules/defaults/main.yml`'s `ha_resources` list (with `type: ct`, `vmid: 167`, `max_relocate: 1`, `max_restart: 3`, `failback: 1`) **and** to the `standard` rule's `resources` CSV,
- **Then** the `state:` field is set per the operator's explicit decision (recorded in AC3) — never defaulted without that decision.

**AC3 — `state` recorded as an explicit operator decision (R6). — DECIDED 2026-09-09: `stopped`.**

> **Operator decision, 2026-09-09 (REVISED same day — see correction below):** `ct:167` runs with **`state: started`**.
>
> **Correction.** The decision was first recorded as `stopped` on the basis of an incorrect
> description: `stopped` was explained as "HA treats off as correct; you start it manually".
> That is wrong. Proxmox's `stopped` state is ACTIVE — ha-manager shuts a running container down
> and keeps it down. On registration it immediately stopped ct:167
> (`pve-ha-lrm: stopping service ct:167`), blocking FE1-S04. Corrected to `started`.
>
> Useful mechanic discovered: `pve-ha-rules/defaults/main.yml:19-30` documents that `state:` is
> applied ONLY at registration — an existence guard skips it on later runs, so the role never
> re-asserts it. `ha-manager set <sid> --state` is therefore the sanctioned operator flip and
> survives subsequent role runs. Verified: role re-run after the flip reported changed=0.
>
> Superseded rationale (kept for the record): `stopped` was chosen to stop HA restarting the CT
> during repeated PoC stop/start cycles.

- **Given** the Project-CT HA Policy memory's guidance (`started` for always-on services, `stopped` for containers that should stay stopped on a peer at failover),
- **When** the operator is consulted specifically about `ct:167` given R6's context (pve1's unresolved hard-hang cycle, pve2's ~12 GB free measurement),
- **Then** the decision and its rationale are recorded in this story's Definition of Done before AC2's edit is finalized — **this is an operator call and this story does not make it on the operator's behalf.**

**AC4 — Both playbooks applied idempotently.**
- **Given** AC1–AC3's edits,
- **When** the dev runs `ansible-playbook playbooks/pve-ha-replication.yml` followed by `ansible-playbook playbooks/pve-ha-rules.yml` from `homelab-infra/ansible`,
- **Then** both complete with `failed=0`, and a second immediate re-run of both shows `changed=0` (idempotency).

**AC5 — HA pickup verified (gate k precondition).**
- **Given** AC4's successful playbook runs,
- **When** the dev runs `ssh root@pve3 "sleep 10 ; ha-manager status | grep ct:167"` and `ssh root@pve3 "cat /etc/pve/replication.cfg | grep -A3 '167-0\|167-1'"`,
- **Then** `ha-manager status` shows `ct:167 (pve3, stopped)` per AC3's recorded decision, and `/etc/pve/replication.cfg` contains **both** `167-0` and `167-1`.

## Implementation Notes

Reference runbook §4 (HA + replication) and Pitfall §4 (`ha-manager rules set` replaces `--resources`, doesn't append — the role's reconcile pass in `tasks/rules.yml` handles this safely; do not bypass it) and Pitfall §5 (single-peer replication). Reference `~/.claude/projects/-home-developer-workspace-homelab/memory/project_project_container_ha_policy.md` for the `state` decision framework, and `project_pve1_crash_loop.md` for the R6 context the operator should weigh.

```yaml
# homelab-infra/ansible/roles/pve-ha-replication/defaults/main.yml — append to ha_replication_jobs:
- jobid: "167-0"
  source: pve3
  target: pve1
  schedule: "*/15"
  rate: 50
  comment: "ct-forge-01 HA replica to pve1"
- jobid: "167-1"
  source: pve3
  target: pve2
  schedule: "*/15"
  rate: 50
  comment: "ct-forge-01 HA replica to pve2"
```

```yaml
# homelab-infra/ansible/roles/pve-ha-rules/defaults/main.yml — append to ha_resources:
- type: ct
  vmid: 167
  state: started   # or 'stopped' — OPERATOR DECISION, see AC3, R6
  max_relocate: 1
  max_restart: 3
  failback: 1
  comment: "standard-tier; ct-forge-01"

# ha_rules.standard.resources — include ct:167 in the CSV:
resources: "ct:101,ct:151,ct:163,ct:164,ct:167,ct:250"
```

```bash
cd homelab-infra/ansible
ansible-playbook playbooks/pve-ha-replication.yml
ansible-playbook playbooks/pve-ha-rules.yml

ssh root@pve3 "sleep 10 ; ha-manager status | grep ct:167"
ssh root@pve3 "grep -A3 '167-0\|167-1' /etc/pve/replication.cfg"
```

## Test Plan

**Pre-state:** CT 167 exists and is reachable (FE1-S02 done); neither replication job nor rule membership exists yet.

**Action sequence:**
1. Operator decides `started` vs `stopped` given R6 context (AC3).
2. Edit `pve-ha-replication` role defaults (AC1).
3. Edit `pve-ha-rules` role defaults with the decided `state` (AC2).
4. Run both playbooks (AC4), confirm idempotency on re-run.
5. Verify HA pickup and replication config (AC5).

**Post-state checks:**
- `ha-manager status | grep ct:167` shows the expected state.
- `/etc/pve/replication.cfg` has both `167-0` and `167-1`.
- Re-running both playbooks produces `changed=0`.

**Rollback:** Remove the `167-0`/`167-1` entries and the `ct:167` resource/CSV entry from the two role defaults files, re-run both playbooks (the role's reconcile pass will remove the live jobs/rule membership to match). Do **not** hand-run `ha-manager remove` or `pvesr delete` directly — that reintroduces the exact drift this story exists to prevent.

## Dependencies

- **Blocked by:** FE1-S02 (CT must exist), FE0-S01, FE0-S02 (§5.4).
- **Blocks:** FE4-S02 gate (k).

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| `state` decision (AC3) skipped or defaulted without operator input | Medium (easy to rush past) | Medium — could register an always-on always-fails-over CT on a pve1 with a known hard-hang cycle, or vice versa | AC3 is a standalone, explicit gate in this story's ACs, not folded silently into AC2 |
| Direct `ha-manager`/`pvesr` CLI used to "fix" a failed playbook run instead of debugging the role | Low, but historically has happened (ct:163/ct:164) | High — drifts state out of IaC, requires backfilling later | NFR-IAC-001 and this story's Background section name the exact prior incident as a deterrent |
| Only one replication job lands (e.g. a typo drops `167-1`) | Low | High — failover lands in `error` per the ct:151 lesson, undetected until an actual failover attempt | AC5 explicitly checks `/etc/pve/replication.cfg` for **both** job IDs, not just one |

## Definition of Done

- [ ] AC1–AC5 all green and evidenced.
- [ ] `state` decision recorded here: _______________ (operator decision, with rationale re: R6).
- [ ] Both replication jobs and the rule membership present via role defaults, applied idempotently.
- [ ] `ha-manager status` and `/etc/pve/replication.cfg` confirm HA pickup per AC5.
- [ ] Story status updated from `draft` to `done` in this file's frontmatter.
