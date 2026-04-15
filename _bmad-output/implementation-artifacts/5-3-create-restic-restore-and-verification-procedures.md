# Story 5.3: Create Restic Restore and Verification Procedures

**Epic:** 5 - Backup and Recovery
**Status:** done
**Implements:** FR3, FR4, FR5
**Target repo:** homelab-infra

---

## User Story

**As a** homelab operator,
**I want** documented and tested procedures for listing snapshots, verifying integrity, and restoring data,
**So that** I can confidently recover from any failure within 1 hour.

---

## Acceptance Criteria

### AC1: List available snapshots (FR3)
**Given** the operator wants to list available snapshots
**When** they run `restic-restore.sh list`
**Then** they see a list of snapshots with timestamps, paths, and sizes
**And** output can be filtered by `--latest N` or `--path /some/path`

### AC2: Restore from snapshot (FR4)
**Given** the operator wants to restore a specific stack's data
**When** they run `restic-restore.sh restore <snapshot-id>` (original path) or `--target /alt/path`
**Then** the data is restored to the specified location
**And** the `--include` flag allows restoring a single subdirectory

### AC3: Verify backup integrity (FR5)
**Given** the operator wants to verify backup integrity
**When** they run `restic-restore.sh verify`
**Then** it executes `restic check` against the repository
**And** reports integrity status without performing a full restore
**And** `--read-data` flag enables full data verification (slower)

### AC4: Structured logging (ARCH-9)
**Given** any subcommand runs
**When** it produces output
**Then** all log lines follow `[ISO8601] [OK/FAIL] restic-restore: message` format

### AC5: Safety confirmation for original-path restore
**Given** the operator runs restore without `--target`
**When** the script is in an interactive terminal
**Then** it prompts for confirmation before overwriting original files

---

## Implementation Details

### Architecture Compliance

| # | Requirement | Source | Status |
|---|------------|--------|--------|
| 1 | Variable prefix `restic_backup_*` | Architecture: Ansible Role Patterns | Done |
| 2 | All tasks tagged `restic-backup` | Architecture: Ansible Role Patterns | Done |
| 3 | Idempotent deployment task | Architecture: Ansible Role Patterns | Done |
| 4 | Structured logging `[ISO8601] [OK/FAIL]` | Architecture: Logging & Output Patterns (ARCH-9) | Done |
| 5 | CLI-based restore | Architecture: Backup & Recovery decisions | Done |
| 6 | Env file sourcing (manual run vs systemd) | D-502 pattern from Story 5.1 | Done |

### Script Subcommands

| Subcommand | FR | Description |
|------------|-----|-------------|
| `list` | FR3 | Shows snapshots with timestamps, paths; supports `--latest N`, `--path` filters; includes repo stats |
| `restore` | FR4 | Restores snapshot to original (`--target /`) or alternate path; `--include` for single subdirectory |
| `verify` | FR5 | Runs `restic check` (metadata only by default); `--read-data` for full data verification |

---

## Files Created / Modified

| File | Action | Purpose |
|------|--------|---------|
| `ansible/roles/restic-backup/templates/restic-restore.sh.j2` | **Created** | Restore/verify script with list, restore, verify subcommands |
| `ansible/roles/restic-backup/tasks/main.yml` | **Modified** | Added 1 task: deploy restore script |
| `ansible/roles/restic-backup/defaults/main.yml` | **Modified** | Added `restic_backup_restore_script_path` variable |

### New Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `restic_backup_restore_script_path` | `/usr/local/bin/restic-restore.sh` | Restore script location |

---

## Dependencies

- **Depends on:** Story 5.1 (restic-backup role), Story 5.2 (failure notifications)
- **Blocks:** Story 5.4 (backup status Grafana dashboard)

---

## Review Findings

| # | Date | Story | Finding | Severity | Resolution |
|---|------|-------|---------|----------|------------|
| R-507 | 2026-04-01 | 5.3 | Snapshot validation via `grep -q '"id"'` is fragile -- `restic snapshots <id> --json` returns `[]` for unknown snapshots, not an error | Medium | Changed to explicit check for empty/null/`[]` JSON output instead of grep for `"id"` string |
