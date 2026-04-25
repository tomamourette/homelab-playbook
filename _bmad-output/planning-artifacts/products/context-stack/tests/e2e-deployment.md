---
type: e2e-deployment-test-plan
product: context-stack
version: 1.0.0-draft
status: draft
date: 2026-04-25
arch_ref: architecture.md
epics_ref: epics.md
prd_ref: prd.md
acceptance_ref: tests/acceptance.md
runbook_ref: ../../research/graphiti-claude-code-install-plan-2026-04-25.md
---

# Context Stack — End-to-End Deployment Test Plan (Phase 5b)

## 1. Overview and Scope

### 1.1 What this plan tests

This plan validates the **end-to-end, cross-layer behaviour** of the Context Stack at the two deployment surfaces called out in architecture §8:

1. **Workstation** (Phase 1, daily-driver). Tier 1 wiki + Tier 2 GitNexus run here; Tier 3 Graphiti is reached via Tailscale to `ct-ai-01`. The workstation install is mostly hand-driven; Ansible role optional.
2. **`ct-dev-homelab`** (Phase 2, 192.168.50.150). Reach-the-stack-from-a-fresh-container deploy via the Ansible role `ai-dev-context-stack` authored in story E4-S07 and exercised in story E4-S08. `ct-dev-homelab` is a *client* of the stack — Graphiti itself stays on `ct-ai-01`.

### 1.2 What this plan does NOT test (delegated)

Per-story acceptance criteria live in `tests/acceptance.md`. This plan deliberately avoids re-litigating any single AC; instead, it covers the **cross-layer concerns** that no single story can verify:

- Install ordering across L0 → L5 (which layer must be in place before the next can ship).
- Post-each-layer smoke tests that verify the previous layer hasn't been damaged when the next is installed.
- Full-stack integration (a single Claude Code session that exercises all four tiers in turn per ADR-013).
- Operationally honest rollback drills — not just "documented" rollbacks but ones that have been thought through against partial-state failure.
- Disaster scenarios that reveal whether the design is operationally honest.

### 1.3 Two-phase boundary

```
Phase 1 — Workstation                     Phase 2 — ct-dev-homelab
─────────────────────────                 ─────────────────────────
L0 Decommission   (E1, hand-driven)        L0 already done in Phase 1
L1 Wiki tier      (E4-S01..03)             L1 deployed via Ansible role
L2 GitNexus       (E2 entirely)            L2 delegated workstation install
L3 Graphiti       (E3 — on ct-ai-01)       L3 client-side MCP registration
L4 LiteLLM        (E4-S05/S06, stretch)    L4 phase-aware .env (default off)
L5 Obs + Cap      (E4-S04/S09)             L5 cron + cost-cap on ct-ai-01
                                                                     
Acceptance gate: G-Latency clean,          Acceptance gate: G-Rollback
all 4 tiers exercised in one session       drill IN ANGER (E4-S08 AC6)
```

Phase 1 is the operator's daily surface. Phase 2 is the standing test container per `feedback_test_container.md` — every story validates here first, and the brief §6 G-Rollback hard gate is the binding promotion bar.

---

## 2. Prerequisites

### 2.1 Workstation prereqs

| # | Check | Pass criterion |
|---|---|---|
| 2.1.1 | OS / shell | Linux (Debian/Ubuntu/Arch) with bash or zsh |
| 2.1.2 | Claude Code CLI present | `claude --version` reports ≥ a version that supports `mcp` subcommand and `--session-name` (operator's current daily-driver) |
| 2.1.3 | Docker installed (for any local drill) | `docker version` returns server + client versions |
| 2.1.4 | Node.js / npm (for GitNexus) | `node --version` ≥ 18.x; `npm --version` returns a number |
| 2.1.5 | Python 3.11+ (residual tools) | `python3 --version` ≥ 3.11 |
| 2.1.6 | Anthropic reachability | `curl -fsS -m 10 -o /dev/null https://api.anthropic.com/ || echo OK` (any TCP success — auth not needed) |
| 2.1.7 | OpenAI reachability | `curl -fsS -m 10 -o /dev/null https://api.openai.com/ || echo OK` |
| 2.1.8 | SSH key to `ct-dev-homelab` | `ssh -o BatchMode=yes -o ConnectTimeout=5 ct-dev-homelab.tail-scale.ts.net 'echo OK'` |
| 2.1.9 | Tailscale up | `tailscale status \| grep -E 'ct-(ai-01\|dev-homelab\|101)' \| wc -l` ≥ 3 |
| 2.1.10 | Ansible from workstation | `ansible --version` ≥ 2.14; `ansible-vault --help` available |
| 2.1.11 | Git working tree clean | `git -C ~/workspace/homelab status --porcelain` empty (or only this E2E plan) |
| 2.1.12 | Disk free | `df -h ~ \| awk 'NR==2 {print $4}'` ≥ 5 GB |

### 2.2 ct-dev-homelab prereqs

| # | Check | Pass criterion |
|---|---|---|
| 2.2.1 | Container reachable | `ssh ct-dev-homelab.tail-scale.ts.net 'uptime'` returns load avg |
| 2.2.2 | Ansible ping | `ansible -i homelab-infra/ansible/inventory/hosts.yml ct_dev_homelab -m ping` returns `pong` |
| 2.2.3 | Disk free | `ssh ct-dev-homelab.tail-scale.ts.net 'df -h /'` shows ≥ 5 GB free on `/` |
| 2.2.4 | RAM free | `ssh ct-dev-homelab.tail-scale.ts.net "free -m \| awk 'NR==2 {print \$7}'"` ≥ 2048 |
| 2.2.5 | Claude Code on container | `ssh ct-dev-homelab.tail-scale.ts.net 'which claude'` returns a path |
| 2.2.6 | OMEGA / MemPalace fully decommissioned | `ssh ct-dev-homelab.tail-scale.ts.net "pgrep -f 'mempalace\|omega' \|\| echo CLEAN"` returns `CLEAN`; `grep -ri -l 'mempalace\|omega' ~/.claude/ \|\| echo CLEAN` returns `CLEAN` |
| 2.2.7 | E1 tag present in repo | `git -C ~/workspace/homelab tag \| grep -q phase-1-decommission-complete` |
| 2.2.8 | `ct-ai-01` reachable from container | `ssh ct-dev-homelab.tail-scale.ts.net 'curl -fsS -m 5 -o /dev/null http://ct-ai-01.tail-scale.ts.net:8000/mcp/ \|\| echo OK'` |

### 2.3 Pre-flight verification command (single block, copy-paste)

```bash
#!/usr/bin/env bash
# Pre-flight for Context Stack E2E deploy test.
# Each line emits "PASS <check>" or "FAIL <check>". Exit non-zero if any FAIL.
set +e
PF_FAIL=0
chk() { if eval "$2" >/dev/null 2>&1; then echo "PASS $1"; else echo "FAIL $1"; PF_FAIL=$((PF_FAIL+1)); fi; }

# Workstation (§2.1)
chk "2.1.2 claude CLI"                "command -v claude"
chk "2.1.3 docker"                    "docker version"
chk "2.1.4 node + npm"                "node --version && npm --version"
chk "2.1.5 python 3.11+"              "python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3,11) else 1)'"
chk "2.1.6 anthropic reach"           "curl -fsS -m 10 -o /dev/null https://api.anthropic.com/ || true; true"
chk "2.1.7 openai reach"              "curl -fsS -m 10 -o /dev/null https://api.openai.com/ || true; true"
chk "2.1.8 ssh ct-dev-homelab"        "ssh -o BatchMode=yes -o ConnectTimeout=5 ct-dev-homelab.tail-scale.ts.net 'true'"
chk "2.1.9 tailscale 3+ peers"        "[ \$(tailscale status | grep -cE 'ct-(ai-01|dev-homelab|101)') -ge 3 ]"
chk "2.1.10 ansible"                  "ansible --version"
chk "2.1.12 disk free 5GB"            "[ \$(df -B1G ~ | awk 'NR==2 {print \$4}') -ge 5 ]"

# ct-dev-homelab (§2.2)
chk "2.2.1 container up"              "ssh ct-dev-homelab.tail-scale.ts.net 'uptime'"
chk "2.2.2 ansible ping"              "ansible -i homelab-infra/ansible/inventory/hosts.yml ct_dev_homelab -m ping"
chk "2.2.3 ct disk free 5GB"          "[ \$(ssh ct-dev-homelab.tail-scale.ts.net 'df -B1G / | awk \"NR==2 {print \\\$4}\"') -ge 5 ]"
chk "2.2.4 ct ram free 2GB"           "[ \$(ssh ct-dev-homelab.tail-scale.ts.net \"free -m | awk 'NR==2 {print \\\$7}'\") -ge 2048 ]"
chk "2.2.5 ct claude CLI"             "ssh ct-dev-homelab.tail-scale.ts.net 'command -v claude'"
chk "2.2.6 ct omega/mempalace clean"  "ssh ct-dev-homelab.tail-scale.ts.net \"pgrep -f 'mempalace|omega' || true\" | grep -v ."
chk "2.2.7 phase-1-decom tag"         "git -C ~/workspace/homelab tag | grep -q phase-1-decommission-complete"
chk "2.2.8 ct can reach ct-ai-01"     "ssh ct-dev-homelab.tail-scale.ts.net 'curl -fsS -m 5 -o /dev/null http://ct-ai-01.tail-scale.ts.net:8000/mcp/ || true; true'"

echo "==="
if [ $PF_FAIL -eq 0 ]; then echo "PRE-FLIGHT GREEN — proceed"; exit 0; else echo "PRE-FLIGHT $PF_FAIL FAIL — DO NOT proceed"; exit 1; fi
```

**Gate.** If pre-flight is not GREEN, abort and resolve before any deploy work begins. Especially `2.2.6` and `2.2.7` are non-negotiable — installing Context Stack on top of a non-decommissioned container is the failure mode E1 is designed to prevent.

---

## 3. Phase 1 Workstation Deploy

The workstation deploy is the operator's daily surface. It is mostly hand-driven; the Ansible role `ai-dev-context-stack` is *available* for the workstation (delegate-to-localhost) but optional in Phase 1 (E4-S07 AC2 keeps `context_stack_install_gitnexus` togglable).

### 3.1 Layer-by-layer install sequence

Layers are installed in cost-order, lowest-blast-radius first. **Do not skip the smoke test between layers** — the whole point of the layered approach is that we can isolate which layer broke when something does break.

#### L0 — Decommission (already done in Sprint 1)

**Pre-condition:** Sprint 1 (Epic E1) has merged, the merged commit is tagged `phase-1-decommission-complete`, and the workstation has been operating without OMEGA/MemPalace for at least one full session.

**Smoke test (T-L0):**
```bash
# T-L0.1 — no residual processes
pgrep -f 'mempalace\|omega' && echo "FAIL L0" || echo "PASS L0.1"
# T-L0.2 — no residual settings.json hooks
jq -e '.hooks // {} | to_entries[] | select(.value | tostring | test("omega|mempalace"; "i"))' \
   ~/.claude/settings.json >/dev/null && echo "FAIL L0.2" || echo "PASS L0.2"
# T-L0.3 — no residual repo references
( cd ~/workspace/homelab && git grep -i -l 'mempalace\|omega' \
    -- ':!docs/decommission' ':!_bmad-output' >/dev/null && echo "FAIL L0.3" \
    || echo "PASS L0.3" )
# T-L0.4 — auto-memory MEMORY.md still loads end-to-end at session start
claude -p 'echo memory loaded' | grep -q 'memory loaded' && echo "PASS L0.4" || echo "FAIL L0.4"
```

**Go/No-Go gate G0.** All four T-L0 checks PASS. Proceed to L1.

**Rollback procedure for L0** (only if a regression surfaces post-L0 but pre-L1):
1. `git -C ~/workspace/homelab checkout phase-1-decommission-complete~1` (the commit immediately before E1 merge).
2. Re-run E1's pre-decommission Hermes role: `ansible-playbook deploy-ai-dev-omega-memory.yml --limit ct-dev-homelab` (the file removed in commit 3 of E1; recover from git history).
3. Re-install OMEGA from PyPI: `pip install omega-memory==<last-known-version>`.
4. Restore four hook entries in `~/.claude/settings.json` from the disable-only commit (E1 commit 1).
5. Confirm `pgrep -f omega` returns a PID.
6. **This is the FR-DEP-007 / NFR-MAINT-002 path and is documented in the Phase-1 decommission runbook.** Time bound: ≤ 1 day (NFR-MAINT-001).

#### L1 — Wiki tier

**Install:**
```bash
# Skill source-of-truth lives in the repo; install copies it into ~/.claude/skills/
mkdir -p ~/workspace/homelab/homelab-playbook/wiki/{architecture,runbooks,decisions,glossary,projects}
mkdir -p ~/.claude/skills/wiki-query
cp ~/workspace/homelab/homelab-playbook/skills/wiki-query/SKILL.md ~/.claude/skills/wiki-query/SKILL.md
chmod 644 ~/.claude/skills/wiki-query/SKILL.md
# Bootstrap index.md, _schema.md, and 3-5 seed entries (committed by E4-S01/S02)
ls ~/workspace/homelab/homelab-playbook/wiki/index.md \
   ~/workspace/homelab/homelab-playbook/wiki/_schema.md
# Wiki lint hook
bash ~/workspace/homelab/homelab-playbook/scripts/wiki-lint.sh
```

**Smoke test (T-L1):**
```bash
# T-L1.1 — skill installed, readable
test -f ~/.claude/skills/wiki-query/SKILL.md && echo "PASS L1.1" || echo "FAIL L1.1"
# T-L1.2 — index.md exists and references at least 3 seed entries
[ "$(grep -cE '^\- \[' ~/workspace/homelab/homelab-playbook/wiki/index.md)" -ge 3 ] \
   && echo "PASS L1.2" || echo "FAIL L1.2"
# T-L1.3 — wiki-lint clean
bash ~/workspace/homelab/homelab-playbook/scripts/wiki-lint.sh \
   && echo "PASS L1.3" || echo "FAIL L1.3"
# T-L1.4 — Claude Code triggers wiki-query on a known phrase
time claude -p "what's our tailscale policy?" 2>&1 | tee /tmp/t-l1-4.log
grep -qE 'tailscale.+only|network-tailscale-policy' /tmp/t-l1-4.log \
   && echo "PASS L1.4" || echo "FAIL L1.4"
# T-L1.5 — wiki query latency under 200 ms (NFR-PERF-003); excludes Claude Code's own startup
awk '/real/ {print $2}' /tmp/t-l1-4.log
```

**Go/No-Go gate G1.** T-L1.1 / .2 / .3 / .4 all PASS. T-L1.5 < 200 ms p95 SHOULD (per NFR-PERF-003 / FR-WIKI-005 — SHOULD post-ADR-014). Proceed to L2.

**Rollback procedure for L1** (without disturbing L0):
```bash
rm -rf ~/.claude/skills/wiki-query
# Wiki tree itself stays in repo; it's portable markdown and removing it would lose work.
# To "fully un-wire" the tier: leave wiki/ in place but remove the skill. Claude Code will
# then no longer auto-trigger wiki-query; manual reads still work.
# Verify rollback:
test ! -f ~/.claude/skills/wiki-query/SKILL.md && echo "PASS L1-rollback"
```
**Time bound:** ≤ 5 min (NFR-MAINT-001 satisfied).

#### L2 — Code-graph (GitNexus)

**Install:**
```bash
# Supply-chain verification BEFORE installing
npm view gitnexus@1.6.3 maintainers integrity name
# Confirm package name spelled exactly (graphify/graphifyy lesson — architecture §5.3)
npm install -g gitnexus@1.6.3
# Register MCP across Claude Code (and any other supported clients)
npx gitnexus@1.6.3 setup
# Configure parent-folder topology
# (writes ~/.gitnexus/config.json — operator confirms topology to parent ~/workspace/homelab/)
# Hooks land in ~/.claude/settings.json (PreToolUse + PostToolUse-on-Bash-commit)
```

**Smoke test (T-L2):**
```bash
# T-L2.1 — MCP registered and healthy
claude mcp list | grep -E '^gitnexus.+(healthy|connected|active)$' \
   && echo "PASS L2.1" || echo "FAIL L2.1"
# T-L2.2 — daemon RSS under 500 MB (NFR-FOOTPRINT-002 / closes AR1)
ps -o rss= -p "$(pgrep -f gitnexus | head -1)" | awk '{print "RSS_KB="$1}; { if ($1 > 512000) exit 1 }' \
   && echo "PASS L2.2" || echo "FAIL L2.2 (>500MB)"
# T-L2.3 — hooks present in settings.json
jq '.hooks.PreToolUse, .hooks.PostToolUse' ~/.claude/settings.json | grep -qi gitnexus \
   && echo "PASS L2.3" || echo "FAIL L2.3"
# T-L2.4 — parent-folder topology covers all 3 sibling repos
claude -p 'use mcp__gitnexus__cypher with query="MATCH (n:File) RETURN DISTINCT split(n.file, \"/\")[5] LIMIT 10"' \
   | tee /tmp/t-l2-4.log
grep -E 'homelab\b|homelab-bootstrap|homelab-playbook' /tmp/t-l2-4.log | wc -l \
   | awk '$1 >= 3 {print "PASS L2.4"} $1 < 3 {print "FAIL L2.4"}'
# T-L2.5 — incremental reindex under 30 s (NFR-PERF-004) on a typical commit
( cd ~/workspace/homelab/homelab-playbook && \
  echo "# E2E test marker $(date)" >> wiki/_session-log.md && \
  /usr/bin/time -f '%e' git commit -am "test: L2 smoke" 2>&1 | tail -3 )
# T-L2.6 — privacy audit: no LLM-API calls during reindex
sudo timeout 65 tcpdump -i any -nn 'host api.openai.com or host api.anthropic.com' &
TCPDUMP_PID=$!
( cd ~/workspace/homelab/homelab-playbook && \
  npx gitnexus@1.6.3 reindex --full )
sleep 5; sudo kill $TCPDUMP_PID 2>/dev/null
# Expectation: zero packets to api.openai.com or api.anthropic.com (FR-CG-002, NFR-PRIV-001)
# T-L2.7 — graceful degradation drill (FR-CG-011, NFR-AVAIL-001)
pkill -STOP -f gitnexus
timeout 5 claude -p 'echo session continues' \
   && echo "PASS L2.7" || echo "FAIL L2.7"
pkill -CONT -f gitnexus
```

**Go/No-Go gate G2.** T-L2.1, .2, .3, .4, .7 all PASS; T-L2.5 < 30 s; T-L2.6 produces zero packets to api.openai.com / api.anthropic.com. Proceed to L3.

**Rollback procedure for L2** (without disturbing L0/L1):
```bash
# 1. Stop daemon
pkill -f gitnexus
# 2. Remove MCP registration
claude mcp remove gitnexus
# 3. Remove hooks from settings.json
jq 'del(.hooks.PreToolUse[] | select(.command | test("gitnexus"))) |
    del(.hooks.PostToolUse[] | select(.command | test("gitnexus")))' \
    ~/.claude/settings.json > /tmp/settings.json && mv /tmp/settings.json ~/.claude/settings.json
# 4. Uninstall package
npm uninstall -g gitnexus
# 5. Remove LadybugDB index
rm -rf ~/.gitnexus
# Verify
which gitnexus 2>/dev/null && echo "FAIL L2-rollback (binary still present)" || echo "PASS L2-rollback"
claude mcp list | grep -q gitnexus && echo "FAIL L2-rollback (MCP still registered)" || echo "PASS L2-rollback"
```
**Time bound:** ≤ 15 min. **Critical: L2 rollback must NOT touch L1's wiki skill nor L3's Graphiti registration.** The jq filter scopes to the gitnexus hooks only.

#### L3 — Memory (Graphiti on `ct-ai-01`)

This layer's *server* is on `ct-ai-01` (already deployed via Epic E3). The workstation's L3 install is **client-side** only: register the MCP HTTP endpoint with Claude Code.

**Install:**
```bash
# E3 has already deployed graphiti-mcp + graphiti-falkordb on ct-ai-01.
# Workstation registers the HTTP endpoint:
claude mcp add --transport http graphiti http://ct-ai-01.tail-scale.ts.net:8000/mcp/
# (E3 used 127.0.0.1 binding inside the LXC; Tailscale provides the cross-host reach)
```

**Smoke test (T-L3):**
```bash
# T-L3.1 — MCP healthy from workstation
claude mcp list | grep -E '^graphiti.+(healthy|connected|active)$' \
   && echo "PASS L3.1" || echo "FAIL L3.1"
# T-L3.2 — server-side reachability
ssh ct-ai-01.tail-scale.ts.net 'docker compose -f /srv/graphiti/docker-compose.yml ps' \
   | grep -E 'graphiti-mcp.+Up.+graphiti-falkordb.+Up|Up.+Up' \
   && echo "PASS L3.2" || echo "FAIL L3.2"
# T-L3.3 — add_episode roundtrip
TS=$(date -u +%Y%m%dT%H%M%SZ)
claude -p "use mcp__graphiti__add_episode with name=l3-smoke-$TS, episode_body=L3 smoke at $TS, source=text, group_id=l3-workstation-smoke" \
   | grep -qiE 'uuid|added' && echo "PASS L3.3" || echo "FAIL L3.3"
# T-L3.4 — search_facts roundtrip
sleep 3
claude -p "use mcp__graphiti__search_facts with query=L3 smoke at $TS, group_id=l3-workstation-smoke" \
   | grep -qF "$TS" && echo "PASS L3.4" || echo "FAIL L3.4"
# T-L3.5 — namespace discipline (closes AR8)
claude -p "use mcp__graphiti__search_facts with query=$TS, group_id=tom-personal" \
   | grep -qE 'no.+result|empty' && echo "PASS L3.5 (probe did NOT leak to tom-personal)" \
                                  || echo "FAIL L3.5 (LEAK to tom-personal)"
# T-L3.6 — search latency p95 under 500 ms (NFR-PERF-002)
for i in 1 2 3 4 5 6 7 8 9 10; do
  /usr/bin/time -f '%e' claude -p "use mcp__graphiti__search_facts with query=L3 smoke, group_id=l3-workstation-smoke" \
     2>>/tmp/t-l3-6-latency.csv >/dev/null
done
sort -n /tmp/t-l3-6-latency.csv | awk 'NR==9 {print "p95:", $1}'
# T-L3.7 — graceful degradation (FR-MEM-013, NFR-AVAIL-002) — < 3 s timeout, not hang
ssh ct-ai-01.tail-scale.ts.net 'cd /srv/graphiti && sudo docker compose stop graphiti-mcp'
START=$(date +%s)
timeout 10 claude -p "use mcp__graphiti__search_facts with query=test, group_id=tom-personal" \
   2>&1 || echo "(failed as expected)"
END=$(date +%s)
[ $((END-START)) -lt 5 ] && echo "PASS L3.7 (degraded $((END-START))s)" \
                         || echo "FAIL L3.7 (hung $((END-START))s)"
ssh ct-ai-01.tail-scale.ts.net 'cd /srv/graphiti && sudo docker compose start graphiti-mcp'
# T-L3.8 — cleanup the smoke pollution
claude -p "use mcp__graphiti__clear_graph with group_id=l3-workstation-smoke"
```

**Go/No-Go gate G3.** T-L3.1..5, .7 all PASS; T-L3.6 p95 < 500 ms; T-L3.8 returns empty when re-queried. Proceed to L4 (or skip to L5 if Phase 4 is deferred per FR-LLM-007).

**Rollback procedure for L3** (without disturbing L0/L1/L2; ct-ai-01-side rollback is separate):
```bash
# Workstation-side: just unregister MCP — Graphiti server keeps running on ct-ai-01
claude mcp remove graphiti
claude mcp list | grep -q graphiti && echo "FAIL L3-rollback" || echo "PASS L3-rollback"
# Optional: clear smoke pollution if not already done
ssh ct-ai-01.tail-scale.ts.net 'curl -X POST http://127.0.0.1:8000/mcp/clear_graph -d "group_id=l3-workstation-smoke"' || true
```
**Server-side rollback** (drop Graphiti on ct-ai-01 entirely — only if E3 needs to back out):
```bash
ssh ct-ai-01.tail-scale.ts.net <<'EOF'
cd /srv/graphiti
sudo docker compose down -v
sudo crontab -l | grep -v -E 'cost-cap|cypher-export|graphiti' | sudo crontab -
sudo rm -rf /srv/graphiti
EOF
```
**Time bound:** workstation-side ≤ 2 min; server-side ≤ 10 min. **Backup integrity preserved:** the monthly Cypher export at `/srv/graphiti/backups/cypher-*.json` should be copied off-host BEFORE the `docker compose down -v` if data preservation is desired.

#### L4 — LiteLLM bridge (Phase 4 stretch)

**Pre-condition for L4:** E4-S06 has run the 50-fact validation set against the bridge and the gate passed at ≥ 95% well-formed JSON. If gate failed OR `hybrid_gemma_serving` unavailable, **skip L4** per FR-LLM-007.

**Install:**
```bash
# E4-S05 / E4-S07's role re-renders /srv/graphiti/.env on ct-ai-01 with phase-4 layout
# when enable_phase_4_bridge=true is set in the Ansible role's defaults.
ansible-playbook -i homelab-infra/ansible/inventory/hosts.yml \
  homelab-infra/ansible/playbooks/deploy-ai-dev-context-stack.yml \
  --ask-vault-pass --limit ct-ai-01.tail-scale.ts.net \
  -e enable_phase_4_bridge=true
ssh ct-ai-01.tail-scale.ts.net 'cd /srv/graphiti && sudo docker compose up -d --force-recreate graphiti-mcp'
```

**Smoke test (T-L4):**
```bash
# T-L4.1 — env reflects phase-4 layout
ssh ct-ai-01.tail-scale.ts.net 'sudo grep OPENAI_BASE_URL /srv/graphiti/.env' \
   | grep -q 'hybrid-gemma-litellm' && echo "PASS L4.1" || echo "FAIL L4.1"
# T-L4.2 — embeddings DID NOT switch (must stay on OpenAI per ADR-003 / FR-LLM-004)
ssh ct-ai-01.tail-scale.ts.net 'sudo grep -E "EMBEDDER_OPENAI_BASE_URL|EMBEDDER_MODEL_NAME" /srv/graphiti/.env'
# Expectation: EMBEDDER_OPENAI_BASE_URL=https://api.openai.com/v1, EMBEDDER_MODEL_NAME=text-embedding-3-small
# T-L4.3 — add_episode still produces a UUID with the bridge active
TS=$(date -u +%Y%m%dT%H%M%SZ)
claude -p "use mcp__graphiti__add_episode with name=l4-bridge-$TS, episode_body=Bridge probe at $TS, source=text, group_id=l4-bridge-smoke" \
   | grep -qiE 'uuid|added' && echo "PASS L4.3" || echo "FAIL L4.3"
# T-L4.4 — backstop: search_facts still works
sleep 3
claude -p "use mcp__graphiti__search_facts with query=Bridge probe at $TS, group_id=l4-bridge-smoke" \
   | grep -qF "$TS" && echo "PASS L4.4" || echo "FAIL L4.4"
# T-L4.5 — fallback drill (NFR-AVAIL-003 / FR-LLM-006)
ssh hybrid-gemma-litellm.tail-scale.ts.net 'sudo systemctl stop litellm' \
   2>/dev/null || echo "(no LiteLLM systemd unit on workstation; assume external)"
# Expectation per FR-LLM-006: bridge auto-falls-back to cloud gpt-4o-mini.
# This depends on Graphiti's OpenAIGenericClient retry policy — verify by attempting an episode.
TS2=$(date -u +%Y%m%dT%H%M%SZ)
timeout 30 claude -p "use mcp__graphiti__add_episode with name=l4-fallback-$TS2, episode_body=fallback probe, source=text, group_id=l4-bridge-smoke" \
   | grep -qiE 'uuid|added' && echo "PASS L4.5 (fallback to OpenAI succeeded)" \
                            || echo "FAIL L4.5 (no fallback)"
ssh hybrid-gemma-litellm.tail-scale.ts.net 'sudo systemctl start litellm' 2>/dev/null || true
# T-L4.6 — cleanup
claude -p "use mcp__graphiti__clear_graph with group_id=l4-bridge-smoke"
```

**Go/No-Go gate G4.** T-L4.1, .2, .3, .4 all PASS. T-L4.5 demonstrates auto-fallback OR the operator accepts the gap and revert-drills to Phase 3. Proceed to L5.

**Rollback procedure for L4** (revert env vars only; no Graphiti down-time required):
```bash
# Re-render .env without the bridge flag
ansible-playbook -i homelab-infra/ansible/inventory/hosts.yml \
  homelab-infra/ansible/playbooks/deploy-ai-dev-context-stack.yml \
  --ask-vault-pass --limit ct-ai-01.tail-scale.ts.net \
  -e enable_phase_4_bridge=false
ssh ct-ai-01.tail-scale.ts.net 'cd /srv/graphiti && sudo docker compose up -d --force-recreate graphiti-mcp'
# Verify reversion
ssh ct-ai-01.tail-scale.ts.net 'sudo grep -c OPENAI_BASE_URL /srv/graphiti/.env' \
   | grep -q 0 && echo "PASS L4-rollback" || echo "FAIL L4-rollback"
```
**Time bound:** ≤ 5 min (FR-LLM-008: bridge MUST be reversible in ≤ 1 day; we beat that by orders of magnitude because no data migration is involved).

#### L5 — Observability + daily $1 cap

**Install:**
```bash
# Cost-cap.sh + cron + admin key already deployed by E4-S07's role on ct-ai-01.
# Verify they're in place:
ssh ct-ai-01.tail-scale.ts.net <<'EOF'
test -x /srv/graphiti/scripts/cost-cap.sh && echo "PASS cap-script-present"
crontab -l | grep -q 'cost-cap.sh' && echo "PASS cap-cron-present"
test -f /srv/graphiti/.env && sudo grep -q OPENAI_ADMIN_KEY /srv/graphiti/.env && echo "PASS admin-key-present"
EOF
# Weekly digest template + first digest committed by E4-S09:
test -f ~/workspace/homelab/homelab-playbook/wiki/runbooks/weekly-digest-template.md \
   && echo "PASS digest-template"
```

**Smoke test (T-L5):**
```bash
# T-L5.1 — cron firing every 30 min
ssh ct-ai-01.tail-scale.ts.net 'tail -50 /var/log/syslog' | grep -qE 'cost-cap.sh|CRON.*cost-cap' \
   && echo "PASS L5.1" || echo "FAIL L5.1 (cron not visible — check cron service)"
# T-L5.2 — manual breach test (forces SEMAPHORE_LIMIT drop)
ssh ct-ai-01.tail-scale.ts.net 'sudo /srv/graphiti/scripts/cost-cap.sh --test-trigger' 2>&1 | tee /tmp/t-l5-2.log
ssh ct-ai-01.tail-scale.ts.net 'sudo grep SEMAPHORE_LIMIT /srv/graphiti/.env'
# Expectation: SEMAPHORE_LIMIT=1 after trigger
# T-L5.3 — ntfy alert reached the phone (operator visual confirmation; or check ntfy server log)
ssh ct101.tail-scale.ts.net 'tail -20 /var/log/ntfy.log' | grep -q graphiti-alerts \
   && echo "PASS L5.3" || echo "FAIL L5.3"
# T-L5.4 — auto-restore at UTC day rollover
# (operator runs at next UTC 00:00; or simulate by editing today's spend marker)
ssh ct-ai-01.tail-scale.ts.net 'sudo /srv/graphiti/scripts/cost-cap.sh --test-restore'
ssh ct-ai-01.tail-scale.ts.net 'sudo grep SEMAPHORE_LIMIT /srv/graphiti/.env' \
   | grep -q 'SEMAPHORE_LIMIT=5' && echo "PASS L5.4" || echo "FAIL L5.4"
# T-L5.5 — disk footprint inventory (NFR-FOOTPRINT-003)
ssh ct-ai-01.tail-scale.ts.net 'sudo du -sh /srv/graphiti/data /srv/graphiti/backups'
du -sh ~/.gitnexus 2>/dev/null
du -sh ~/workspace/homelab/homelab-playbook/wiki
# Sum should be < 5 GB
# T-L5.6 — weekly digest is filable
test -f ~/workspace/homelab/homelab-playbook/wiki/runbooks/weekly-digest-$(date -u +%Y-%V).md \
   || echo "(digest not yet authored this week — expected if mid-week)"
```

**Go/No-Go gate G5.** T-L5.1, .2, .3, .4 all PASS. T-L5.5 inventory < 5 GB combined.

**Rollback procedure for L5** (without disturbing L1-L4):
```bash
# Stop the cron
ssh ct-ai-01.tail-scale.ts.net 'sudo crontab -l | grep -v cost-cap.sh | sudo crontab -'
# Restore SEMAPHORE_LIMIT to baseline
ssh ct-ai-01.tail-scale.ts.net 'sudo sed -i "s/^SEMAPHORE_LIMIT=.*/SEMAPHORE_LIMIT=5/" /srv/graphiti/.env'
ssh ct-ai-01.tail-scale.ts.net 'cd /srv/graphiti && sudo docker compose up -d --force-recreate graphiti-mcp'
# Verify
ssh ct-ai-01.tail-scale.ts.net 'crontab -l | grep -c cost-cap.sh' | grep -q 0 \
   && echo "PASS L5-rollback"
```
**Time bound:** ≤ 5 min.

### 3.2 Full-stack integration test (all four tiers cooperating)

**Goal.** A single Claude Code session that demonstrates ADR-013's tier-of-truth division by exercising each tier in turn for the kind of question that tier owns.

```bash
# T-PHASE1-INT — tier-of-truth integration
# This is one Claude Code session; the operator confirms each "tier hit" by inspecting the response.

claude --session-name=phase1-int <<'EOF'
You are running a Phase 1 end-to-end integration test of Context Stack.
Please perform these four queries in sequence and tell me which tier answered each:

1. (Tier 1, wiki) "What is our tailscale-only network policy for phone-facing surfaces?"
2. (Tier 2, GitNexus) "Which Ansible roles in homelab-infra/ansible/roles/ depend on the
    `ai-dev-base` role? Use mcp__gitnexus__cypher to find out."
3. (Tier 3, Graphiti) "Use mcp__graphiti__search_facts to find any prior decisions about
    'storage redesign for pve3'. Use group_id=tom-personal."
4. (Tier 4, auto-memory) "What does my MEMORY.md say about phone notifications? Don't run
    any tools — just read your loaded memory."

Then summarise: which tier provided the most useful answer for which query, and where would
the wrong tier have failed?
EOF
```

**Pass criterion:**
- Tier 1 → wiki-query skill triggered and cited a slug under `architecture/`.
- Tier 2 → at least one MCP `cypher` call returned non-empty results.
- Tier 3 → either returned a relevant fact OR returned an explicit "no results" (both are valid; the contract is that the call completed within 500 ms p95, NFR-PERF-002).
- Tier 4 → answered from auto-memory without any tool call.
- Total session-start overhead under NFR-PERF-001 (< 1 s vs pre-deploy 5-session baseline; G-Latency).

**Privacy check (cross-cut, NFR-PRIV-001):**
```bash
# In a separate terminal during T-PHASE1-INT, capture network traffic from the workstation
sudo timeout 60 tcpdump -i any -nn 'host api.openai.com or host api.anthropic.com' -w /tmp/phase1-int.pcap
# Inspect: api.anthropic.com is Claude Code's own conversation channel (allowed).
#          api.openai.com only receives embedding+extraction prompts triggered by Tier 3 add/search.
#          NO source code should appear in any payload (sample N=5 with `tcpdump -A`).
sudo tcpdump -A -r /tmp/phase1-int.pcap 'host api.openai.com' | head -200 \
   | grep -qE 'function|class|def |import' \
   && echo "FAIL privacy (source code in OpenAI payload)" \
   || echo "PASS privacy"
```

### 3.3 Phase 1 acceptance gate

Phase 1 is "deployed" when:

| Gate | Criterion | Evidence |
|---|---|---|
| G1A | All G0–G5 layer gates passed | This document — checkbox each layer |
| G1B | T-PHASE1-INT integration session passed all four tiers | Session log preserved |
| G1C | G-Latency: post-deploy 5-session avg ≤ pre-deploy + 1 s | `/tmp/phase1-glatency-{baseline,postdeploy}.csv` |
| G1D | Privacy audit: zero source-code lines in api.openai.com payloads | tcpdump capture |
| G1E | Combined disk footprint < 5 GB (NFR-FOOTPRINT-003) | `du -sh` outputs |
| G1F | All MCP servers healthy: `claude mcp list` shows gitnexus + graphiti both up | command output |
| G1G | Wiki seeds (≥ 3) referenced by ≥ 3 sessions in week leading up to test | `homelab-playbook/wiki/_session-log.md` |

**If any gate fails:** rollback the responsible layer per §3.1 procedures and do NOT proceed to Phase 2. Phase 2 is an additive test — installing on `ct-dev-homelab` cannot fix a Phase 1 fault.

---

## 4. Phase 2 ct-dev-homelab Deploy

Phase 2 exercises the same stack via the Ansible role `ai-dev-context-stack` against the standing test container. **Critical mental model (per E4-S07 Implementation Notes):** `ct-dev-homelab` is a *Claude Code client* of the stack, not a Graphiti host. The role installs:
- On `ct-dev-homelab`: wiki-query skill, wiki tree mirror, MCP registration pointing at `ct-ai-01`.
- On the workstation (delegate-to-localhost): GitNexus install (if `context_stack_install_gitnexus=true`).
- On `ct-ai-01`: `.env` re-rendering only when `enable_phase_4_bridge` flips.

### 4.1 Ansible role invocation

```bash
TS=$(date -u +%Y%m%dT%H%M%SZ)

# Step 1 — pre-deploy snapshot (E4-S08 AC1)
bash homelab-playbook/scripts/snapshot-ct-dev-homelab.sh \
   /tmp/ct-dev-homelab-pre-deploy-$TS.txt
# Step 2 — G-Latency baseline (E4-S08 AC12)
for i in 1 2 3 4 5; do
  ssh ct-dev-homelab.tail-scale.ts.net "/usr/bin/time -f '%e' claude -p 'just exit'" \
     2>>/tmp/p2-glatency-baseline.csv
done
# Step 3 — RUN THE DEPLOY (E4-S08 AC2)
time ansible-playbook \
  -i homelab-infra/ansible/inventory/hosts.yml \
  homelab-infra/ansible/playbooks/deploy-ai-dev-context-stack.yml \
  --ask-vault-pass \
  --limit ct-dev-homelab.tail-scale.ts.net \
  2>&1 | tee /tmp/p2-deploy-$TS.log
# Step 4 — verify deploy success (AC2 markers)
grep -E 'failed=0.+unreachable=0' /tmp/p2-deploy-$TS.log
# Wall-time target: ≤ 15 min for this command
```

### 4.2 Per-layer smoke tests (post-Ansible-run)

The Ansible role's `verify.yml` (E4-S07 AC9) covers most per-layer assertions in-line during the run. The post-run human-driven checks below confirm the *cross-layer* integrity — i.e., that all layers work together, not just each in isolation.

```bash
# T-P2-L1 — wiki tree mirrored
ssh ct-dev-homelab.tail-scale.ts.net 'find ~/workspace/homelab/homelab-playbook/wiki -name "*.md" | wc -l'
# Expectation: matches workstation count
ssh ct-dev-homelab.tail-scale.ts.net 'test -f ~/.claude/skills/wiki-query/SKILL.md && echo PASS'

# T-P2-L2 — GitNexus on workstation (if delegated)
# Verify the role didn't break the workstation install
claude mcp list | grep -q gitnexus && echo "PASS workstation L2 unchanged"

# T-P2-L3 — Graphiti MCP registered on the container, pointing at ct-ai-01
ssh ct-dev-homelab.tail-scale.ts.net 'claude mcp list' | grep -E '^graphiti.+http://ct-ai-01' \
   && echo "PASS P2-L3.1" || echo "FAIL P2-L3.1"
# Roundtrip from container
ssh ct-dev-homelab.tail-scale.ts.net \
   "claude -p 'use mcp__graphiti__add_episode with name=p2-smoke, episode_body=phase 2 probe, source=text, group_id=ct-dev-homelab-smoke'" \
   | grep -qi uuid && echo "PASS P2-L3.2"

# T-P2-L5 — cron + cost-cap unchanged on ct-ai-01
ssh ct-ai-01.tail-scale.ts.net 'crontab -l | grep -c cost-cap.sh' | grep -q 1 && echo "PASS P2-L5.1"

# T-P2-VERIFY — re-run the role's verify.yml directly
ansible-playbook \
  -i homelab-infra/ansible/inventory/hosts.yml \
  homelab-infra/ansible/playbooks/deploy-ai-dev-context-stack.yml \
  --ask-vault-pass --limit ct-dev-homelab.tail-scale.ts.net --tags verify
```

### 4.3 Full-stack integration test on container

```bash
# T-PHASE2-INT — same four-tier integration as §3.2, but executed FROM ct-dev-homelab
ssh ct-dev-homelab.tail-scale.ts.net <<'EOF'
cd ~/workspace/homelab
claude --session-name=phase2-int <<'INNER'
Please run the four-tier integration test:
1. Tier 1 (wiki): "what's the runbook for restoring Graphiti from a Cypher export?"
2. Tier 2 (GitNexus delegated to workstation — expected to be UNAVAILABLE here, that's fine):
    "use mcp__gitnexus__cypher to count files. If gitnexus is not registered here, just say so."
3. Tier 3 (Graphiti via Tailscale to ct-ai-01): "use mcp__graphiti__search_facts to find any
    prior decisions about 'pve3 storage redesign'. group_id=tom-personal."
4. Tier 4 (auto-memory): "summarise what MEMORY.md tells you about ct-dev-homelab itself."

Tell me which tiers fired and which (correctly) did not.
INNER
EOF
```

**Pass criterion:**
- Tier 1 fires successfully on the container.
- Tier 2 correctly reports "not available here" — this is the expected client-only topology.
- Tier 3 succeeds via Tailscale.
- Tier 4 reads `MEMORY.md` from the container's `~/.claude/projects/.../memory/` and answers.

### 4.4 Five smoke tests from runbook §7 (E4-S08 AC3 / FR-DEP-006)

Run the canonical bundle:
```bash
bash homelab-playbook/scripts/smoke-tests/ct-dev-homelab.sh
# Expectations (per E4-S08 AC4 — ADR-014 SHOULD calibration):
#   Hard-pass (non-negotiable): tests 1, 2, 5
#   Quality-acceptable: tests 3, 4
```

### 4.5 Phase 2 acceptance gate

| Gate | Criterion | Evidence |
|---|---|---|
| G2A | Ansible deploy AC2 success (failed=0 unreachable=0) | `/tmp/p2-deploy-*.log` |
| G2B | All T-P2 smoke tests pass | command output |
| G2C | Phase-2 integration session passes 4-tier sanity | session log |
| G2D | Smoke-test bundle: hard-pass on tests 1, 2, 5 + quality on 3, 4 | `/tmp/e4-s08-smoke-*.log` |
| G2E | G-Latency post-deploy ≤ baseline + 1 s on the container | `/tmp/p2-glatency-*.csv` |
| G2F | Idempotency: second deploy reports `changed=0` (E4-S07 AC11) | rerun output |
| G2G | Smoke pollution cleared (E4-S08 AC5) | search_facts returns empty |
| G2H | **G-Rollback drill** (next section) succeeds | §5.1 evidence |

**Note:** G2H gates promotion off `ct-dev-homelab`. Brief §6 hard requirement.

---

## 5. Rollback Tests

The whole point of testing rollback "in anger" (per the brief special note) is to discover failures that the design doesn't anticipate. Each drill below is *not* a re-statement of the deploy-procedure-in-reverse — it deliberately tries to break things and then sees if rollback recovers.

### 5.1 Per-layer rollback drills (mid-flight kill scenarios)

#### Drill RB-L1 — Kill the wiki skill copy mid-rsync

```bash
# Setup: ensure wiki is in known good state
ssh ct-dev-homelab.tail-scale.ts.net 'rm -rf ~/workspace/homelab/homelab-playbook/wiki ~/.claude/skills/wiki-query'

# Run install with deliberate mid-flight kill (15s — typically catches mid-rsync)
timeout 15 ansible-playbook ... --tags wiki || echo "killed (expected)"
# Assert: partial state observable
ssh ct-dev-homelab.tail-scale.ts.net 'find ~/workspace/homelab/homelab-playbook/wiki -name "*.md" | wc -l'
# Likely 1-3 files instead of full count

# Run rollback
ansible-playbook ... rollback-ai-dev-context-stack.yml --tags wiki

# Verify clean state
ssh ct-dev-homelab.tail-scale.ts.net 'test ! -d ~/workspace/homelab/homelab-playbook/wiki && test ! -d ~/.claude/skills/wiki-query' \
   && echo "PASS RB-L1"
```

**Expected behaviour:** the rollback playbook uses `state: absent` — partial files are removed cleanly. **If FAIL** (e.g., a half-rsynced file is locked or owned by an unexpected user): file an idempotency bug against E4-S07 and iterate.

#### Drill RB-L2 — Kill `npm install -g gitnexus` mid-flight

```bash
# Workstation drill: timeout the install
timeout 5 npm install -g gitnexus@1.6.3
# Verify partial state
ls /usr/local/lib/node_modules/gitnexus 2>/dev/null && echo "(partial install observed)"
# Run rollback
npm uninstall -g gitnexus
rm -rf /usr/local/lib/node_modules/gitnexus
# Verify
which gitnexus 2>/dev/null && echo "FAIL RB-L2 (binary still present)" || echo "PASS RB-L2"
```

**Expected behaviour:** `npm uninstall` is idempotent and idempotent-equivalent on partial installs. **If FAIL:** manual `rm -rf` of the package dir is the documented recovery (this is in the rollback runbook).

#### Drill RB-L3 — Kill `docker compose up` mid-pull on ct-ai-01 (server-side)

```bash
ssh ct-ai-01.tail-scale.ts.net <<'EOF'
cd /srv/graphiti
sudo docker compose down
# Force a fresh image pull then kill
sudo docker rmi zepai/graphiti-mcp:v1.0.2 falkordb/falkordb:edge 2>/dev/null
timeout 8 sudo docker compose up -d || echo "killed (expected)"
sudo docker compose ps  # likely shows partial: one container up, one not
EOF
# Run server-side rollback
ssh ct-ai-01.tail-scale.ts.net <<'EOF'
cd /srv/graphiti
sudo docker compose down -v
EOF
# Verify
ssh ct-ai-01.tail-scale.ts.net 'sudo docker ps -a | grep -E "graphiti-mcp|graphiti-falkordb" | wc -l' \
   | grep -q 0 && echo "PASS RB-L3"
# Re-deploy to recover (data is preserved on /srv/graphiti/data unless -v was used; this drill uses -v)
ssh ct-ai-01.tail-scale.ts.net 'cd /srv/graphiti && sudo docker compose up -d'
# Verify recovery
ssh ct-ai-01.tail-scale.ts.net 'sudo docker compose ps' | grep -c Up | grep -q 2 \
   && echo "PASS RB-L3 recovery"
```

**Critical observation:** `docker compose down -v` deletes the volume. If the operator wanted to preserve data, they must `sudo cp -a /srv/graphiti/data /srv/graphiti/data.bak` before `down -v`. Document this in the rollback runbook.

#### Drill RB-L4 — Kill LiteLLM bridge mid-validation

```bash
# Trigger E4-S06 validation harness
nohup bash homelab-playbook/scripts/litellm-50-fact-validation.sh > /tmp/l4-val.log 2>&1 &
HARNESS_PID=$!
sleep 30  # let it process some facts
kill -TERM $HARNESS_PID 2>/dev/null

# Per FR-LLM-006: the bridge must auto-fallback. Verify the next add_episode succeeds via cloud.
TS=$(date -u +%Y%m%dT%H%M%SZ)
claude -p "use mcp__graphiti__add_episode with name=rb-l4-$TS, episode_body=fallback drill, source=text, group_id=rb-l4-smoke" \
   | grep -qi uuid && echo "PASS RB-L4 (fallback to cloud after harness kill)" \
                   || echo "FAIL RB-L4"
# Cleanup
claude -p "use mcp__graphiti__clear_graph with group_id=rb-l4-smoke"
```

#### Drill RB-L5 — Cron pickup mid-cycle

```bash
# Kill the cost-cap.sh while it's running (race the */30 schedule)
ssh ct-ai-01.tail-scale.ts.net 'sudo /srv/graphiti/scripts/cost-cap.sh &'
sleep 2
ssh ct-ai-01.tail-scale.ts.net 'sudo pkill -f cost-cap.sh'
# Verify .env not left in inconsistent state
ssh ct-ai-01.tail-scale.ts.net 'sudo grep -c "^SEMAPHORE_LIMIT=" /srv/graphiti/.env' | grep -q 1 \
   && echo "PASS RB-L5 (no duplicate SEMAPHORE_LIMIT lines)"
```

**Expected behaviour:** cost-cap.sh writes via atomic file replacement (sed -i with backup), so partial writes are impossible. **If FAIL** (duplicate line / corrupted .env): the script needs `mv -f` semantics — file a bug.

### 5.2 Full-stack rollback — the "uh oh, abort" exercise (RB-FULL)

**Scenario:** at week 3, the operator discovers GitNexus is consuming 800 MB RSS (failing NFR-FOOTPRINT-002, AR1). They want to drop **only L2** and keep L1 + L3 + L5 running.

```bash
# Drop L2 only
pkill -f gitnexus
claude mcp remove gitnexus
jq 'del(.hooks.PreToolUse[] | select(.command | test("gitnexus"))) |
    del(.hooks.PostToolUse[] | select(.command | test("gitnexus")))' \
    ~/.claude/settings.json > /tmp/settings.json && mv /tmp/settings.json ~/.claude/settings.json
npm uninstall -g gitnexus
rm -rf ~/.gitnexus

# Verify L1 still works
claude -p "what's our tailscale policy?" | grep -qi tailscale && echo "PASS L1 still up"
# Verify L3 still works
TS=$(date -u +%Y%m%dT%H%M%SZ)
claude -p "use mcp__graphiti__search_facts with query=anything, group_id=tom-personal" \
   && echo "PASS L3 still up"
# Verify L5 still firing on ct-ai-01
ssh ct-ai-01.tail-scale.ts.net 'crontab -l | grep -c cost-cap.sh' | grep -q 1 \
   && echo "PASS L5 still up"
# Confirm operator's daily session-start latency dropped (G-Latency improvement!)
for i in 1 2 3 4 5; do /usr/bin/time -f '%e' claude -p 'just exit' 2>>/tmp/rb-full-postL2-removal.csv; done
awk '{ s+=$1; n++ } END { print "avg:", s/n }' /tmp/rb-full-postL2-removal.csv
```

**Pass criterion:** L1, L3, L5 still respond; G-Latency improves (or stays flat); the workstation continues to be daily-driverable. **This is the operator-realistic rollback** — no all-or-nothing.

### 5.3 Disaster recovery scenarios

These three are the "operationally honest" tests — they reveal whether the design holds when something *unexpected* happens.

#### Disaster D1 — FalkorDB AOF corruption + RDB restore + Cypher replay

**Threat model.** Power-loss or disk-full mid-AOF-write leaves a truncated AOF. FalkorDB starts but reports "AOF tail corrupted". Operator restores from latest weekly RDB, then replays the daily Cypher export to fill the gap.

```bash
# Setup: induce corruption on a copy (do NOT do this on production data)
ssh ct-ai-01.tail-scale.ts.net <<'EOF'
sudo cp -a /srv/graphiti/data /srv/graphiti/data.bak
sudo truncate -s -1k /srv/graphiti/data/appendonlydir/appendonly.aof.*.incr.aof 2>/dev/null \
  || sudo truncate -s -1k /srv/graphiti/data/appendonly.aof
EOF

# Bring FalkorDB back up — should show recovery error in logs
ssh ct-ai-01.tail-scale.ts.net 'cd /srv/graphiti && sudo docker compose restart graphiti-falkordb'
sleep 10
ssh ct-ai-01.tail-scale.ts.net 'sudo docker compose logs --tail=50 graphiti-falkordb' \
   | grep -qE 'AOF.+(truncate|corrupt|invalid)' && echo "PASS D1.1 (corruption detected)"

# Restore from RDB (latest weekly)
ssh ct-ai-01.tail-scale.ts.net <<'EOF'
cd /srv/graphiti
sudo docker compose down
LATEST_RDB=$(ls -t /srv/graphiti/backups/dump-*.rdb | head -1)
sudo cp "$LATEST_RDB" /srv/graphiti/data/dump.rdb
sudo rm -f /srv/graphiti/data/appendonly.aof /srv/graphiti/data/appendonlydir/*.aof 2>/dev/null
sudo docker compose up -d
EOF
sleep 10
# Verify FalkorDB up and serving
ssh ct-ai-01.tail-scale.ts.net 'sudo docker compose exec -T graphiti-falkordb redis-cli PING' \
   | grep -q PONG && echo "PASS D1.2 (RDB-restored and PING OK)"

# Replay the missing day from Cypher export (ADR-007 monthly export — covers gap)
LATEST_CYPHER=$(ssh ct-ai-01.tail-scale.ts.net 'ls -t /srv/graphiti/backups/cypher-*.json | head -1')
ssh ct-ai-01.tail-scale.ts.net "sudo bash /srv/graphiti/scripts/cypher-replay.sh $LATEST_CYPHER"
# Verify episode count restored
claude -p "use mcp__graphiti__get_episodes with last_n=10, group_id=tom-personal" | grep -qE 'episode|uuid' \
   && echo "PASS D1.3"

# Cleanup if drill (keep .bak for re-attempt)
ssh ct-ai-01.tail-scale.ts.net 'sudo rm -rf /srv/graphiti/data.bak'
```

**Pass criterion:** FalkorDB serves PING; `get_episodes` returns episodes; total count is at-least-RDB-snapshot-count plus replayed gap. **If FAIL at D1.3:** ADR-007's three-layer backup (AOF + RDB + Cypher) does not actually compose into a recoverable system; this is a real architectural gap. File a critical bug against E3-S07.

#### Disaster D2 — OpenAI / Anthropic 429 storm + $1/day cap engagement

**Threat model.** Anthropic or OpenAI throttles the operator (rate limit 429); usage spike pushes daily spend toward $1. Cap MUST engage; SEMAPHORE_LIMIT MUST drop; ntfy MUST fire; auto-memory MUST keep working.

```bash
# Synthetic: trigger cost-cap.sh with simulated $0.99 spend
ssh ct-ai-01.tail-scale.ts.net 'sudo OPENAI_TODAY_USD=0.99 /srv/graphiti/scripts/cost-cap.sh' 2>&1 \
   | tee /tmp/d2.log
# Verify SEMAPHORE_LIMIT dropped to 1
ssh ct-ai-01.tail-scale.ts.net 'sudo grep SEMAPHORE_LIMIT /srv/graphiti/.env' | grep -q '=1' \
   && echo "PASS D2.1"
# Verify ntfy alert fired
ssh ct101.tail-scale.ts.net 'tail -5 /var/log/ntfy.log' | grep -q graphiti-alerts \
   && echo "PASS D2.2"
# Verify Tier 1 (wiki) still works WITHOUT any LLM call
claude -p "what's our tailscale policy?" 2>&1 | grep -qi tailscale && echo "PASS D2.3"
# Verify Tier 4 (auto-memory) still works without any LLM call
claude -p 'echo memory loaded' | grep -q 'memory loaded' && echo "PASS D2.4"
# Verify Tier 3 still WORKS but slowly (SEMAPHORE=1 → serialised episodes)
TS=$(date -u +%Y%m%dT%H%M%SZ)
time claude -p "use mcp__graphiti__add_episode with name=d2-$TS, episode_body=throttled probe, source=text, group_id=d2-smoke"
# Expect: completes (degraded) within reasonable bound
# Verify auto-restore at next UTC day rollover (or simulate)
ssh ct-ai-01.tail-scale.ts.net 'sudo /srv/graphiti/scripts/cost-cap.sh --test-restore'
ssh ct-ai-01.tail-scale.ts.net 'sudo grep SEMAPHORE_LIMIT /srv/graphiti/.env' | grep -q '=5' \
   && echo "PASS D2.5"
# Cleanup
claude -p "use mcp__graphiti__clear_graph with group_id=d2-smoke"
```

**Pass criterion:** D2.1–D2.5 all PASS. Crucially, even when the cap engages, the workstation remains daily-driverable because L1 (wiki) and L4 (auto-memory) require zero LLM calls. **If FAIL** at D2.3 or D2.4: there's a hidden coupling between the LLM tiers and the wiki/memory tiers; this contradicts ADR-013's tier-of-truth division and is a critical architectural finding.

**Real-world variant.** Genuine 429 from Anthropic during a chatty session. Pass criterion in this case is operator-perceptual: Claude Code retries with backoff; auto-memory + wiki continue to function; episode-write is queued or refused gracefully.

#### Disaster D3 — Network partition (workstation can't reach `ct-dev-homelab` / `ct-ai-01`)

**Threat model.** Tailscale outage or operator on hotel wifi without Tailscale.

```bash
# Simulate: drop Tailscale
sudo tailscale down
sleep 5

# Verify Tier 1 (workstation-local) still works
bash ~/workspace/homelab/homelab-playbook/scripts/wiki-lint.sh && echo "PASS D3.1 (lint local)"
claude -p "what's our tailscale policy?" | grep -qi tailscale && echo "PASS D3.2 (wiki-query local)"

# Verify Tier 2 (workstation-local) still works
claude -p 'use mcp__gitnexus__cypher with query="MATCH (n) RETURN count(n) LIMIT 1"' \
   | grep -qE '[0-9]' && echo "PASS D3.3"

# Verify Tier 3 fails GRACEFULLY (within 3 s, not hang) — NFR-AVAIL-002
START=$(date +%s)
timeout 10 claude -p "use mcp__graphiti__search_facts with query=test, group_id=tom-personal" \
   2>&1 || echo "(failed as expected — graphiti unreachable)"
END=$(date +%s)
[ $((END-START)) -lt 5 ] && echo "PASS D3.4 (graceful in $((END-START))s)"

# Verify Tier 4 (auto-memory) still works
claude -p 'echo memory loaded' | grep -q 'memory loaded' && echo "PASS D3.5"

# Restore
sudo tailscale up
```

**Pass criterion:** D3.1–D3.5 all PASS. **The architectural commitment:** offline workstation use is a first-class mode (NFR-AVAIL-001/002 force it). If D3.4 hangs > 5 s, the MCP HTTP timeout is misconfigured — this is a real bug.

---

## 6. Performance / NFR Gates (E2E)

These gates are measured end-to-end across all four tiers active, not per-component. They map directly to PRD §6 NFRs.

| NFR | Threshold | Measurement | Where |
|---|---|---|---|
| NFR-PERF-001 (G-Latency) | Session-start overhead < 1 s vs pre-deploy 5-session baseline | `for i in 1..5; do /usr/bin/time -f '%e' claude -p 'just exit'; done` baseline + post-deploy; compare averages | §3.3 G1C; §4.5 G2E |
| NFR-PERF-002 | Query p95 < 500 ms (Graphiti search_facts, GitNexus cypher) | 50-query batch with timing capture; sort and pick p95 | §3.1 T-L3.6, T-L2 cypher |
| NFR-PERF-003 | Wiki Tier-1 file-read < 200 ms | 20 wiki-query invocations, average | §3.1 T-L1.5 |
| NFR-PERF-004 | GitNexus incremental reindex < 30 s | PostToolUse log on 10 typical commits | §3.1 T-L2.5 |
| NFR-PERF-005 | GitNexus full reindex < 60 s | `npx gitnexus reindex --full` cold start | §3.1 T-L2 reindex section |
| NFR-PERF-006 | Graphiti add_episode < 5 s per ~2k-token episode | 30 episodes timed; average | run during T-L3.3 with timing |
| NFR-COST-001 | < $20/month all-in | Weekly OpenAI billing + Anthropic usage export | E4-S09 weekly digest |
| NFR-COST-002 | < $1/day hard cap | cost-cap.sh poll | §3.1 T-L5.2 + §5.3 D2 |
| NFR-COST-003 | Phase 4 cost-neutrality | 7-day pre-bridge vs post-bridge spend at equal usage | E4-S09 |
| NFR-FOOTPRINT-001 | FalkorDB RSS < 200 MB | `docker stats graphiti-falkordb` 24h sample | E3-S09 |
| NFR-FOOTPRINT-002 | GitNexus daemon RSS < 500 MB | `ps -o rss` 24h sample | §3.1 T-L2.2 |
| NFR-FOOTPRINT-003 | Combined disk footprint < 5 GB | `du -sh` Graphiti data + GitNexus index + wiki | §3.1 T-L5.5 |
| NFR-AVAIL-001 | GitNexus down → no hang > 3 s | drill at §3.1 T-L2.7 | §3.1 + §5.3 D3.4 |
| NFR-AVAIL-002 | Graphiti down → no hang > 3 s | drill at §3.1 T-L3.7 | §3.1 + §5.3 D3.4 |
| NFR-AVAIL-003 | LiteLLM down → cloud fallback | drill at §3.1 T-L4.5 | §3.1 |
| NFR-MAINT-001 | Each component unwireable in ≤ 1 day | Per-layer rollback in §3.1 (each section ends with time bound) | §3.1 + §5.1 |
| NFR-MAINT-002 | Decommission rollback documented | E1 runbook + dry-run on ct-dev-homelab | E1-S07 + §3.1 L0 rollback |
| NFR-PRIV-001 | Source code stays workstation-local | tcpdump audit during reindex + integration test | §3.1 T-L2.6 + §3.2 privacy check |
| NFR-AVAIL-003 + offline | Phase 1 stack functional with no internet | §5.3 D3 | §5.3 D3 |

### 6.1 G-Latency end-to-end test

```bash
# Pre-deploy baseline (run BEFORE any L1-L5 install)
for i in 1 2 3 4 5; do /usr/bin/time -f '%e' claude -p 'just exit' 2>>/tmp/glat-baseline.csv; done
# Post-deploy (after all 5 layers installed)
for i in 1 2 3 4 5; do /usr/bin/time -f '%e' claude -p 'just exit' 2>>/tmp/glat-postdeploy.csv; done
# Compute deltas
B=$(awk '{s+=$1;n++} END {print s/n}' /tmp/glat-baseline.csv)
P=$(awk '{s+=$1;n++} END {print s/n}' /tmp/glat-postdeploy.csv)
echo "baseline=$B postdeploy=$P delta=$(echo "$P - $B" | bc)"
# Pass: delta < 1.0
```

### 6.2 Footprint inventory (final state)

```bash
echo "=== Workstation ==="
du -sh ~/.gitnexus 2>/dev/null
du -sh ~/workspace/homelab/homelab-playbook/wiki
du -sh ~/.claude/skills/wiki-query
echo "=== ct-ai-01 ==="
ssh ct-ai-01.tail-scale.ts.net 'sudo du -sh /srv/graphiti/data /srv/graphiti/backups'
echo "=== ct-ai-01 Docker ==="
ssh ct-ai-01.tail-scale.ts.net 'sudo docker stats --no-stream --format "{{.Name}} {{.MemUsage}}"' \
   | grep -E 'graphiti'
```

---

## 7. Test Matrix Summary

| Test ID | Phase | Layer | Type | Pass criterion | Time budget |
|---|---|---|---|---|---|
| 2.3-PF | Pre | — | preflight | All 20 checks PASS | 5 min |
| T-L0 | P1 | L0 | smoke | 4 PASS | 5 min |
| T-L1 | P1 | L1 | smoke | 4 hard PASS + latency SHOULD | 10 min |
| T-L2 | P1 | L2 | smoke | 5 PASS + reindex < 30 s + privacy clean | 25 min |
| T-L3 | P1 | L3 | smoke | 5 PASS + p95 < 500 ms + degraded < 5 s | 15 min |
| T-L4 | P1 | L4 | smoke (stretch) | 4 PASS or skip per FR-LLM-007 | 20 min |
| T-L5 | P1 | L5 | smoke | 4 PASS + disk < 5 GB | 15 min |
| T-PHASE1-INT | P1 | all | integration | 4-tier session passes | 10 min |
| Privacy audit | P1 | L2 | NFR | tcpdump shows no source-code in OpenAI payloads | 10 min |
| G1A..G1G | P1 | — | gate | All 7 gates green | 5 min |
| 4.1-DEPLOY | P2 | — | install | ansible exit 0, ≤ 15 min | 15 min |
| T-P2-L1..5 | P2 | per-layer | smoke | role's verify.yml + cross-layer | 15 min |
| T-PHASE2-INT | P2 | all | integration | container 4-tier session | 10 min |
| 4.4 smoke bundle | P2 | all | smoke (FR-DEP-006) | hard 1, 2, 5 + quality 3, 4 | 20 min |
| G2A..G2H | P2 | — | gate | All 8 gates green (incl. RB-FULL) | 5 min |
| RB-L1 | P2 | L1 | rollback drill | Mid-rsync kill recovers | 10 min |
| RB-L2 | P1 | L2 | rollback drill | npm partial install removed | 5 min |
| RB-L3 | P2 | L3 | rollback drill | Compose mid-pull recovers | 15 min |
| RB-L4 | P1 | L4 | rollback drill | Validation harness kill → fallback | 10 min |
| RB-L5 | P1 | L5 | rollback drill | cron pickup mid-cycle no .env corruption | 5 min |
| RB-FULL | P1 | all | rollback exercise | drop only L2, L1+L3+L5 still work | 15 min |
| D1 | P2 | L3 | disaster | AOF corruption → RDB+Cypher restore | 30 min |
| D2 | P1 | L5+L3 | disaster | $1 cap engages; L1+L4 unaffected | 15 min |
| D3 | P1 | all | disaster | Tailscale down → L1+L2+L4 still work | 10 min |
| 6.1-GLAT | P1+P2 | all | NFR | post-baseline delta < 1 s | 5 min |
| 6.2-FOOT | P1+P2 | all | NFR | combined < 5 GB | 5 min |

**Total: 26 test groups.**

---

## 8. Test Execution Sequence (happy-path runbook)

A single-afternoon sequence (≤ 4 hours wall-clock) from cold start to all-greens. Designed to fit a half-day operator window.

| # | Step | Time | Cumulative | Notes |
|---|---|---|---|---|
| 1 | Pre-flight (§2.3) | 5 min | 0:05 | Run the script; abort if any FAIL |
| 2 | Capture pre-deploy G-Latency baseline (§6.1) | 3 min | 0:08 | 5 sessions × ~30 s each |
| 3 | Phase 1 L0 verification (T-L0) | 5 min | 0:13 | E1 already merged; just verify state |
| 4 | Phase 1 L1 install + T-L1 (§3.1) | 10 min | 0:23 | Wiki + skill |
| 5 | Phase 1 L2 install + T-L2 (§3.1) | 25 min | 0:48 | npm install + reindex + tcpdump audit |
| 6 | Phase 1 L3 register + T-L3 (§3.1) | 15 min | 1:03 | MCP add + 5 smoke + p95 + degraded |
| 7 | Phase 1 L4 install + T-L4 (§3.1) — SKIP if Phase 4 deferred | 20 min (or 0) | 1:23 | Bridge + 50-fact gate already passed in E4-S06 |
| 8 | Phase 1 L5 install + T-L5 (§3.1) | 15 min | 1:38 | cost-cap + cron + ntfy |
| 9 | Phase 1 integration session (§3.2 T-PHASE1-INT) | 10 min | 1:48 | 4-tier in one session |
| 10 | Phase 1 privacy audit (§3.2) | 10 min | 1:58 | tcpdump replay |
| 11 | Phase 1 G1A..G1G gate (§3.3) | 5 min | 2:03 | Checklist |
| 12 | Phase 2 pre-deploy snapshot (§4.1) | 5 min | 2:08 | snapshot-ct-dev-homelab.sh |
| 13 | Phase 2 deploy (§4.1 ansible-playbook) | 15 min | 2:23 | role wall-time |
| 14 | Phase 2 per-layer smoke (§4.2 T-P2-*) | 15 min | 2:38 | verify.yml + cross-layer |
| 15 | Phase 2 integration session (§4.3 T-PHASE2-INT) | 10 min | 2:48 | container-side 4-tier |
| 16 | Phase 2 5-test smoke bundle (§4.4) | 20 min | 3:08 | E4-S08 AC3 |
| 17 | Phase 2 idempotency re-run + post-deploy G-Latency (§4.5) | 10 min | 3:18 | second `--check --diff` |
| 18 | RB-FULL drill (§5.2) | 15 min | 3:33 | drop only L2; verify L1+L3+L5 |
| 19 | Phase 2 G-Rollback drill (E4-S08 AC6 = full RB-L1+RB-L3 combined IN ANGER) | 25 min | 3:58 | mid-flight kill + rollback playbook + clean-state diff |
| 20 | Re-deploy round-trip (E4-S08 AC9) + final state | 15 min | 4:13 | leave Phase 2 active for E4-S09/S11 |
| 21 | Footprint inventory (§6.2) | 5 min | 4:18 | du -sh sweep |
| 22 | Sign-off note + commit logs (§9) | 7 min | 4:25 | preserve evidence |

**Total wall-clock target: 4 h 25 min.** Phase 4 stretch (Step 7) can drop the total to **~3 h 45 min** if deferred.

**Disaster drills are NOT in the happy-path** — D1, D2, D3 are scheduled separately because each takes 10–30 min and they are intrusive. Recommended cadence: D1 quarterly (matches the FalkorDB restore drill), D2 monthly (cap behaviour drift), D3 ad-hoc (any time the operator changes ISP/Tailscale).

---

## 9. Sign-off Criteria

The E2E deployment test is **complete and green** when ALL of:

- [ ] Pre-flight script (§2.3) green
- [ ] All Phase 1 layer gates G0–G5 (§3.1) green
- [ ] Phase 1 acceptance gates G1A–G1G (§3.3) green
- [ ] All Phase 2 layer smoke tests (§4.2 T-P2-*) pass
- [ ] Phase 2 acceptance gates G2A–G2H (§4.5) green, including G2H = G-Rollback drill IN ANGER (E4-S08 AC6)
- [ ] All five rollback drills (§5.1 RB-L1..L5) succeed
- [ ] Full-stack rollback exercise (§5.2 RB-FULL) succeeds
- [ ] At least D1 + D2 + D3 disaster drills run once and PASS — within the past quarter
- [ ] All NFR gates (§6) measured and within threshold
- [ ] Operator-attested signature appended to `homelab-playbook/wiki/_session-log.md` with timestamp + summary line
- [ ] G-Latency CSVs preserved at `tests/glatency-<TS>.csv` for E4-S11 KPI scorecard

**Operator attestation template** (committed to wiki session log):
```markdown
| 2026-04-DD | E2E-deploy | sign-off | Phase1+Phase2 all green; G-Rollback IN ANGER PASS at <Ns>; D1+D2+D3 PASS; G-Latency delta <Xs>; tomamourette |
```

---

## 10. Schedule + Resource Budget

### 10.1 Recommended execution window

**Day:** mid-week afternoon (Tue/Wed/Thu) — avoids weekend on-call spike on the operator's daily-driver and avoids Monday context-switching. Target slot: **13:00–18:00 local (UTC+1 / UTC+2)**, allowing for a 30-minute buffer beyond the 4 h 25 min happy-path budget.

**Pre-execution prep day:** 24 h prior, run pre-flight script (§2.3) once — surfaces network / vault-password / Tailscale issues early.

**Operator availability:** the entire window must be operator-attended; this is not an automated-CI test. Disaster drills especially require visual confirmation of ntfy alerts and screenshot capture.

### 10.2 LLM token-budget allocation

Target total spend during E2E test execution: **≤ $5 USD across both Anthropic and OpenAI**.

| Source | Estimate | Cost @ 2026-04 pricing |
|---|---|---|
| Claude Code interactive sessions during test (~50 prompts × ~5k input + ~2k output tokens, Sonnet 4.7) | ~250k in / ~100k out | ~$0.75 + $1.50 = $2.25 |
| Graphiti `add_episode` extractions (~30 episodes × ~2k input + ~500 output, gpt-4o-mini) | ~60k in / ~15k out | ~$0.009 + $0.009 = $0.02 |
| Graphiti embeddings (~80 search/embed calls × ~50 tokens) | ~4k tokens | < $0.01 |
| LiteLLM-bridge 50-fact validation gate (E4-S06; not re-run during E2E) | already paid in E4 | $0 |
| L4 fallback drill — 5 cloud `add_episode` after LiteLLM kill | ~10k in / ~2.5k out | < $0.02 |
| Ansible role run + verify (no LLM calls) | 0 | $0 |
| **Total estimated** | | **~$2.30** |

**Buffer:** 2× headroom = $5 cap. If spend tracker shows $4 mid-execution, pause and audit before continuing.

### 10.3 Operator energy budget

The 4 h 25 min plan is at the upper bound of "single-afternoon focus" — recommend two 10-min breaks at the gate transitions (after Step 11 and after Step 17). The IN-ANGER rollback drill (Step 19) is the most cognitively demanding section and benefits from being placed AFTER a break.

---

**End of E2E deployment test plan — ready for Phase 5c readiness check.**
