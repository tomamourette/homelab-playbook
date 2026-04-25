---
type: story
epic: E3
id: E3-S07
title: "Implement Graphiti backup (AOF + daily AOF rewrite + weekly RDB + monthly Cypher export)"
size: 1.5d
priority: MUST
fr_refs: [FR-MEM-012, FR-MEM-014]
adr_refs: [ADR-007, ADR-001]
status: draft
date: 2026-04-25
---

# E3-S07: Implement Graphiti backup (AOF + daily AOF rewrite + weekly RDB + monthly Cypher export)

## User Story

As **tomamourette** (homelab operator), I want **the three-layer backup strategy from ADR-007 implemented and running on `ct-ai-01` — in-process AOF (default-on), daily `BGREWRITEAOF` cron at 03:00, weekly `BGSAVE` cron Sundays at 03:30, and monthly Cypher JSON export at 04:00 on the 1st**, so that **a hardware/data-loss event has near-zero RPO, the FalkorDB binary format isn't a vendor-lock-in trap (monthly portable JSON is the exit-ramp insurance), and FR-MEM-014 backup-mechanism-exercised is half-met (E3-S08 covers the actual restore drill — that's the *only* way you know your backups work)**.

## Background and Context

ADR-007 prescribes the cadence and the exact `redis-cli` commands. FalkorDB inherits Redis's AOF + RDB dual durability — `appendonly yes` is on by default, so write-loss tolerance is already at the last `fsync` boundary. The crons compact AOF (keeps replay time bounded) and force RDB snapshots (gives ZFS-snapshotable point-in-time markers). The monthly Cypher export is the architectural exit-ramp insurance for ADR-001 (FalkorDB choice) — if FalkorDB becomes unmaintained, replay any monthly export into Neo4j or Kuzu via a bespoke importer.

Per architecture §5.4, the operator already has a nightly `zfs send` / rsnapshot pattern covering `/srv/graphiti/data` — this story drops the in-container compaction/snapshot crons that make those ZFS captures coherent. Without `BGREWRITEAOF`, replay time grows unboundedly; without `BGSAVE`, ZFS snapshots may catch FalkorDB mid-write.

## Acceptance Criteria

### AC1: AOF is on by default (verify, don't change)

- **Given** the FalkorDB container from E3-S01
- **When** I run `docker compose -f /srv/graphiti/docker-compose.yml exec falkordb redis-cli -a "$FALKORDB_PASSWORD" CONFIG GET appendonly`
- **Then** the response is `appendonly` `yes`. (No action; just verification.)

### AC2: cron entry installed at `/etc/cron.d/graphiti-backup` on ct-ai-01

- **Given** ADR-007 §Layer-2 cron block
- **When** I commit `homelab-playbook/roles/ai-dev-graphiti/files/cron.d/graphiti-backup` (verbatim from ADR-007) and deploy it to `ct-ai-01:/etc/cron.d/graphiti-backup`
- **Then**:
  - `ls -l /etc/cron.d/graphiti-backup` returns mode `0644`, owner `root:root`
  - `crontab -l` (or `cat /etc/cron.d/graphiti-backup`) shows two lines (with comments):
    - `0 3 * * * docker exec graphiti-falkordb redis-cli -a "$FALKORDB_PASSWORD" BGREWRITEAOF >> /var/log/graphiti-backup.log 2>&1`
    - `30 3 * * 0 docker exec graphiti-falkordb redis-cli -a "$FALKORDB_PASSWORD" BGSAVE >> /var/log/graphiti-backup.log 2>&1`
  - `systemctl status cron` is `active (running)`

### AC3: `cypher-export.sh` script committed and tested manually

- **Given** ADR-007 §Layer-3 script template
- **When** I commit `homelab-playbook/roles/ai-dev-graphiti/files/cypher-export.sh` and deploy to `/srv/graphiti/scripts/cypher-export.sh` (mode 0755) per Implementation Notes
- **Then**:
  - `bash /srv/graphiti/scripts/cypher-export.sh > /tmp/e3-s07-test-export.json 2>&1`
  - `jq . < /tmp/e3-s07-test-export.json | head -20` parses successfully (the script emits JSON the Cypher server returns; any wrapping must be valid JSON)
  - File size > 0 bytes; node count from the export ≥ 1 (matches at least the install marker from E3-S05)

### AC4: monthly Cypher export cron entry added to `/etc/cron.d/graphiti-backup`

- **Given** AC3 + AC2
- **When** I append the third cron line:
  - `0 4 1 * * /srv/graphiti/scripts/cypher-export.sh > /srv/graphiti/exports/graphiti-$(date +%Y-%m).json 2>> /var/log/graphiti-backup.log`
- **Then** `cat /etc/cron.d/graphiti-backup | grep -c "^[0-9]"` returns 3 (three active cron lines: daily AOF, weekly RDB, monthly Cypher). Exports directory `/srv/graphiti/exports/` exists with mode `0755`.

### AC5: First daily AOF rewrite runs successfully

- **Given** ACs 1–2
- **When** I manually trigger the daily cron line (or wait for 03:00 — manual trigger is faster):
  ```bash
  ssh ct-ai-01 'docker exec graphiti-falkordb redis-cli -a "$FALKORDB_PASSWORD" BGREWRITEAOF >> /var/log/graphiti-backup.log 2>&1'
  ```
- **Then** `tail -20 /var/log/graphiti-backup.log` shows a line like `Background append only file rewriting started by pid ...` (or equivalent Redis-module success message); no error follows within 60 s; `journalctl --since 5.minutes.ago | grep -i graphiti-backup` shows no failures.

### AC6: First weekly BGSAVE runs successfully

- **Given** ACs 1–2
- **When** I manually trigger:
  ```bash
  ssh ct-ai-01 'docker exec graphiti-falkordb redis-cli -a "$FALKORDB_PASSWORD" BGSAVE >> /var/log/graphiti-backup.log 2>&1'
  ```
- **Then** `tail /var/log/graphiti-backup.log` shows `Background saving started`; within 30 s, `ls -lh /srv/graphiti/data/dump.rdb` shows a fresh file (mtime within last minute) > 0 bytes.

### AC7: First monthly Cypher export runs and writes to `/srv/graphiti/exports/`

- **Given** ACs 3–4
- **When** I manually trigger:
  ```bash
  ssh ct-ai-01 'sudo /srv/graphiti/scripts/cypher-export.sh > /srv/graphiti/exports/graphiti-$(date +%Y-%m).json 2>> /var/log/graphiti-backup.log'
  ```
- **Then** `ls -lh /srv/graphiti/exports/graphiti-2026-04.json` shows a file > 0 bytes; `jq . < /srv/graphiti/exports/graphiti-2026-04.json | head` parses; the export contains the install marker from E3-S05.

### AC8: ZFS-snapshot pattern coverage of `/srv/graphiti/data` documented

- **Given** the operator's existing nightly ZFS-snapshot pattern (per project memory + architecture §5.4)
- **When** I add `/srv/graphiti/data` to the documented snapshot inventory at `homelab-playbook/docs/runbooks/backup-inventory.md` (or equivalent existing doc)
- **Then** the doc lists `/srv/graphiti/data` with retention 14 daily + 8 weekly + 3 monthly per ADR-007 §Layer-2-retention; `zfs list -t snapshot | grep graphiti` (after the next nightly run) shows at least one snapshot in the next 24 h.

### AC9: Combined disk footprint check

- **Given** ACs 5–7 ran
- **When** I run `du -sh /srv/graphiti/data /srv/graphiti/exports`
- **Then** combined size is < 5 GB at this data scale (NFR-FOOTPRINT-003 — combined backup data + exports stays within budget). At week-1 scale the realistic number is < 50 MB total.

### AC10: Log rotation policy applies to `/var/log/graphiti-backup.log`

- **Given** AC2
- **When** I commit `homelab-playbook/roles/ai-dev-graphiti/files/logrotate.d/graphiti-backup` (monthly rotate, 6 keep, compress)
- **Then** `logrotate -d /etc/logrotate.d/graphiti-backup` dry-runs without errors.

## Implementation Notes

**`/etc/cron.d/graphiti-backup` (verbatim from ADR-007 §Layer-2-3):**

```cron
# Graphiti backup cadence — ADR-007
# Daily 03:00 — rewrite AOF (compact, bounded replay time)
0 3 * * * root docker exec graphiti-falkordb redis-cli -a "${FALKORDB_PASSWORD}" BGREWRITEAOF >> /var/log/graphiti-backup.log 2>&1

# Weekly Sunday 03:30 — force RDB snapshot
30 3 * * 0 root docker exec graphiti-falkordb redis-cli -a "${FALKORDB_PASSWORD}" BGSAVE >> /var/log/graphiti-backup.log 2>&1

# Monthly 1st 04:00 — Cypher export (exit-ramp insurance)
0 4 1 * * root /srv/graphiti/scripts/cypher-export.sh > /srv/graphiti/exports/graphiti-$(date +\%Y-\%m).json 2>> /var/log/graphiti-backup.log
```

**Important:** `/etc/cron.d/` files require an explicit user column (`root` after the time spec). The ADR-007 example omitted this — fix in implementation. Also: `%` in cron must be escaped as `\%`.

**`FALKORDB_PASSWORD` exposure to cron:** the cron runs as root and needs the password. Two acceptable patterns:
- **Pattern A (chosen):** source `/srv/graphiti/.env` from the cron line itself — `(. /srv/graphiti/.env && docker exec ...)` wrap. Keeps secret in mode-600 .env only.
- **Pattern B:** `/etc/default/graphiti-backup` mode 600 (root-owned) carrying `FALKORDB_PASSWORD=...`; `/etc/cron.d/graphiti-backup` sources it. Slightly cleaner; doubles the secret surface.

Implement **Pattern A** unless ops review prefers B.

**`cypher-export.sh` (verbatim from ADR-007 §Layer-3):**

```bash
#!/usr/bin/env bash
set -euo pipefail
. /srv/graphiti/.env
docker exec graphiti-falkordb redis-cli -a "${FALKORDB_PASSWORD}" \
  GRAPH.QUERY default_db \
  "MATCH (n)-[r]->(m) RETURN n, r, m" --no-auth-warning
```

Output is the raw `redis-cli` text response. For a true JSON export, post-process with `redis-cli --json` if FalkorDB version supports it; otherwise the text-format export is still replayable into Neo4j via a small Python script (operator builds at recovery time, not now — the export FILE is the insurance, the importer is built on demand).

**`logrotate.d/graphiti-backup`:**

```
/var/log/graphiti-backup.log {
    monthly
    rotate 6
    compress
    delaycompress
    missingok
    notifempty
    create 0644 root root
}
```

**ZFS snapshot inventory entry:**

```markdown
| Path | Pool | Frequency | Retention | Owner |
|---|---|---|---|---|
| /srv/graphiti/data | rpool/graphiti or pve3 dataset | nightly | 14d + 8w + 3m | tomamourette |
```

## Test Plan

```bash
# AC1
ssh ct-ai-01 'docker compose -f /srv/graphiti/docker-compose.yml exec -T falkordb redis-cli -a "$(grep ^FALKORDB_PASSWORD= /srv/graphiti/.env | cut -d= -f2)" CONFIG GET appendonly'

# AC2 — install cron file
sudo scp homelab-playbook/roles/ai-dev-graphiti/files/cron.d/graphiti-backup ct-ai-01:/etc/cron.d/graphiti-backup
ssh ct-ai-01 'sudo chown root:root /etc/cron.d/graphiti-backup && sudo chmod 0644 /etc/cron.d/graphiti-backup'
ssh ct-ai-01 'cat /etc/cron.d/graphiti-backup'
ssh ct-ai-01 'systemctl status cron'

# AC3 — install + test cypher-export.sh
sudo scp homelab-playbook/roles/ai-dev-graphiti/files/cypher-export.sh ct-ai-01:/srv/graphiti/scripts/cypher-export.sh
ssh ct-ai-01 'sudo chmod 0755 /srv/graphiti/scripts/cypher-export.sh'
ssh ct-ai-01 'bash /srv/graphiti/scripts/cypher-export.sh' > /tmp/e3-s07-test-export.json 2>&1
jq . < /tmp/e3-s07-test-export.json | head -20    # parses
ls -l /tmp/e3-s07-test-export.json

# AC4 — exports dir + check 3 active cron lines
ssh ct-ai-01 'sudo mkdir -p /srv/graphiti/exports && sudo chmod 0755 /srv/graphiti/exports'
ssh ct-ai-01 'grep -c "^[0-9]" /etc/cron.d/graphiti-backup'    # expect 3

# AC5 — manual AOF rewrite
ssh ct-ai-01 'sudo touch /var/log/graphiti-backup.log && sudo chmod 0644 /var/log/graphiti-backup.log'
ssh ct-ai-01 'docker exec graphiti-falkordb redis-cli -a "$(grep ^FALKORDB_PASSWORD= /srv/graphiti/.env | cut -d= -f2)" BGREWRITEAOF'
sleep 30
ssh ct-ai-01 'tail -20 /var/log/graphiti-backup.log'

# AC6 — manual BGSAVE
ssh ct-ai-01 'docker exec graphiti-falkordb redis-cli -a "$(grep ^FALKORDB_PASSWORD= /srv/graphiti/.env | cut -d= -f2)" BGSAVE'
sleep 30
ssh ct-ai-01 'ls -lh /srv/graphiti/data/dump.rdb'

# AC7 — manual Cypher export
ssh ct-ai-01 'sudo /srv/graphiti/scripts/cypher-export.sh > /srv/graphiti/exports/graphiti-$(date +%Y-%m).json 2>> /var/log/graphiti-backup.log'
ssh ct-ai-01 'ls -lh /srv/graphiti/exports/graphiti-2026-04.json'
ssh ct-ai-01 'jq . < /srv/graphiti/exports/graphiti-2026-04.json | head'

# AC8 — verify ZFS coverage
ssh ct-ai-01 'zfs list -t snapshot | grep graphiti | head'

# AC9
ssh ct-ai-01 'du -sh /srv/graphiti/data /srv/graphiti/exports'

# AC10
ssh ct-ai-01 'sudo logrotate -d /etc/logrotate.d/graphiti-backup 2>&1 | grep -i error || echo NO_ERRORS'
```

## Dependencies

- **Blocks:** E3-S08 (restore drill — the actual safety-net validation; this story creates the artefacts E3-S08 restores from). Blocks E3-S09 partially (KPI gate references the backup-exercised state).
- **Blocked by:** E3-S05 + E3-S06 (graph must be populated with probe data so AC3/AC7 export contains real content).

## Risks and Mitigations

| Risk | Mitigation |
|---|---|
| `FALKORDB_PASSWORD` leaking into cron logs | `--no-auth-warning` flag suppresses the redis-cli warning; cron output goes to mode-0644 log but the `-a` value is masked by Redis on first use |
| `BGREWRITEAOF` failure on first run (e.g. disk full) | AC5 catches it; runtime mitigation is the standard `df -h` pre-check on /srv/graphiti pool |
| `cypher-export.sh` produces malformed JSON (FalkorDB version-specific output format) | AC3 `jq` parse is the gate; if it fails, post-process with a 3-line awk wrapper to JSON-encode the redis-cli text output — document in script comments |
| Cron daemon not running on the LXC | AC2 `systemctl status cron` is the gate; if absent, install `cron` package via Ansible |
| `%` not escaped → cron silently runs `date +Y-m` (literally Y-m) | AC4 manual run with the `\%` escape is the verification |
| Pattern A `.env` sourcing leaks secrets to ps output | `docker exec` runs the command inside the container; the password reaches `redis-cli` via stdin, not argv (verify with `ps -ef | grep redis-cli` while running) |
| Combined disk usage exceeds budget at scale (AC9) | NFR-FOOTPRINT-003 < 5 GB threshold; if approached, drop monthly export retention from 12 to 6 months (still > 6 months coverage) |

## Definition of Done

- [ ] All ACs (AC1–AC10) pass
- [ ] `homelab-playbook/roles/ai-dev-graphiti/files/cron.d/graphiti-backup` committed
- [ ] `homelab-playbook/roles/ai-dev-graphiti/files/cypher-export.sh` committed (mode 0755 in role)
- [ ] `homelab-playbook/roles/ai-dev-graphiti/files/logrotate.d/graphiti-backup` committed
- [ ] Backup inventory doc updated with `/srv/graphiti/data` entry
- [ ] One manual run each of AOF rewrite, BGSAVE, Cypher export captured in `/var/log/graphiti-backup.log` and archived to story evidence
- [ ] `/srv/graphiti/exports/graphiti-2026-04.json` exists (the first month's exit-ramp insurance file)
- [ ] Acceptance test stubs `AT-FR-MEM-012a`, `AT-FR-MEM-014a` (write-side; read-side is E3-S08) referenced in `tests/acceptance.md`
- [ ] Architectural exit-ramp doc updated: "to leave FalkorDB, take any monthly export from /srv/graphiti/exports/ + replay via importer" (links to ADR-001 §Exit Ramp)
