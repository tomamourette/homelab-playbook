# Story 5.1: Create Restic Backup Ansible Role

**Epic:** 5 - Backup and Recovery
**Status:** ready-for-dev
**Implements:** FR1, FR2, FR6
**Target repo:** homelab-infra

---

## User Story

**As a** homelab operator,
**I want** an Ansible role that installs and configures Restic with systemd timers on both hosts,
**So that** nightly encrypted backups run automatically without manual intervention.

---

## Acceptance Criteria

### AC1: Restic installation and repository initialization
**Given** the `restic-backup` Ansible role is applied to ct-docker-01 and ct-media-01
**When** the role completes
**Then** Restic is installed on both hosts
**And** the Restic repository is initialized at the configured path (default `/mnt/backups/restic/`)
**And** backup data is encrypted at rest with AES-256 (NFR-SEC-2)

### AC2: Nightly systemd timer
**Given** the role installs systemd units
**When** the timer fires at 02:00 nightly (ARCH-3)
**Then** the backup service executes the backup script
**And** all `/opt/appdata/` paths on the target host are backed up
**And** retention is applied: 7 daily, 4 weekly, 3 monthly snapshots (default, overridable)

### AC3: Backend-agnostic configuration (FR6)
**Given** the role defaults define the backup target
**When** the operator changes the target from local to NAS to S3
**Then** only the `restic_backup_repo` variable changes; no backup job reconfiguration needed
**And** the `RESTIC_REPOSITORY` environment variable is set from the configurable variable

### AC4: Role conventions
**Given** the role follows homelab-infra conventions
**When** inspected
**Then** variables are prefixed with `restic_backup_`
**And** all tasks are tagged with `restic-backup`
**And** tasks are idempotent (re-running does not create duplicates or errors)
**And** the repo password is stored in an Ansible-templated env file (NFR-SEC-6)

### AC5: Structured logging (ARCH-9)
**Given** the backup script runs
**When** it produces output
**Then** all log lines follow `[ISO8601] [OK/FAIL] restic-backup: message` format

---

## Tasks

- [ ] Create `ansible/roles/restic-backup/defaults/main.yml`
  - [ ] `restic_backup_repo` — repository path (default: `/mnt/backups/restic/{{ inventory_hostname }}`)
  - [ ] `restic_backup_password` — repository password (no default, must be set)
  - [ ] `restic_backup_paths` — list of paths to back up (default: `[/opt/appdata]`)
  - [ ] `restic_backup_exclude_patterns` — list of exclude patterns
  - [ ] `restic_backup_keep_daily` — daily retention count (default: 7)
  - [ ] `restic_backup_keep_weekly` — weekly retention count (default: 4)
  - [ ] `restic_backup_keep_monthly` — monthly retention count (default: 3)
  - [ ] `restic_backup_schedule` — systemd timer OnCalendar (default: `*-*-* 02:00:00`)
  - [ ] `restic_backup_env_file_path` — path for env file (default: `/etc/restic-backup.env`)
- [ ] Create `ansible/roles/restic-backup/tasks/main.yml`
  - [ ] Install restic package via apt
  - [ ] Create env file from template (contains RESTIC_REPOSITORY and RESTIC_PASSWORD)
  - [ ] Initialize restic repository (idempotent — skip if already initialized)
  - [ ] Deploy backup script from template
  - [ ] Deploy systemd service unit from template
  - [ ] Deploy systemd timer unit from template
  - [ ] Enable and start the systemd timer
- [ ] Create `ansible/roles/restic-backup/handlers/main.yml`
  - [ ] Handler to reload systemd daemon
  - [ ] Handler to restart restic-backup timer
- [ ] Create `ansible/roles/restic-backup/templates/restic-backup.sh.j2`
  - [ ] Source env file for RESTIC_REPOSITORY and RESTIC_PASSWORD
  - [ ] Iterate backup paths with structured log output
  - [ ] Run `restic forget` with retention policy after backup
  - [ ] Exit with non-zero on any failure
- [ ] Create `ansible/roles/restic-backup/templates/restic-backup.service.j2`
  - [ ] Type=oneshot systemd service
  - [ ] ExecStart pointing to backup script
  - [ ] EnvironmentFile directive for secrets
- [ ] Create `ansible/roles/restic-backup/templates/restic-backup.timer.j2`
  - [ ] OnCalendar with configurable schedule
  - [ ] Persistent=true to catch missed runs
  - [ ] RandomizedDelaySec for jitter

---

## Dev Notes

### Architecture Compliance Requirements

| # | Requirement | Source |
|---|------------|--------|
| 1 | systemd timers, NOT cron | Architecture: Scheduled Task Patterns |
| 2 | Variable prefix `restic_backup_*` | Architecture: Ansible Role Patterns |
| 3 | All tasks tagged `restic-backup` | Architecture: Ansible Role Patterns |
| 4 | Idempotent tasks | Architecture: Ansible Role Patterns |
| 5 | Handlers for service restarts | Architecture: Ansible Role Patterns |
| 6 | Structured logging `[ISO8601] [OK/FAIL]` | Architecture: Logging & Output Patterns (ARCH-9) |
| 7 | Password in env file, not in task | NFR-SEC-6 |
| 8 | Backup target = `/mnt/backups/restic/` | Architecture: Backup & Recovery decisions |
| 9 | Retention: 7d/4w/3m | Architecture: Backup & Recovery decisions |
| 10 | Backend-agnostic repo path | FR6 |

### Existing Role Conventions (from docker-host, dev-host, media-host)

- Single `tasks/main.yml` (no `include_tasks` splitting)
- `apt` module for package installation with `state: present`
- `systemd` module for service management
- `file` module for directory creation
- `template` module for Jinja2 files
- Comment header at top of tasks/main.yml describing the role

### Security Notes

- `restic_backup_password` MUST be set via host_vars, group_vars, or vault — never committed in plaintext
- The env file at `/etc/restic-backup.env` is mode 0600, owned by root
- Restic encrypts all data at rest with AES-256 using the repository password

---

## Dependencies

- **Depends on:** Story 1.2 (SMTP relay — for future failure notifications in Story 5.2)
- **Blocks:** Story 5.2 (failure notification service)

---

## Files Created

| File | Purpose |
|------|---------|
| `ansible/roles/restic-backup/defaults/main.yml` | Configurable role variables |
| `ansible/roles/restic-backup/tasks/main.yml` | Role tasks |
| `ansible/roles/restic-backup/handlers/main.yml` | Handlers for systemd reload/restart |
| `ansible/roles/restic-backup/templates/restic-backup.sh.j2` | Backup script with structured logging |
| `ansible/roles/restic-backup/templates/restic-backup.service.j2` | systemd service unit |
| `ansible/roles/restic-backup/templates/restic-backup.timer.j2` | systemd timer unit |
