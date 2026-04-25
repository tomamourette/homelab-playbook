---
status: draft
epic: 7
story: 7.13
title: pve-ha-rules reconcile mode (field-level drift detection)
created: 2026-04-25
author: BMad SM
---

# Story 7.13: pve-ha-rules reconcile mode

Status: draft

## Story

As an operator,
I want the `pve-ha-rules` Ansible role to detect AND reconcile field-level drift on existing rules and resources (not just whether they exist), so that an emergency `ha-manager rules set ...` I run outside Ansible doesn't silently persist while the role still reports `changed=0` on the next run,
so that `defaults/main.yml` becomes the single source of truth for HA placement policy in fact, not just in theory.

## Business value

The `pve-ha-rules` role authored in Story 6.3 enforces **presence**: if a rule by name exists in `/etc/pve/ha/rules.cfg`, the role's `tasks/rules.yml` skips it. If a resource by SID exists in `/etc/pve/ha/resources.cfg`, the role's `tasks/resources.yml` skips it. **Field-level drift is invisible.**

Concrete failure scenario:

1. Story 6.3 creates the `standard` rule with `--resources ct:101,ct:151,ct:250 --strict 0 --nodes pve1,pve2,pve3`.
2. During an incident, the operator runs (legitimately, under pressure):
   ```
   ssh pve1 "ha-manager rules set node-affinity standard --resources ct:101,ct:151"
   ```
   to drop ct:250 from the rule because ct:250's storage is having an issue and they want to keep it from being failed over.
3. Incident resolves. Operator forgets to update `defaults/main.yml`.
4. Next Ansible run: `tasks/rules.yml` sees `standard` exists (greps the rule name out of `rules.cfg`), reports `changed=0`, walks away. **ct:250 is still missing from the rule.** `defaults/main.yml` says `ct:101,ct:151,ct:250` but the cluster runs `ct:101,ct:151`.
5. Drift surfaces only the next time ct:250 needs to fail over — which, in the homelab's failure-distribution, is exactly the moment the operator can least afford to discover the rule is wrong.

The same hole exists for **resource fields**: an operator who runs `ha-manager set ct:151 --max_restart 10` on a hot day to keep a flapping CT on its home node will see that `max_restart` value persist past Ansible reconverge. `defaults/main.yml` says `max_restart: 3`; the cluster runs `max_restart: 10`. No alert fires; no log line records the divergence.

**7.13 closes this hole** by upgrading the role from "presence checks" to "parse-existing-then-set" reconcile mode. The pattern already exists in the codebase — `tasks/failback.yml` (Story 6.3 Dev Agent Record completion note 7) parses the per-stanza body of `resources.cfg`, extracts the current `failback` value for each SID, and only invokes `ha-manager set ... --failback N` when the desired value differs from the on-disk value. **7.13 generalises that pattern to all fields on rules and resources.**

This is Epic 7 reproducibility theme work: same axis as `pve-host-zfs-maintenance` (drift in scrub schedule), `pve-host-pve3-storage` (drift in zpool config), `apt-check` (drift in update reporting). The role becomes safe to run on a regular cadence (weekly playbook run via cron, or pre-merge CI gate) because reconverge actually means reconverge, not "noop if name exists".

## Absorbed finding

This story **absorbs** the Story 6.3 adversarial-review finding **R3 (MEDIUM severity)**: "`pve-ha-rules` Ansible role only checks resource/rule existence — does not reconcile field drift in `nodes`, `strict`, `comment`, or rule membership. An operator's emergency `ha-manager rules set ...` outside Ansible silently persists; next role run reports `changed=0` even though defaults/main.yml says otherwise."

R3's severity is MEDIUM (not gating like R1 / 6-10) because the failure mode requires both (a) an emergency manual edit and (b) the operator not remembering to update YAML — neither happens daily. But the cost when it does happen is real (silent placement-policy divergence; surfaces only in a drill or a real failover). Worth fixing as Epic 7 hardening, not blocking 6.5 drills.

## Acceptance Criteria

### AC-1: Role detects existing rule's `nodes` / `strict` / `comment` / `resources` field drift vs. defaults/main.yml

**Given** Story 6.3 left the cluster with 4 rules matching `defaults/main.yml`
**And** I introduce **synthetic drift** by running, on the cluster:
```
ssh pve1 "ha-manager rules set node-affinity standard --resources ct:101,ct:151"
ssh pve1 "ha-manager rules set node-affinity critical --comment 'Emergency-edited comment 2026-04-XX'"
ssh pve1 "ha-manager rules set node-affinity pinned-pve1 --strict 0"
```
(three independent drifts: `resources` membership shrunk on `standard`; `comment` mutated on `critical`; `strict` flipped on `pinned-pve1`)

**When** I run `ansible-playbook -i inventories/homelab playbooks/pve-ha-rules.yml --check` (dry-run)
**Then** the role's parse-existing-config step builds a per-rule fact (e.g. `_ha_existing_rules_state`) keyed by rule name, with a value that includes the on-disk `nodes`, `strict`, `resources` (sorted, comma-joined for stable comparison), and `comment` fields per rule
**And** the dry-run output flags **3 changes** (or more, depending on how the diff task is structured): one per drifted field
**And** the dry-run output includes a **diff block** for each changed rule showing `was: <on-disk>` → `wanted: <defaults>` for the changed fields specifically (not a wholesale rule rewrite)
**And** for the 1 undrifted rule (`pinned-pve3`), the role reports no change
**And** the same drift detection covers **resources** field drift on `ha-manager add`-registered guests: if I additionally run `ssh pve1 "ha-manager set ct:151 --max_restart 10"`, the role flags ct:151's `max_restart` field as drifted (3 desired, 10 actual). `--max_relocate`, `--state`, `--comment` get the same treatment.

### AC-2: Role calls `ha-manager rules set` (or `ha-manager set` for resources) to reconcile divergent fields

**Given** AC-1 holds with synthetic drift in place
**When** I run `ansible-playbook -i inventories/homelab playbooks/pve-ha-rules.yml` (real run, not `--check`)
**Then** the role invokes `ha-manager rules set node-affinity <rule> --<field> <desired-value>` for each drifted field on rules — **only the drifted fields**, not a wholesale `rules remove + rules add` cycle. Concretely:
- `ha-manager rules set node-affinity standard --resources ct:101,ct:151,ct:250`
- `ha-manager rules set node-affinity critical --comment 'Epic 6 critical-tier: ct-quant-trading'`
- `ha-manager rules set node-affinity pinned-pve1 --strict 1`

**And** the role invokes `ha-manager set <sid> --<field> <desired-value>` for each drifted field on resources:
- `ha-manager set ct:151 --max_restart 3`

**And** after the run, `cat /etc/pve/ha/rules.cfg` and `cat /etc/pve/ha/resources.cfg` match `defaults/main.yml` exactly for every drifted field
**And** the underlying CTs/VMs are NOT restarted by reconcile actions — `pct status <id>` and `qm status <id>` continue to report `running` throughout (drift correction is metadata-only; same property as `ha-manager set --failback` proven in Story 6.3 Task 3).

### AC-3: Role logs the drift diff before applying — useful for ops audit

**Given** AC-2 holds
**When** the real run executes the reconcile actions
**Then** Ansible output includes a clearly-labelled **diff block** per drifted item, showing the field name, the on-disk value, and the wanted value. Example shape (paraphrased — exact format up to `ansible.builtin.debug` task design):
```
TASK [pve-ha-rules : ha-rules: drift detected on rule 'standard'] *********
ok: [pve1] => {
    "drift": {
        "rule": "standard",
        "field": "resources",
        "was": "ct:101,ct:151",
        "wanted": "ct:101,ct:151,ct:250"
    }
}
```
**And** the diff is emitted **before** the corresponding `ha-manager rules set` action runs (so the operator sees what is about to change, not what just changed — important for `--check` mode parity)
**And** rules and resources with no drift do NOT emit a diff block (signal-to-noise: only flag what's changing)
**And** the diff is structured (a fact / debug var) so a future Story could render it into a prettier format (e.g. via callback plugin) without changing the role logic.

### AC-4: Idempotency — second run after reconcile reports `changed=0`

**Given** AC-2 + AC-3 hold (drift was reconciled in run 1)
**When** I run the playbook a second time, immediately, with no further synthetic drift
**Then** the run reports `changed=0` across all hosts (mirrors Story 6.3 Task 6's idempotency proof — the bar 7.13 must clear is not lower than what 6.3 cleared)
**And** the diff-detection step reports zero drift entries
**And** no `ha-manager rules set` or `ha-manager set` invocations fire (verified via Ansible's per-task `changed` status, or via `journalctl -u pve-ha-crm | grep 'rules\|set'` showing no recent activity)

### AC-5: Synthetic drift round-trip — operator manually drops a resource from a rule, role re-adds it, change=1

**Given** AC-4 holds (cluster is in defaults-matching state)
**When** I run `ssh pve1 "ha-manager rules set node-affinity standard --resources ct:101,ct:151"` (drop ct:250 from `standard`, mimicking the R3 scenario verbatim)
**And** I run the playbook
**Then** the run reports `changed=1` for the `standard` rule
**And** the diff block shows `field: resources, was: ct:101,ct:151, wanted: ct:101,ct:151,ct:250`
**And** after the run, `ssh pve1 "ha-manager rules config --type node-affinity"` shows the `standard` stanza with `resources ct:101,ct:151,ct:250`
**And** ct:250 is again subject to the standard rule's eligibility — verifiable via `ha-manager status` (ct:250's home node remains its current home; placement policy is restored without restart)
**And** running the playbook **a third time** (no further drift) reports `changed=0` (compound idempotency proof: drift-detect → reconcile → idempotent).

### AC-6: `--check` mode shows divergence without changing state

**Given** AC-5 left the cluster matching defaults
**When** I introduce drift again (`ssh pve1 "ha-manager rules set node-affinity standard --comment 'Drift test'"`)
**And** I run `ansible-playbook ... --check`
**Then** the dry-run output reports the `comment` drift on the `standard` rule, identifies the wanted value, and emits `changed=1` on the diff task
**And** **no** `ha-manager rules set` action runs against the cluster (verified via `cat /etc/pve/ha/rules.cfg` — the drifted comment is still present)
**And** running the **real** playbook immediately after the `--check` reconciles the drift; running it a second time reports `changed=0`
**And** the `--check` output is operationally useful — i.e. an operator can pipe it through `grep drift` or similar to get a quick "what's currently divergent on the cluster" report. Documented in the role README as a usage pattern.

### AC-7: Existing presence-creation path remains intact (regression check)

**Given** AC-6 holds
**When** I introduce a **presence** gap by running:
```
ssh pve1 "ha-manager rules remove pinned-pve1"
```
(rule deleted entirely — not field drift, but absence)

**And** I run the playbook
**Then** the role recreates the `pinned-pve1` rule via `ha-manager rules add node-affinity pinned-pve1 --nodes pve1 --resources vm:100 --strict 1 --comment '...'`
**And** the run reports `changed=1` on the rule-create task (presence path unchanged from Story 6.3)
**And** running the playbook again reports `changed=0` (idempotency unchanged)
**And** the same regression check is performed for **resource** absence: `ssh pve1 "ha-manager remove ct:151"` followed by playbook run → `changed=1` on the resource-add task; second run `changed=0`. (Confirms the new reconcile logic in `tasks/rules.yml` and `tasks/resources.yml` did not break the existing presence-creation guard from Story 6.3 Task 6.)

## Tasks

- [ ] **Task 0: Pre-flight** (baseline capture)
  - Cluster quorate; Story 6.3's 4 rules + 6 resources present and matching `defaults/main.yml`.
  - Capture `/tmp/ha-rules-pre-7-13.txt` (`ha-manager rules config`), `/tmp/ha-resources-pre-7-13.txt` (`cat /etc/pve/ha/resources.cfg`), `/tmp/ha-status-pre-7-13.txt` (`ha-manager status`).
  - Confirm dry-run of unmodified `pve-ha-rules` role reports `changed=0` (proves baseline is clean before introducing drift).

- [ ] **Task 1: Extend `tasks/rules.yml` to parse-existing-then-set** (AC-1, AC-2 for rules)
  - Use the same `slurp` of `/etc/pve/ha/rules.cfg` already present (`_ha_rules_cfg_raw`).
  - Add a stanza-split parser (model: `tasks/failback.yml`) that splits the cfg body on blank lines, walks each stanza, and builds a fact `_ha_existing_rules_state: {<rule-name>: {nodes: ..., strict: ..., resources: <sorted-list>, comment: ...}, ...}`.
  - For `resources` field: split the stored value on `,`, sort, re-join — same normalisation applied to `defaults/main.yml`'s value before comparison. Sort-then-compare prevents spurious drift from operator-typed `ct:151,ct:101,ct:250` vs. role-typed `ct:101,ct:151,ct:250`.
  - For `strict` field: cast to int for comparison (defaults uses `0` / `1`; on-disk stores `0` / `1`; explicit cast avoids `"0"` vs `0` mismatches).
  - For `comment`: string-equal comparison; if either side contains the empty string, treat both as equivalent.
  - Add a per-rule diff task that emits a `debug` block per drifted field (AC-3 shape).
  - Add the field-level `ha-manager rules set node-affinity <rule> --<field> <wanted>` invocation guarded by `when: <field>_drift`. One invocation per drifted field (NOT a wholesale rewrite — preserves the audit trail and avoids touching undrifted fields).

- [ ] **Task 2: Extend `tasks/resources.yml` to parse-existing-then-set** (AC-1, AC-2 for resources)
  - Same shape as Task 1 but against `/etc/pve/ha/resources.cfg`.
  - Stanza-split parser builds `_ha_existing_resources_state: {<sid>: {state: ..., max_relocate: ..., max_restart: ..., comment: ..., failback: ...}, ...}`.
  - **Reuse the existing `tasks/failback.yml`** — the `failback` field is already handled there; do not duplicate. Tasks/resources.yml handles `state`, `max_relocate`, `max_restart`, `comment`. Failback continues to be reconciled in its own file.
  - Per-field drift detection + per-field `ha-manager set <sid> --<field> <wanted>` invocations.
  - Emit per-resource diff blocks (AC-3 shape).

- [ ] **Task 3: Update `defaults/main.yml` schema documentation** (AC-3, AC-6)
  - Add comment block at top documenting the **reconcile contract**: every field listed in `ha_rules` and `ha_resources` is enforced; values not listed are not enforced (room for explicit-opt-out via `null` if the role grows that).
  - Document that `resources` lists are normalised (sort+join) — operator can write them in any order in YAML.
  - Document `--check` mode usage as a "what's currently divergent" report.
  - Document the `failback` field's separate-file reconcile path so the structure isn't surprising to a reader.

- [ ] **Task 4: Validate AC-1 through AC-6 against synthetic drift** (test plan)
  - Introduce drift per AC-1 (3 rules × different fields + 1 resource field).
  - Dry-run: confirm `changed=4`, diff blocks for each drifted field, no cluster state change.
  - Real run: confirm `changed=4`, diff blocks before each set action, on-disk state matches defaults.
  - Second run: `changed=0` (AC-4 idempotency).
  - AC-5 round-trip: drop ct:250 from standard, real-run reconciles, third-run `changed=0`.
  - AC-6: drift + `--check` shows drift without applying; subsequent real run applies; subsequent dry-run is clean.
  - Capture all evidence in `/tmp/7-13-drift-test-evidence.txt`.

- [ ] **Task 5: Validate AC-7 regression** (presence path unchanged)
  - Remove a rule entirely (`ha-manager rules remove pinned-pve1`); playbook run should `changed=1`, second run `changed=0`.
  - Remove a resource entirely (`ha-manager remove ct:151`); playbook run should `changed=1`, second run `changed=0`. **Note**: removing ct:151 momentarily un-HAs it; the role's `ha-manager add` re-HAs it. The CT itself is not stopped/restarted. Verify `pct status 151` is unchanged throughout.
  - Capture evidence: `/tmp/7-13-presence-regression-evidence.txt`.

- [ ] **Task 6: Update role README** (AC-3, AC-6, AC-7)
  - Document the new reconcile-mode behaviour at the top of the README (what changed vs. Story 6.3's presence-only role).
  - Document the diff output format (so future operators reading Ansible logs know what they're looking at).
  - Document `--check` as a drift-report tool.
  - Document the `failback` field's separate-file path explicitly (avoids confusion).
  - Add a "Manual interventions" section: when operators run `ha-manager rules set ...` outside Ansible, **document the change in the YAML defaults** at the next opportunity, OR accept that the role will revert it on the next run. Both are valid; the role makes the choice explicit instead of silent.

- [ ] **Task 7: Status flip to `review`** + Dev Agent Record
  - Append Dev Agent Record per Story 6.2/6.3 pattern.
  - Frontmatter `status: draft` → `status: review`.
  - **Operator-side TODO (NOT this task):** sprint-status YAML edit to mark 7.13 done — operator's review-and-flip step.

## Dev Notes

### Parse-existing-config pattern reference: `tasks/failback.yml`

**Read this file first:** `homelab-infra/ansible/roles/pve-ha-rules/tasks/failback.yml` (authored in Story 6.3, Dev Agent Record completion note 7). It is the canonical pattern for "parse on-disk state, build a fact, only apply when desired ≠ actual". The relevant snippets to mirror:

```yaml
# Stanza-split parser (avoids greedy-regex traps that swallow whole files)
loop: "{{ ((_ha_resources_cfg_raw_post.content | default('') | b64decode).split('\n\n')) | reject('match', '^\\s*$') | list }}"

# Per-stanza fact build
_hdr: "{{ stanza | regex_findall('^(ct|vm):\\s+([0-9A-Za-z_.\\-]+)') }}"
_fb: "{{ stanza | regex_findall('(?m)^\\s+failback\\s+([0-9]+)\\s*$') }}"
_stanza_kv: "{{ {(_hdr[0][0] ~ ':' ~ _hdr[0][1]): (_fb[0] if _fb else '')} if _hdr else {} }}"

# Conditional set
when:
  - item.failback is defined
  - _ha_failback_state.get(item.type ~ ':' ~ item.vmid, '') != (item.failback | string)
```

7.13 generalises this. For each field on `ha_rules` and `ha_resources`, the same shape applies: extract on-disk value via per-stanza regex, normalise (sort lists, cast ints), compare against desired, emit set-action only on mismatch.

The Story 6.3 Dev Agent Record completion-note 6 also documents a **subtle Ansible YAML escaping gotcha** that a reviewer of this story should know about: `\\s` in YAML block scalars (`>-`) is preserved as the two literal characters, not escaped to `\s`. **Use inline double-quoted strings** for any new regex tasks — same as `failback.yml` does. This will save a debug cycle.

### Why field-level set rather than wholesale `rules remove + add`

Three reasons:

1. **Audit trail.** A `--diff` log saying `field=resources was=A,B wanted=A,B,C` is dramatically more useful in a post-incident review than `rule=standard removed+recreated`.
2. **Atomicity.** `ha-manager rules remove standard` followed by `ha-manager rules add` has a window (10s+ of CRM tick) where `standard` doesn't exist. During that window, no resource has the standard rule's eligibility, which could affect placement decisions if a node fails simultaneously. `rules set` is a single in-place metadata edit on `pmxcfs`; no window.
3. **Comment preservation.** A wholesale recreate would lose any operator-added comments not codified in defaults; in-place set lets the role be conservative about touching only what it owns.

### Field set per rule type

Source of truth for valid fields: `/usr/share/perl5/PVE/HA/Rules/NodeAffinity.pm` and `man ha-manager` § rules. For `node-affinity` rules:

| Field | Set via | Comparison |
|---|---|---|
| `nodes` | `--nodes <comma-list>` | string-equal after sort+join |
| `strict` | `--strict 0\|1` | int |
| `resources` | `--resources <comma-list>` | string-equal after sort+join (each item is a `<type>:<vmid>` SID) |
| `comment` | `--comment '<string>'` | string-equal |

Per-resource fields (`ha-manager add` / `ha-manager set`):

| Field | Set via | Comparison |
|---|---|---|
| `state` | `--state started\|stopped\|disabled` | string-equal |
| `max_relocate` | `--max_relocate <int>` | int |
| `max_restart` | `--max_restart <int>` | int |
| `comment` | `--comment '<string>'` | string-equal |
| `failback` | `--failback 0\|1` | int (handled in `tasks/failback.yml`, do not duplicate) |

### Stanza format (live cluster reference)

Sample `/etc/pve/ha/rules.cfg`:
```
node-affinity: critical
        comment Epic 6 critical-tier: ct-quant-trading
        nodes pve1,pve2,pve3
        resources ct:162
        strict 0
```

Sample `/etc/pve/ha/resources.cfg`:
```
ct: 162
        comment Epic 6 critical-tier; <=1-min RPO target
        failback 1
        max_relocate 1
        max_restart 3
        state started
```

Per-stanza, fields are indented with TAB (or four spaces, depending on PVE version — handle both via `^\s+` regex). Each stanza ends with a blank line. Last stanza in the file may or may not have a trailing blank — split-on-`\n\n` + `reject('match', '^\\s*$')` handles both.

### Project-container `state` field handling — preserve Story 6.3's policy

Story 6.3's project-container HA state policy says: "if running, fail over and start on peer; if stopped, migrate the storage but stay stopped on peer". Implementation: `--state` matches the **current actual run-state** at registration time, not a blanket value. Defaults/main.yml currently codifies what was observed at Story 6.3 registration (`started` for both ct:151 and ct:250).

**Reconcile-mode tension:** if the operator manually `ha-manager set ct:151 --state stopped` (legitimate; they want it stopped on the peer post-failover), the role would currently revert that to `started` on the next run. **This is wrong** — operator policy intent gets clobbered.

**Resolution:** add a per-resource opt-out flag in `defaults/main.yml` to mark fields that the role should NOT reconcile:

```yaml
- type: ct
  vmid: 151
  state: started
  state_managed_by_operator: true   # role will NOT enforce state for this resource
  # ... other fields ...
```

When `state_managed_by_operator: true`, `tasks/resources.yml` skips the `state` field's drift check and reconcile action for that SID. All other fields (`max_restart`, `max_relocate`, `comment`) continue to be enforced.

**OPERATOR-RESOLVED 2026-04-25** (was NEEDS OPERATOR CONFIRMATION): Default for the flag in `defaults/main.yml`:
- **`state_managed_by_operator: true`** for **project containers**: `ct:151` (sparkle-cps), `ct:250` (dev-homelab) — preserves the Story 6.3 project-container HA state policy ("if running, fail over; if stopped, stay stopped") so reconcile-mode never clobbers a deliberate operator stop.
- **`state_managed_by_operator: false`** for **always-on infra**: `ct:101` (docker), `ct:160` (ai-host), `ct:162` (quant-trading), `vm:100` (smarthome) — these MUST stay `--state started`; reconcile-mode should clobber any drift.

Document this in the role README under "Project-container state policy" — explicit cross-reference to Story 6.3's project-container HA state policy section AND the `project_project_container_ha_policy.md` memory.

### Why this is a separate story rather than a 6.3 amendment

6.3 is in `review` and shipped a working role with presence-only checks. The R3 finding was MEDIUM, not gating; 6.3 was shipped explicitly with this gap acknowledged in the Dev Notes ("Updating an existing rule uses `ha-manager rules set node-affinity <name> ...`, not `add`. For 6.3's scope, assume fresh state and don't build the reconcile path — that's Epic 7 hardening."). 7.13 is the Epic 7 hardening that 6.3 deferred to. Cleaner backlog item than amending a closed story.

### What "done" looks like post-Story-7.13

- `pve-ha-rules` role's `--check` mode is a useful drift report: `ansible-playbook ... --check | grep drift` shows every divergent field on every rule and resource.
- Real run reconciles every drifted field via `ha-manager [rules] set <thing> --<field> <wanted>`; second run `changed=0`.
- Operator emergency edits no longer silently persist — they either get reverted on next reconverge OR the operator updates `defaults/main.yml`. Either path is explicit.
- Project-container `state` field retains operator-policy precedence via the `state_managed_by_operator` opt-out (assuming operator confirms the recommendation).
- Existing presence-creation logic from 6.3 is untouched — AC-7 regression check proves it.

## Test strategy

**Phase 1 (Task 0):** observation-only baseline. Confirm 6.3's role reports `changed=0` cleanly against the unmodified cluster.

**Phase 2 (Tasks 1-3):** code change to the role + defaults documentation. No cluster state change yet.

**Phase 3 (Task 4):** synthetic-drift validation against the live cluster.
- Drift introduction: 3 rule fields + 1 resource field manually edited via `ha-manager`.
- Dry-run: confirms drift detected, `--check` makes no state change.
- Real run: reconciles all 4 drifted fields; on-disk matches defaults.
- Second run: `changed=0` idempotency.
- Round-trip drop-and-restore: ct:250 dropped from standard, role re-adds, third run `changed=0`.

**Phase 4 (Task 5):** regression validation. Presence path (rule-remove, resource-remove) still works.

**Phase 5 (Task 6):** README update.

**Phase 6 (Task 7):** status flip + Dev Agent Record.

**Drill safety:** all drift introduced in this story's testing is to **metadata only** — `comment`, `strict` (on a rule with all 3 nodes member, so 0/1 has no observable effect under normal operation), `resources` membership shrink-and-restore, `max_restart` value. None of these affect running guests or cause restarts. The presence-removal regression check (AC-7) does momentarily un-HA a guest, but the underlying CT/VM is not stopped (Story 6.3 §"Safety of HA-add operations" applies in reverse for `ha-manager remove`).

**Window:** can run during business hours; no scheduling constraint like Story 6.10's drill. ct:162's market-hours sensitivity does not apply since this story does not stop or restart any guest.

## Rollback procedure

Trivial — revert the role:
```
git checkout homelab-infra/ansible/roles/pve-ha-rules/
git checkout homelab-infra/ansible/roles/pve-ha-rules/defaults/main.yml
git checkout homelab-infra/ansible/roles/pve-ha-rules/tasks/{rules,resources}.yml
git checkout homelab-infra/ansible/roles/pve-ha-rules/README.md
```
After revert, the role behaves exactly as Story 6.3 left it — presence-only checks, no reconcile mode. No cluster state to roll back; AC-2's reconcile actions are functionally `ha-manager set` calls that the operator can reverse manually if needed (or accept; the on-disk values match `defaults/main.yml` by definition after a successful reconcile, which is the desired end state regardless of whether 7.13 ships).

## References

- **Adversarial finding source**: Story 6.3 review (`/tmp/6-3-adversarial-review.md` or operator's review notes), R3 MEDIUM-severity finding
- **Parse-existing pattern reference**: `homelab-infra/ansible/roles/pve-ha-rules/tasks/failback.yml` (Story 6.3, completion note 7) — **canonical model for this story**
- **Role to extend**: `homelab-infra/ansible/roles/pve-ha-rules/` (presence-only as of Story 6.3)
- **Role README to update**: `homelab-infra/ansible/roles/pve-ha-rules/README.md`
- **Story 6.3 (the trigger)**: `homelab-playbook/_bmad-output/implementation-artifacts/6-3-define-ha-groups.md` — esp. Dev Notes §"Idempotency at the `ha-manager` level" which acknowledges the reconcile-mode gap and points at this story for fix
- **Story 6.3 Dev Agent Record completion note 6**: documents the YAML `\\s` escaping gotcha that a reviewer of this story will likely encounter
- **Story 6.3 Dev Agent Record completion note 7**: documents the stanza-split parser pattern — direct prior art for AC-1's per-stanza walking
- **Memory: project_pve9_ha_rules_migration**: `/home/developer/.claude/projects/-home-developer-workspace-homelab/memory/project_pve9_ha_rules_migration.md` — authoritative `ha-manager rules set` syntax
- **Memory: project_project_container_ha_policy**: `/home/developer/.claude/projects/-home-developer-workspace-homelab/memory/project_project_container_ha_policy.md` — context for the `state_managed_by_operator` opt-out
- **PVE source**: `/usr/share/perl5/PVE/HA/Rules/NodeAffinity.pm` on each cluster node — authoritative field set
- **Proxmox HA docs**: <https://pve.proxmox.com/wiki/High_Availability>, `man ha-manager`
- **Existing reconcile-shape role precedent**: `homelab-infra/ansible/roles/pve-host-zfs-maintenance/` — same axis (drift detection on cluster-wide state)
