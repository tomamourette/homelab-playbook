---
type: story
epic: E3
id: E3-S08
title: "Restore drill — kill FalkorDB, restore from backup, verify zero data loss"
size: 1d
priority: MUST
fr_refs: [FR-MEM-014, FR-DEP-007]
adr_refs: [ADR-007, ADR-001]
status: draft
date: 2026-04-25
---

# E3-S08: Restore drill — kill FalkorDB, restore from backup, verify zero data loss

## User Story

As **tomamourette** (homelab operator), I want **a restore drill that kills the live `graphiti-falkordb` container, wipes its data directory, restores from yesterday's AOF + RDB, brings the stack back up, and verifies the install marker fact (E3-S05 AC1) returns from `search_facts` end-to-end via the MCP server**, so that **FR-MEM-014 backup-mechanism-exercised is fully met (the only way you know your backups work is restore-tested), the G-Rollback partial-validation lights up for E4-S08, and the architectural premise of ADR-007 is proven on real probe data**.

## Background and Context

Architecture §5.4 + ADR-007 §Restore-drill-protocol mandate restore drills "before Phase 2 promotion off `ct-dev-homelab`" and quarterly thereafter. Per the brief: *"the only way you know your backups work is restore-tested"*. This story is exactly that — the destructive validation of E3-S07's backup machinery against real probe data ingested in E3-S05/06.

This is a **destructive test** by construction: the live container is taken down and its data dir wiped. The stack is then rebuilt from backup files. If anything goes wrong, the recovery path is to recreate empty and re-ingest probe data — graceful, but costs ~15 min and confirms the drill exposed a real backup gap.

Per epics §9 EQ6 (Phase 4b open question), the clock for the drill starts at **start-of-rollback** (the `docker compose stop` step), not at decision-to-rollback. Wall-clock target: < 10 min for the full drill on this data scale.

## Acceptance Criteria

### AC1: Pre-drill state captured — known facts queryable

- **Given** the populated graph from E3-S05 + E3-S06
- **When** I run before any destructive action:
  ```bash
  ssh ct-ai-01 'docker exec graphiti-falkordb redis-cli -a "$FALKORDB_PASSWORD" GRAPH.QUERY default_db "MATCH (n) WHERE n.group_id=\"tom-personal\" RETURN count(n)"' > /tmp/e3-s08-pre-count.txt
  ```
- **And** drive `search_facts(query='graphiti install', group_id='tom-personal')` from Claude Code; capture response to `/tmp/e3-s08-pre-search.json`.
- **Then** pre-count > 0; pre-search returns the install-marker fact text. These are the **golden** values for AC6 comparison.

### AC2: Backup files exist and are recent

- **Given** E3-S07 has run AOF rewrite + BGSAVE + Cypher export (at least once each)
- **When** I run:
  ```bash
  ssh ct-ai-01 'ls -lh /srv/graphiti/data/appendonly.aof /srv/graphiti/data/dump.rdb /srv/graphiti/exports/graphiti-2026-04.json'
  ```
- **Then** all three files exist; AOF and RDB mtimes are within last 24 h; Cypher export within last 30 days.

### AC3: Containers stopped — start-of-rollback clock starts here

- **Given** ACs 1–2
- **When** I run:
  ```bash
  START=$(date +%s)
  ssh ct-ai-01 'cd /srv/graphiti && docker compose down'
  ```
- **Then** `docker compose ps` reports zero running containers (or is empty); `START` is the EQ6 clock-start (operator records it in story evidence).

### AC4: Data directory wiped (the failure simulation)

- **Given** AC3
- **When** I run:
  ```bash
  ssh ct-ai-01 'sudo rm -rf /srv/graphiti/data && sudo mkdir -p /srv/graphiti/data'
  ```
- **Then** `ls -A /srv/graphiti/data` returns empty — the data dir is empty as if we'd just provisioned `ct-ai-01` for the first time.

### AC5: Restore from backup files

- **Given** AC4 (data wiped) and the backup files captured at AC2 from a separate location (per ADR-007 §Layer-2: copy from `/backup/$DATE/` or rely on the in-place AOF/RDB if they were preserved before the wipe)
- **When** I follow the ADR-007 §Restore-drill-protocol step 3 — copy backup to data dir:
  ```bash
  # If the operator's nightly backup pattern keeps a snapshot at /backup/graphiti/<date>/:
  ssh ct-ai-01 'sudo cp /backup/graphiti/$(date -d yesterday +%Y-%m-%d)/appendonly.aof /srv/graphiti/data/'
  ssh ct-ai-01 'sudo cp /backup/graphiti/$(date -d yesterday +%Y-%m-%d)/dump.rdb /srv/graphiti/data/'
  # Alternative path (no separate snapshot location): preserve copies before AC4:
  #   ssh ct-ai-01 'sudo cp /srv/graphiti/data/{appendonly.aof,dump.rdb} /tmp/' BEFORE running AC4
  #   ssh ct-ai-01 'sudo cp /tmp/{appendonly.aof,dump.rdb} /srv/graphiti/data/'   AFTER AC4
  ssh ct-ai-01 'sudo chown -R 999:999 /srv/graphiti/data'
  ```
- **Then** `ls /srv/graphiti/data/` shows the restored files; ownership is correct for FalkorDB container UID.

### AC6: Stack restarts and recall returns the install marker

- **Given** AC5
- **When** I run:
  ```bash
  ssh ct-ai-01 'cd /srv/graphiti && docker compose --env-file .env up -d'
  sleep 20
  ssh ct-ai-01 'docker compose ps'
  ssh ct-ai-01 'docker compose exec falkordb redis-cli -a "$FALKORDB_PASSWORD" PING'
  ssh ct-ai-01 'docker compose exec falkordb redis-cli -a "$FALKORDB_PASSWORD" GRAPH.QUERY default_db "MATCH (n) WHERE n.group_id=\"tom-personal\" RETURN count(n)"' > /tmp/e3-s08-post-count.txt
  ```
- **And** drive `search_facts(query='graphiti install', group_id='tom-personal')` from Claude Code; capture to `/tmp/e3-s08-post-search.json`.
- **Then**:
  - `PING` returns `PONG`
  - `diff /tmp/e3-s08-pre-count.txt /tmp/e3-s08-post-count.txt` shows zero or near-zero difference (zero-difference is the gold standard; if AOF was not flushed before AC4, up-to-1-fact-loss is acceptable and documented)
  - The install-marker fact is in the post-search JSON (text similarity match against pre-search content)

### AC7: End-of-rollback clock — total drill < 10 min

- **Given** ACs 3–6
- **When** I record `END=$(date +%s)` after AC6 verification passes
- **Then** `END - START` (seconds) is < 600 (i.e. < 10 min wall-clock); operator records the value in story evidence; this seeds FR-DEP-007 G-Rollback gate baseline (E4-S08 will measure the full-stack version, not just FalkorDB).

### AC8: Smoke tests 1–3 from runbook §7 pass against restored data

- **Given** AC6
- **When** I re-run the install-runbook §7 smoke tests 1, 2, 3 (write probe, read probe, bi-temporal) — leveraging the `graphiti-smoke.sh` script from E3-S06 AC7 — against the restored stack
- **Then** all three exit PASS; no `JSONDecodeError` in `docker compose logs graphiti-mcp` for the restore window.

### AC9: Restore drill recorded in operator journal

- **Given** ACs 1–8
- **When** I write a one-page restore-drill record at `_bmad-output/evidence/E3-S08-restore-drill-2026-04-25.md` per ADR-007 §Validation
- **Then** the record contains: pre/post counts, pre/post search results, total wall-clock, any deviations from the procedure, and the next quarterly drill date (2026-07-25 or thereabouts) added to the operator's calendar / weekly retro template (FR-OBS-004).

### AC10: Recovery path validated if drill fails

- **Given** any AC failure in 1–8
- **When** I cannot recover the populated state from backup
- **Then**:
  1. Document the failure mode in the journal
  2. Recreate empty: `ssh ct-ai-01 'cd /srv/graphiti && docker compose down && sudo rm -rf /srv/graphiti/data && sudo mkdir -p /srv/graphiti/data && docker compose --env-file .env up -d'`
  3. Re-ingest probe data per E3-S05 AC1
  4. File a Sprint-3 bug story to investigate the backup gap before E3-S09 decision gate

## Implementation Notes

- **Schedule the drill outside an active Claude Code session.** The destructive window is < 10 min but during that window Graphiti is offline; FR-MEM-013 graceful-degradation covers operator continuity, but the drill-time-of-day should be quiet.
- **Backup-source ambiguity (ADR-007 didn't specify a backup directory layout):** ADR-007 references `/backup/$DATE/appendonly.aof` but the operator's existing ZFS snapshot pattern (architecture §5.4) doesn't necessarily expose files that path. **Resolve at drill time:**
  - If ZFS snapshots are mounted at `/.zfs/snapshot/<snap-name>/...`, copy from that path.
  - If `rsnapshot` is in use, copy from `/.snapshots/daily.0/srv/graphiti/data/`.
  - **Most pragmatic for the first drill:** AC5's "alternative path" — preserve copies *before* AC4 to `/tmp/` and restore from there. This proves the AOF/RDB files themselves are restore-correct without depending on the ZFS snapshot machinery (which is its own validation surface, separate concern).
- **AOF replay vs RDB load order:** Redis prefers AOF if both files are present (via `aof-use-rdb-preamble` config). The drill proves AOF replay; for the RDB-only test, run a second drill in Q3 and document.
- **Capturing stdout/stderr:** all destructive steps `tee` to `/tmp/e3-s08-drill.log`. The log is the audit trail.
- **No need to re-run E3-S05 + E3-S06 after recovery.** The probe data is the test artefact; if it returns post-restore, the drill passes. Re-running the full smoke suite would test the restored stack but doesn't test the *restore* — that's AC8 (a quick smoke 1-2-3 against the same data).
- **Quarterly drill cadence reminder:** add a calendar entry / cron-driven ntfy at 90-day intervals (operator preference); the drill is mandatory per ADR-007 §Validation.

## Test Plan

```bash
# AC1 — golden capture
ssh ct-ai-01 'docker exec graphiti-falkordb redis-cli -a "$(grep ^FALKORDB_PASSWORD= /srv/graphiti/.env | cut -d= -f2)" GRAPH.QUERY default_db "MATCH (n) WHERE n.group_id=\"tom-personal\" RETURN count(n)"' > /tmp/e3-s08-pre-count.txt
script -q /tmp/e3-s08-pre-search.log claude
# inside: "Use graphiti search_facts for 'graphiti install', group_id='tom-personal'."
cp /tmp/e3-s08-pre-search.log /tmp/e3-s08-pre-search.json   # archive

# AC2
ssh ct-ai-01 'ls -lh /srv/graphiti/data/appendonly.aof /srv/graphiti/data/dump.rdb /srv/graphiti/exports/graphiti-2026-04.json'

# AC3 — START clock + tear-down
START=$(date +%s); echo "START=$START"
ssh ct-ai-01 'cd /srv/graphiti && docker compose down' | tee /tmp/e3-s08-drill.log

# Pre-AC4: preserve backup copies if no separate snapshot dir is in use
ssh ct-ai-01 'sudo cp /srv/graphiti/data/appendonly.aof /tmp/aof.bak && sudo cp /srv/graphiti/data/dump.rdb /tmp/rdb.bak'

# AC4 — wipe
ssh ct-ai-01 'sudo rm -rf /srv/graphiti/data && sudo mkdir -p /srv/graphiti/data' | tee -a /tmp/e3-s08-drill.log
ssh ct-ai-01 'ls -A /srv/graphiti/data'   # expect empty

# AC5 — restore
ssh ct-ai-01 'sudo cp /tmp/aof.bak /srv/graphiti/data/appendonly.aof && sudo cp /tmp/rdb.bak /srv/graphiti/data/dump.rdb && sudo chown -R 999:999 /srv/graphiti/data' | tee -a /tmp/e3-s08-drill.log

# AC6 — restart + verify
ssh ct-ai-01 'cd /srv/graphiti && docker compose --env-file .env up -d' | tee -a /tmp/e3-s08-drill.log
sleep 20
ssh ct-ai-01 'docker compose -f /srv/graphiti/docker-compose.yml ps'
ssh ct-ai-01 'docker compose -f /srv/graphiti/docker-compose.yml exec -T falkordb redis-cli -a "$(grep ^FALKORDB_PASSWORD= /srv/graphiti/.env | cut -d= -f2)" PING'
ssh ct-ai-01 'docker exec graphiti-falkordb redis-cli -a "$(grep ^FALKORDB_PASSWORD= /srv/graphiti/.env | cut -d= -f2)" GRAPH.QUERY default_db "MATCH (n) WHERE n.group_id=\"tom-personal\" RETURN count(n)"' > /tmp/e3-s08-post-count.txt
diff /tmp/e3-s08-pre-count.txt /tmp/e3-s08-post-count.txt   # expect identical

script -q /tmp/e3-s08-post-search.log claude
# inside: "Use graphiti search_facts for 'graphiti install', group_id='tom-personal'."
diff <(grep -i install /tmp/e3-s08-pre-search.log) <(grep -i install /tmp/e3-s08-post-search.log)   # expect non-empty post = pre

# AC7 — END clock
END=$(date +%s); echo "END=$END"
ELAPSED=$((END - START)); echo "Total: ${ELAPSED}s"
[ $ELAPSED -lt 600 ] && echo "PASS: under 10 min" || echo "FAIL: over 10 min"

# AC8 — smoke 1-2-3 against restored data
./homelab-playbook/scripts/graphiti-smoke.sh   # full suite; expect 0 exit code
ssh ct-ai-01 'docker compose -f /srv/graphiti/docker-compose.yml logs graphiti-mcp 2>&1 | grep -ic JSONDecodeError'   # expect 0

# AC9 — journal entry; manual edit
$EDITOR _bmad-output/evidence/E3-S08-restore-drill-2026-04-25.md
```

## Dependencies

- **Blocks:** E3-S09 (decision gate cites the drill as evidence of FR-MEM-014 fully met). Partially blocks E4-S08 (full-stack rollback drill — this story is the FalkorDB-tier evidence).
- **Blocked by:** E3-S07 (backup machinery must exist), E3-S05 + E3-S06 (probe data populates the graph for the meaningful drill).

## Risks and Mitigations

| Risk | Mitigation |
|---|---|
| AOF restore fails (file format incompatible across FalkorDB versions) | Pin the `falkordb/falkordb:<tag>` exactly across drill (E3-S01 AC2); document the tag in the drill journal |
| Backup files were corrupt at capture time (silent corruption) | AC8 smoke tests against restored data are the binary pass/fail; if probe data missing post-restore, the corruption was real and pre-existed |
| AC4 wipes a path the operator didn't realise was elsewhere-mounted (loss outside Graphiti scope) | `/srv/graphiti/data` is the only path touched; cross-check with `df` before AC4 |
| Container UID mismatch after `chown` causes startup failure | AC5 explicit `chown -R 999:999`; if container fails to start, `docker compose logs falkordb` shows permission error → re-chown |
| Drill takes > 10 min (AC7 fails) → G-Rollback baseline shifts | Document; investigate slow path (AOF replay time vs container startup); report to E4-S08 as the partial baseline |
| Operator runs drill during active session (graceful-degradation drill collides) | Implementation note: schedule drill outside active sessions; FR-MEM-013 was already validated in E3-S06 AC5 |
| ZFS snapshot path doesn't exist on this LXC (Layer-2 backup absent) | AC5's "alternative path" — copy to `/tmp/` before wipe — works; document the resolution and update ADR-007 §Restore-drill-protocol Step 3 |

## Definition of Done

- [ ] All ACs (AC1–AC9) pass
- [ ] AC10 path executed only if AC1–AC8 fail (otherwise skipped)
- [ ] `_bmad-output/evidence/E3-S08-restore-drill-2026-04-25.md` written and committed
- [ ] `/tmp/e3-s08-drill.log` archived to story evidence
- [ ] Pre/post count diff is zero (or documented one-fact loss with rationale)
- [ ] Total drill time recorded; < 10 min target met (or fail mode documented)
- [ ] Quarterly drill calendar entry added (2026-07-25 ± 5 days)
- [ ] FR-MEM-014 status flipped from "documented" to "documented + exercised"
- [ ] Acceptance test stub `AT-FR-MEM-014b` (read-side restore) referenced in `tests/acceptance.md`
- [ ] G-Rollback partial validation note added to E4-S08 dependency tracking
- [ ] EQ6 closed (clock-start at start-of-rollback, recorded in epics §9)
