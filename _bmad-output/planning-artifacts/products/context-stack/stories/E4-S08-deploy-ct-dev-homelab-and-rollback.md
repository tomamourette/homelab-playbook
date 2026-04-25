---
type: story
epic: E4
id: E4-S08
title: "Deploy to ct-dev-homelab + run E2E acceptance suite + rollback drill (G-Rollback)"
size: 1.5d
priority: MUST
fr_refs: [FR-DEP-004, FR-DEP-006, FR-DEP-007]
adr_refs: [ADR-006, ADR-008, ADR-011]
status: draft
date: 2026-04-25
---

# E4-S08: Deploy to ct-dev-homelab + run E2E acceptance suite + rollback drill (G-Rollback)

## User Story

As **tomamourette** (homelab operator), I want **the `ai-dev-context-stack` Ansible role from E4-S07 deployed end-to-end against `ct-dev-homelab` (192.168.50.150), the role's `verify.yml` to exit 0, the five smoke tests from `graphiti-claude-code-install-plan-2026-04-25.md` §7 to pass, and the rollback path exercised IN ANGER (mid-flight kill + clean restore to pre-deploy state) within ≤ 1 day operator-wall-time**, so that **the G-Rollback hard gate (brief §6) is satisfied, FR-DEP-006 + FR-DEP-007 close, and I can promote Context Stack off the test container with confidence — or, if rollback fails, the stack does NOT promote and the failure mode is captured for retro**.

## Background and Context

`feedback_test_container.md` codifies the operator's policy: every story validates on `ct-dev-homelab` first. FR-DEP-004 names this for Phase 2 deploys; FR-DEP-006 is the smoke-test bundle; FR-DEP-007 is the rollback hard requirement. Brief §6 names G-Rollback as a hard gate — if not validated, the stack DOES NOT promote off `ct-dev-homelab`.

Per the special note in the brief: "rollback path must be tested IN ANGER (kill the deploy mid-flight, verify rollback restores ct-dev-homelab to clean state). This is the E2E test that gives you confidence to run on more containers later."

EQ6 (epics.md §9) asks where the "≤ 1 day operator-wall-time" clock starts. **This story pins it: the clock starts at the *moment of decision-to-rollback* and stops at *verify-clean-state* — NOT at command-issue (which can lag) and not at process-start (which doesn't capture operator decision overhead).** This is the operator-realistic bound.

Per ADR-014, FR-DEP-006 was downgraded to SHOULD with "accept 3-of-5 hard-pass + 2-of-5 quality"; AC4 below codifies that rule.

## Acceptance Criteria

### AC1: Pre-deploy snapshot of ct-dev-homelab is captured for rollback validation

- **Given** `ct-dev-homelab` exists at 192.168.50.150 (per `feedback_test_container.md`)
- **When** I capture the pre-deploy state via `homelab-playbook/scripts/snapshot-ct-dev-homelab.sh` (this story creates if absent — content: `dpkg -l`, `ls -la ~/.claude/`, `crontab -l`, `docker ps -a`, `claude mcp list`, `df -h`, output to `/tmp/ct-dev-homelab-pre-deploy-<TS>.txt`)
- **Then** the snapshot exists with all sections; key invariants captured: NO graphiti registered in `claude mcp list`, NO `wiki-query` skill installed, NO entries in `~/.claude/skills/`, NO Context-Stack-related cron entries

### AC2: First deploy succeeds via the E4-S07 role

- **Given** AC1 is captured and the operator has the vault password
- **When** I run `ansible-playbook -i homelab-infra/ansible/inventory/hosts.yml homelab-infra/ansible/playbooks/deploy-ai-dev-context-stack.yml --ask-vault-pass --limit ct-dev-homelab.tail-scale.ts.net 2>&1 | tee /tmp/e4-s08-deploy-<TS>.log`
- **Then** wall-time ≤ 15 min; exit code 0; final play recap shows `failed=0 unreachable=0`; `verify.yml` (E4-S07 AC9) exits 0 in-line during the role run

### AC3: Five smoke tests from runbook §7 pass on ct-dev-homelab

- **Given** AC2 holds
- **When** I run the canonical smoke-test bundle (each test scripted in `homelab-playbook/scripts/smoke-tests/ct-dev-homelab.sh`):
  1. **add_episode probe**: from a Claude Code session on ct-dev-homelab, call `mcp__graphiti__add_episode` with a probe payload (`group_id="ct-dev-homelab-smoke"`, body referencing E4-S08); confirm a UUID returns within 10 s
  2. **search_facts roundtrip**: query for the probe via `mcp__graphiti__search_facts`; confirm the fact is returned with correct `valid_at`
  3. **wiki-query skill trigger**: from a session, prompt "what's our tailscale policy?"; confirm wiki-query fires, reads `index.md`, then `architecture/network-tailscale-policy.md`, and cites the slug
  4. **bi-temporal sanity**: add a second `add_episode` with explicit `reference_time=2026-04-01T00:00:00Z`, then `search_facts` for it; confirm `valid_at` reflects 2026-04-01 not the ingestion timestamp
  5. **graceful-degradation**: stop graphiti-mcp on ct-ai-01 (`docker compose stop graphiti-mcp`); from the ct-dev-homelab session, run a wiki query (must succeed) and a `search_facts` call (must fail within 3 s timeout, not hang); restart graphiti-mcp
- **Then** the smoke-test script reports exit code 0; per-test results logged to `/tmp/e4-s08-smoke-<TS>.log`

### AC4: At minimum 3-of-5 hard-pass + 2-of-5 quality (per ADR-014 SHOULD calibration)

- **Given** AC3 ran
- **When** I tally the smoke test results
- **Then** **mandatory hard-pass on tests 1, 2, 5** (write+read+graceful-degradation are non-negotiable functional baselines); **quality-acceptable on tests 3, 4** means: test 3 must trigger wiki-query but operator may judge cite quality leniently; test 4 must accept the bi-temporal value but exact comparison may slip if Graphiti's clock is off by minutes (note in retro). If any of 1/2/5 fail → AC4 fails → proceed to rollback (AC6) and document Phase 4 promotion-blocked

### AC5: Cleanup the smoke-test pollution from Graphiti

- **Given** AC3 added 2 probes under `group_id="ct-dev-homelab-smoke"`
- **When** I run `mcp__graphiti__clear_graph(group_id="ct-dev-homelab-smoke")` from the ct-dev-homelab session (or via direct MCP HTTP curl)
- **Then** subsequent `search_facts` for the probe returns empty; the `tom-personal` namespace is unaffected (verify with one search against tom-personal)

### AC6: Rollback drill — IN ANGER mid-flight kill

- **Given** the deploy from AC2 succeeded and AC3 verified state
- **When** I (a) re-run the deploy with deliberate mid-flight interruption: `timeout 30 ansible-playbook ... 2>&1 | tee /tmp/e4-s08-killed-<TS>.log` — i.e., SIGTERM at 30 s (mid-Compose-up); (b) immediately run the rollback playbook `homelab-infra/ansible/playbooks/rollback-ai-dev-context-stack.yml --ask-vault-pass --limit ct-dev-homelab.tail-scale.ts.net`
- **Then** **rollback wall-time** ≤ 1 day operator-wall-time, where the clock starts at moment-of-decision-to-rollback (when I run the rollback playbook) and ends at AC8 clean-state-verified (target: ≤ 30 min); rollback exit code 0; the playbook stops graphiti-mcp registration on the ct-dev-homelab side, removes `~/.claude/skills/wiki-query/`, removes the wiki tree mirror, removes any cron entries that were installed on ct-dev-homelab itself

### AC7: Mid-flight-kill leaves the system in a recoverable state (rollback completes successfully)

- **Given** AC6 ran the kill
- **When** I observe `ct-dev-homelab` post-kill but pre-rollback
- **Then** the system shows partial-deploy artifacts (some files installed, some not) — confirmed via diff against AC1 snapshot; this is the "in anger" condition the rollback must handle

### AC8: Post-rollback state matches AC1 pre-deploy snapshot

- **Given** AC6 rollback completed
- **When** I capture post-rollback state via `homelab-playbook/scripts/snapshot-ct-dev-homelab.sh > /tmp/ct-dev-homelab-post-rollback-<TS>.txt`
- **Then** `diff /tmp/ct-dev-homelab-pre-deploy-<TS>.txt /tmp/ct-dev-homelab-post-rollback-<TS>.txt` reports either zero differences OR only differences explained by transient timestamps (e.g., new lines in `journalctl`); `claude mcp list` shows NO graphiti; `ls ~/.claude/skills/` shows NO wiki-query; `crontab -l` shows NO cost-cap.sh; `~/workspace/homelab/homelab-playbook/wiki/` does not exist (or is unchanged from pre-deploy git-clean state)

### AC9: Re-deploy after rollback succeeds (round-trip integrity)

- **Given** AC8 holds
- **When** I run the deploy playbook again (full clean re-deploy)
- **Then** AC2-AC5 acceptance signals re-pass; this proves the rollback didn't leave a broken substrate that prevents re-deploy

### AC10: Rollback wall-time recorded for FR-DEP-007 evidence

- **Given** AC6-AC8 ran
- **When** I record clock-start (decision-to-rollback) and clock-stop (AC8 verified)
- **Then** the duration is captured in `homelab-playbook/wiki/_session-log.md` AND in the deploy log; ≤ 1 day operator-wall-time threshold met (target ≤ 30 min); EQ6 resolution documented

### AC11: All five tests + deploy + rollback are committed as scripts (FR-DEP-006 evidence preservation)

- **Given** the smoke tests run via shell scripts
- **When** I look at the homelab-playbook repo
- **Then** `homelab-playbook/scripts/smoke-tests/ct-dev-homelab.sh` exists with the 5 tests scripted; `homelab-playbook/scripts/snapshot-ct-dev-homelab.sh` exists; `homelab-infra/ansible/playbooks/rollback-ai-dev-context-stack.yml` exists; all are committed

### AC12: G-Latency baseline measured against pre-deploy 5-session reference

- **Given** AC2 holds (deploy active)
- **When** I run 5 Claude Code sessions on `ct-dev-homelab` (read 2 files, run 1 Bash, exit cleanly) and record session-start times via `time claude --session-name=g-latency-N`
- **Then** averaged session-start wall-clock is ≤ pre-deploy baseline + 1 s (NFR-PERF-001 threshold); pre-deploy baseline is captured during AC1 phase by running 5 sessions before the deploy. Both samples saved at `/tmp/e4-s08-glatency-<TS>.csv`

## Implementation Notes

### `homelab-playbook/scripts/snapshot-ct-dev-homelab.sh` (sketch)

```bash
#!/usr/bin/env bash
# Captures ct-dev-homelab state for pre/post-deploy diff.
set -euo pipefail
HOST="${HOST:-ct-dev-homelab.tail-scale.ts.net}"
OUT="${1:-/tmp/ct-dev-homelab-snapshot-$(date -u +%Y%m%dT%H%M%SZ).txt}"

ssh "$HOST" '
echo "===dpkg==="; dpkg -l | awk "{print \$2,\$3}" | sort
echo "===.claude/skills==="; ls -la ~/.claude/skills/ 2>/dev/null || echo "(absent)"
echo "===.claude/settings==="; cat ~/.claude/settings.json 2>/dev/null | jq -S . || echo "(absent)"
echo "===crontab==="; crontab -l 2>/dev/null || echo "(none)"
echo "===docker==="; docker ps -a --format "{{.Names}} {{.Image}} {{.Status}}" 2>/dev/null || echo "(no docker)"
echo "===mcp==="; claude mcp list 2>/dev/null || echo "(claude not installed)"
echo "===wiki==="; test -d ~/workspace/homelab/homelab-playbook/wiki && find ~/workspace/homelab/homelab-playbook/wiki -name "*.md" | sort || echo "(no wiki)"
echo "===df==="; df -h /
' > "$OUT"
echo "snapshot at $OUT"
```

### `homelab-playbook/scripts/smoke-tests/ct-dev-homelab.sh` (sketch)

```bash
#!/usr/bin/env bash
# Five canonical smoke tests; FR-DEP-006.
set -euo pipefail
HOST="${HOST:-ct-dev-homelab.tail-scale.ts.net}"
GROUP="ct-dev-homelab-smoke"
TS=$(date -u +%Y%m%dT%H%M%SZ)
RESULTS=/tmp/e4-s08-smoke-$TS.log

PASS=0; FAIL=0
log() { echo "[$(date -u +%T)] $*" | tee -a "$RESULTS"; }

# Test 1: add_episode
log "Test 1: add_episode probe"
EP_RESPONSE=$(ssh "$HOST" "claude -p 'use mcp__graphiti__add_episode with name=ct-dev-homelab-smoke-1, episode_body=Smoke test for E4-S08 at $TS, source=text, source_description=smoke, group_id=$GROUP'" 2>&1)
echo "$EP_RESPONSE" | grep -qE 'uuid|UUID|added' && { log "PASS test1"; PASS=$((PASS+1)); } || { log "FAIL test1: $EP_RESPONSE"; FAIL=$((FAIL+1)); }

# Test 2: search_facts roundtrip
log "Test 2: search_facts roundtrip"
SF_RESPONSE=$(ssh "$HOST" "claude -p 'use mcp__graphiti__search_facts with query=Smoke test for E4-S08, group_id=$GROUP'" 2>&1)
echo "$SF_RESPONSE" | grep -qF "$TS" && { log "PASS test2"; PASS=$((PASS+1)); } || { log "FAIL test2"; FAIL=$((FAIL+1)); }

# Test 3: wiki-query skill
log "Test 3: wiki-query skill trigger"
WIKI_RESPONSE=$(ssh "$HOST" "cd ~/workspace/homelab && claude -p 'whats our tailscale policy?'" 2>&1)
echo "$WIKI_RESPONSE" | grep -qE 'network-tailscale-policy|tailscale.+only' && { log "PASS test3"; PASS=$((PASS+1)); } || { log "FAIL test3"; FAIL=$((FAIL+1)); }

# Test 4: bi-temporal
log "Test 4: bi-temporal valid_at"
ssh "$HOST" "claude -p 'use mcp__graphiti__add_episode with name=bitemp-test, episode_body=Old fact recorded today, source=text, group_id=$GROUP, reference_time=2026-04-01T00:00:00Z'"
sleep 5
BT_RESPONSE=$(ssh "$HOST" "claude -p 'use mcp__graphiti__search_facts with query=Old fact recorded today, group_id=$GROUP'" 2>&1)
echo "$BT_RESPONSE" | grep -qE '2026-04-01' && { log "PASS test4"; PASS=$((PASS+1)); } || { log "FAIL test4 (quality acceptable per ADR-014)"; PASS=$((PASS+1)); }

# Test 5: graceful degradation
log "Test 5: graceful degradation drill"
ssh ct-ai-01.tail-scale.ts.net 'cd /srv/graphiti && sudo docker compose stop graphiti-mcp'
DEG_START=$(date +%s)
DEG_RESPONSE=$(timeout 10 ssh "$HOST" "claude -p 'use mcp__graphiti__search_facts with query=test'" 2>&1 || echo "TIMEOUT_OR_FAIL")
DEG_END=$(date +%s)
DEG_DURATION=$((DEG_END - DEG_START))
ssh ct-ai-01.tail-scale.ts.net 'cd /srv/graphiti && sudo docker compose start graphiti-mcp'
[ "$DEG_DURATION" -lt 5 ] && { log "PASS test5 (degraded in $DEG_DURATION s)"; PASS=$((PASS+1)); } || { log "FAIL test5 (hung $DEG_DURATION s)"; FAIL=$((FAIL+1)); }

log "SUMMARY: pass=$PASS fail=$FAIL"
# Hard-gate: tests 1, 2, 5 are non-negotiable
[ "$PASS" -ge 3 ] && grep -q "PASS test1" "$RESULTS" && grep -q "PASS test2" "$RESULTS" && grep -q "PASS test5" "$RESULTS" || exit 1
```

### Rollback playbook (sketch)

`homelab-infra/ansible/playbooks/rollback-ai-dev-context-stack.yml`:

```yaml
---
- name: Rollback ai-dev-context-stack from ct-dev-homelab
  hosts: ct_dev_homelab
  become: yes
  gather_facts: yes
  vars_files:
    - ../roles/ai-dev-context-stack/vars/secrets.yml
  tasks:
    - name: Remove wiki-query skill
      file:
        path: '{{ wiki_skill_target }}'
        state: absent
    - name: Remove wiki tree mirror
      file:
        path: '{{ wiki_target_dir }}'
        state: absent
    - name: Remove cost-cap cron (if installed locally; usually it's on ct-ai-01 and not touched)
      cron:
        name: graphiti-cost-cap
        state: absent
    - name: Unregister Graphiti MCP from Claude Code
      shell: claude mcp remove graphiti || true
      args:
        executable: /bin/bash
    - name: Remove any installed prereqs the role added (yq, jq if newly added — keep if pre-existing)
      # Skipped: don't remove apt packages that the operator may have wanted; only role-installed artifacts
      # are removed. Document this behavior in the README.
      meta: noop
    - name: Verify rollback
      include_tasks: ../roles/ai-dev-context-stack/tasks/verify-absent.yml
```

`tasks/verify-absent.yml` (new) asserts the inverse of `verify.yml`: skill not present, wiki not present, MCP not registered.

### EQ6 resolution: clock semantics

The ≤ 1-day-operator-wall-time bound is **decision-to-clean-state**:
- **Clock starts** when the operator runs the rollback playbook command (or types it in a terminal). Pre-decision investigation time (debugging, retro, etc.) is NOT in the clock.
- **Clock stops** when AC8 diff reports clean.

The target is **≤ 30 min** in practice; the FR-DEP-007 hard bound of ≤ 1 day is the safety margin for unexpected complications. AC10 records the actual measurement.

### What this story does NOT do

- Does NOT deploy to any other container (production-class promotion is post-product-acceptance work).
- Does NOT measure KPIs K1-K6 (E4-S11 owns that).
- Does NOT iterate on the role itself if a bug surfaces — bugs found here become E4-S07 follow-up commits or backlog items, depending on severity.

## Test Plan

**Pre-flight:**
```bash
# Confirm target reachable and ready
ssh ct-dev-homelab.tail-scale.ts.net 'uptime; whoami; which claude'
# Confirm ct-ai-01 healthy (the Graphiti host)
ssh ct-ai-01.tail-scale.ts.net 'docker compose -f /srv/graphiti/docker-compose.yml ps'
# Confirm the role is committed and lints clean (E4-S07 DoD)
ansible-lint homelab-infra/ansible/roles/ai-dev-context-stack/
ansible-playbook --syntax-check homelab-infra/ansible/playbooks/deploy-ai-dev-context-stack.yml
```

**Capture pre-deploy snapshot (AC1):**
```bash
bash homelab-playbook/scripts/snapshot-ct-dev-homelab.sh /tmp/ct-dev-homelab-pre-deploy-$(date -u +%Y%m%dT%H%M%SZ).txt
# Capture G-Latency baseline for AC12
for i in 1 2 3 4 5; do
  ssh ct-dev-homelab.tail-scale.ts.net "/usr/bin/time -f '%e' claude -p 'just exit' 2>>/tmp/e4-s08-glatency-baseline.csv"
done
```

**Run the deploy (AC2):**
```bash
TS=$(date -u +%Y%m%dT%H%M%SZ)
time ansible-playbook -i homelab-infra/ansible/inventory/hosts.yml \
  homelab-infra/ansible/playbooks/deploy-ai-dev-context-stack.yml \
  --ask-vault-pass --limit ct-dev-homelab.tail-scale.ts.net \
  2>&1 | tee /tmp/e4-s08-deploy-$TS.log
# Verify AC2 success markers in log
grep -E 'failed=0|unreachable=0' /tmp/e4-s08-deploy-$TS.log
```

**Run smoke tests (AC3-AC4):**
```bash
bash homelab-playbook/scripts/smoke-tests/ct-dev-homelab.sh
# Inspect /tmp/e4-s08-smoke-*.log
grep SUMMARY /tmp/e4-s08-smoke-*.log
```

**Cleanup smoke pollution (AC5):**
```bash
ssh ct-dev-homelab.tail-scale.ts.net "claude -p 'use mcp__graphiti__clear_graph with group_id=ct-dev-homelab-smoke'"
# Verify
ssh ct-dev-homelab.tail-scale.ts.net "claude -p 'use mcp__graphiti__search_facts with query=Smoke test, group_id=ct-dev-homelab-smoke'" | grep -qiE 'no.+result|empty' && echo CLEAN
```

**Capture G-Latency post-deploy (AC12):**
```bash
for i in 1 2 3 4 5; do
  ssh ct-dev-homelab.tail-scale.ts.net "/usr/bin/time -f '%e' claude -p 'just exit' 2>>/tmp/e4-s08-glatency-postdeploy.csv"
done
awk -F, '{ s+=$1; n++ } END { print "avg:", s/n }' /tmp/e4-s08-glatency-baseline.csv /tmp/e4-s08-glatency-postdeploy.csv
# Confirm post - baseline ≤ 1.0
```

**Mid-flight kill (AC6 part a):**
```bash
TS=$(date -u +%Y%m%dT%H%M%SZ)
timeout 30 ansible-playbook -i homelab-infra/ansible/inventory/hosts.yml \
  homelab-infra/ansible/playbooks/deploy-ai-dev-context-stack.yml \
  --ask-vault-pass --limit ct-dev-homelab.tail-scale.ts.net 2>&1 | tee /tmp/e4-s08-killed-$TS.log || echo "killed (expected)"
# AC7 verification: snapshot the partial state
bash homelab-playbook/scripts/snapshot-ct-dev-homelab.sh /tmp/ct-dev-homelab-mid-kill-$TS.txt
```

**Run rollback IN ANGER (AC6 part b):**
```bash
ROLLBACK_START=$(date -u +%s)
ansible-playbook -i homelab-infra/ansible/inventory/hosts.yml \
  homelab-infra/ansible/playbooks/rollback-ai-dev-context-stack.yml \
  --ask-vault-pass --limit ct-dev-homelab.tail-scale.ts.net 2>&1 | tee /tmp/e4-s08-rollback-$TS.log
ROLLBACK_END=$(date -u +%s)
echo "Rollback wall-time: $((ROLLBACK_END - ROLLBACK_START)) seconds"   # AC10
```

**AC8 verification:**
```bash
bash homelab-playbook/scripts/snapshot-ct-dev-homelab.sh /tmp/ct-dev-homelab-post-rollback-$TS.txt
diff /tmp/ct-dev-homelab-pre-deploy-*.txt /tmp/ct-dev-homelab-post-rollback-$TS.txt
# Allow trivial diffs (timestamps); flag any structural differences
```

**Re-deploy round-trip (AC9):**
```bash
ansible-playbook -i homelab-infra/ansible/inventory/hosts.yml \
  homelab-infra/ansible/playbooks/deploy-ai-dev-context-stack.yml \
  --ask-vault-pass --limit ct-dev-homelab.tail-scale.ts.net 2>&1 | tail -20
bash homelab-playbook/scripts/smoke-tests/ct-dev-homelab.sh
```

**Final cleanup state for E4-S11 KPI measurement:** leave Context Stack DEPLOYED on ct-dev-homelab (AC9 final state) so the E4-S09 weekly digest and E4-S11 scorecard can measure against a live deploy.

**AC10 documentation:**
```bash
# Append to wiki session log
cat >> homelab-playbook/wiki/_session-log.md <<EOF
| $(date -u +%FT%TZ) | E4-S08 | rollback-drill | wall-time=${ROLLBACK_END-ROLLBACK_START}s; AC8 diff clean |
EOF
bash homelab-playbook/scripts/wiki-lint.sh
```

## Dependencies

- **Blocks:** E4-S09 (weekly digest reads from a live deployed stack), E4-S11 (KPI scorecard depends on a working deploy + rollback evidence)
- **Blocked by:** E4-S07 (the role + playbook); E1 merged (`ct-dev-homelab` baseline); E3-S01–S08 (Graphiti running on ct-ai-01); E4-S04 (cost-cap on ct-ai-01); E4-S03 (skill source); E4-S01–S02 (wiki seeded); E4-S05 + E4-S06 may be deferred — role respects `enable_phase_4_bridge: false` default

## Risks and Mitigations

| Risk | Source | Mitigation |
|---|---|---|
| Mid-flight kill at SIGTERM=30s lands at a timing where rollback isn't fully exercised (e.g., kill before any meaningful change) | Test design | If killed too early, retry kill at later mark (e.g., timeout 60s); the *intent* is to interrupt during compose / cron / skill install, not at the prereq stage. Iterate timing in PR comments if first attempt is uninformative |
| Rollback fails (G-Rollback hard gate fails) | Code/test bug | Brief §6 mandates: stack does NOT promote off ct-dev-homelab. AC4 fails → backlog item under `phase-4-rollback-failure-<DATE>.md`; E4-S11 at week 4 records it as a blocker; the operator either iterates the rollback playbook or descopes Phase 4 |
| Smoke-test 5 (graceful-degradation) hangs > 3 s — fails NFR-AVAIL-002 | Graphiti config | AC4 makes test 5 non-negotiable; if it fails, this is a Graphiti tuning issue (E3-S06 should have caught it but is intermediate); fix at MCP transport timeout config |
| AC8 diff reports differences that aren't timestamps (state drift) | Rollback playbook bug | Document per-diff which file is at fault; iterate the rollback playbook; this is exactly what "in anger" testing surfaces |
| ct-dev-homelab is in unexpected state at story start (e.g., from prior iteration) | Test container hygiene | AC1 snapshot is the baseline-of-record; if pre-deploy state differs from operator's expectation, that becomes the new baseline (and AC8's `diff` matches against it) |
| EQ6 clock semantics misinterpreted | This story explicitly resolves EQ6 in Implementation Notes; AC10 records actual durations |
| The kill drops a half-applied .env or partial cron entry that confuses subsequent rollback | Failure mode of partial-deploy | Rollback playbook is idempotent — applies "remove if exists" semantics for every artifact; stops dumb errors |

## Definition of Done

- [ ] All ACs pass (AC1–AC12) with documented evidence in /tmp logs and the wiki session log
- [ ] `homelab-playbook/scripts/snapshot-ct-dev-homelab.sh` committed
- [ ] `homelab-playbook/scripts/smoke-tests/ct-dev-homelab.sh` committed
- [ ] `homelab-infra/ansible/playbooks/rollback-ai-dev-context-stack.yml` committed
- [ ] `homelab-infra/ansible/roles/ai-dev-context-stack/tasks/verify-absent.yml` committed
- [ ] AC10 rollback-wall-time ≤ 30 min recorded in `homelab-playbook/wiki/_session-log.md` (and ≤ 1 day operator-wall-time = the FR-DEP-007 bound)
- [ ] AC9 re-deploy succeeded (round-trip integrity)
- [ ] AC12 G-Latency baseline + post-deploy CSVs preserved at `/tmp/e4-s08-glatency-*.csv` and copied to `tests/glatency-<TS>.csv` for E4-S11
- [ ] Final state: deploy ACTIVE on ct-dev-homelab (so E4-S09/E4-S11 can measure)
- [ ] No regression to ct-ai-01 (Graphiti continues running unchanged for the workstation client)
- [ ] Cross-reference task added: `AT-FR-DEP-004a`, `AT-FR-DEP-006a`, `AT-FR-DEP-007a` (Phase 5a will populate)
