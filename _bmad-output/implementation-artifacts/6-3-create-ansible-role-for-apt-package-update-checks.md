# Story 6.3: Create Ansible Role for APT Package Update Checks

**Epic:** 6 - Update Checks
**Status:** done
**Implements:** FR25, FR27
**Target repo:** homelab-infra

---

## User Story

**As a** homelab operator,
**I want** automated checks for available apt package updates on all containers and Proxmox nodes,
**So that** I know about pending system-level updates.

---

## Acceptance Criteria

### AC1: Systemd timer fires daily and checks for updates
**Given** the `apt-check` Ansible role is applied to all containers and Proxmox nodes
**When** the systemd timer fires daily
**Then** the script runs `apt-get update && apt list --upgradable`
**And** sends an email via SMTP relay listing available package updates
**And** produces no email if there are no updates (no noise)

### AC2: Role follows homelab-infra conventions
**Given** the role follows homelab-infra conventions
**When** inspected
**Then** it uses systemd timers (not crontab) per ARCH-3
**And** variables are prefixed with `apt_check_`
**And** all tasks are tagged with `apt-check`
**And** script output uses structured prefix format (ARCH-9)

---

## Files Created

| File | Purpose |
|------|---------|
| `ansible/roles/apt-check/defaults/main.yml` | Default variables: recipient, sender, smtp_host, smtp_port, schedule |
| `ansible/roles/apt-check/tasks/main.yml` | Deploy script + systemd units, validate recipient, enable timer |
| `ansible/roles/apt-check/handlers/main.yml` | systemd daemon-reload and timer restart handlers |
| `ansible/roles/apt-check/templates/apt-check.sh.j2` | Bash script: apt update, check upgradable, send email if updates exist |
| `ansible/roles/apt-check/templates/apt-check.service.j2` | systemd oneshot service unit |
| `ansible/roles/apt-check/templates/apt-check.timer.j2` | systemd daily timer (05:00 with 300s random delay) |

---

## Design Decisions

| Decision | Rationale |
|----------|-----------|
| D-610: SMTP host defaults to 192.168.50.194 | Role targets all hosts; most lack local smtp-relay; cross-host IP pattern from D-605 |
| D-611: Schedule at 05:00 daily | Staggered from Diun (06:00/06:30) and restic-backup (02:00) |
| D-612: No email when zero updates | AC explicitly requires no noise when nothing to report |
| D-613: No ProtectSystem in service unit | apt-get update writes to /var/lib/apt/lists and /var/cache/apt |
| D-614: sendmail-first with nc fallback | Same proven pattern as restic-notify-failure (D-506) |
| D-615: TimeoutStartSec=600 | Prevents hung apt operations; 10 min generous for apt update |

## Review Findings

| Finding | Severity | Resolution |
|---------|----------|------------|
| R-608: `apt list --upgradable` header varies across Debian/Ubuntu | Low | Simplified grep to `^Listing` |
| R-609: ProtectSystem=full breaks apt-get update | Medium | Intentionally omitted; PrivateTmp+NoNewPrivileges still applied |
| R-610: Proxmox nodes may lack sendmail or nc | Low | Accepted -- same as R-108; Proxmox ships ncat |

---

## Implementation Notes

- Follows exact same Ansible role structure as `restic-backup` (tasks, templates, defaults, handlers)
- Email delivery uses identical sendmail/nc pattern from `restic-notify-failure.sh.j2`
- Structured logging follows ARCH-9: `[ISO8601] [OK/WARN/FAIL] apt-check: message`
- Script exits 0 with no email when no packages need updating (noise suppression)
- Script exits 1 only on apt-get update failure (broken mirrors, network issues)
