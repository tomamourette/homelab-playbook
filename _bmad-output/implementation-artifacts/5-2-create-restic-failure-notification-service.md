# Story 5.2: Create Restic Failure Notification Service

**Epic:** 5 - Backup and Recovery
**Status:** done
**Implements:** FR1 (no silent failures), NFR-REL-1
**Target repo:** homelab-infra

---

## User Story

**As a** homelab operator,
**I want** a systemd service that sends an email when a backup fails,
**So that** I am never surprised by silent backup failures.

---

## Acceptance Criteria

### AC1: OnFailure triggers notification
**Given** the `restic-backup.service` systemd unit is configured
**When** the backup job fails (non-zero exit code)
**Then** the `OnFailure=restic-notify-failure@%n.service` directive triggers
**And** the failure notification service sends an email via `localhost:25` (SMTP relay)
**And** the email includes the hostname, timestamp, and failure reason

### AC2: No email on success
**Given** the backup completes successfully
**When** the timer fires
**Then** no failure email is sent

---

## Implementation Details

### Architecture Compliance

| # | Requirement | Source | Status |
|---|------------|--------|--------|
| 1 | systemd OnFailure= directive | Architecture: Scheduled Task Patterns | Done |
| 2 | SMTP via localhost:25 | Architecture: SMTP relay bound to 127.0.0.1:25 | Done |
| 3 | Variable prefix `restic_backup_*` | Architecture: Ansible Role Patterns | Done |
| 4 | All tasks tagged `restic-backup` | Architecture: Ansible Role Patterns | Done |
| 5 | Idempotent tasks | Architecture: Ansible Role Patterns | Done |
| 6 | Structured logging `[ISO8601] [OK/FAIL]` | Architecture: Logging & Output Patterns (ARCH-9) | Done |
| 7 | Conditional deployment via `restic_backup_notify_enabled` | Opt-in pattern | Done |

### Email Content

The failure notification email includes:
- Hostname and failed service name
- ISO 8601 timestamp
- Last 50 lines of journald output from the failed unit
- Troubleshooting steps (journalctl, systemctl, manual re-run commands)

### Mail Transport Strategy

1. **sendmail** (preferred) -- used if available on the host (provided by any local MTA)
2. **nc** (fallback) -- raw SMTP protocol via netcat, zero dependencies beyond base system
   - Uses CRLF line endings per RFC 5321
   - Implements dot-stuffing per RFC 5321 section 4.5.2
   - 10-second timeout to prevent hangs

---

## Files Created / Modified

| File | Action | Purpose |
|------|--------|---------|
| `ansible/roles/restic-backup/templates/restic-notify-failure.sh.j2` | **Created** | Failure notification script with sendmail/nc fallback |
| `ansible/roles/restic-backup/templates/restic-notify-failure.service.j2` | **Created** | systemd oneshot service unit (template instance) |
| `ansible/roles/restic-backup/templates/restic-backup.service.j2` | **Modified** | Added OnFailure= directive in [Unit] section |
| `ansible/roles/restic-backup/tasks/main.yml` | **Modified** | Added 3 tasks: validate recipient, deploy script, deploy service |
| `ansible/roles/restic-backup/defaults/main.yml` | **Modified** | Added 6 notification variables |

### New Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `restic_backup_notify_enabled` | `true` | Enable/disable failure notifications |
| `restic_backup_notify_recipient` | `""` | Recipient email (required when enabled) |
| `restic_backup_notify_sender` | `restic-backup@{{ inventory_hostname }}` | From address |
| `restic_backup_notify_smtp_host` | `localhost` | SMTP relay host |
| `restic_backup_notify_smtp_port` | `25` | SMTP relay port |
| `restic_backup_notify_script_path` | `/usr/local/bin/restic-notify-failure.sh` | Script location |

---

## Dependencies

- **Depends on:** Story 5.1 (restic-backup role), Story 1.2 (SMTP relay)
- **Blocks:** Story 5.3 (restore and verification procedures)

---

## Review Findings

| # | Finding | Severity | Resolution |
|---|---------|----------|------------|
| R-505 | OnFailure= is a [Unit] directive, not [Service]; initial placement in [Service] would be ignored by systemd | High | Moved OnFailure= to [Unit] section |
| R-506 | Fractional sleep values (0.5) in nc SMTP function may not work on all systems; journal log lines starting with '.' could prematurely terminate DATA section | Medium | Changed to integer sleeps; added RFC 5321 dot-stuffing via sed |
