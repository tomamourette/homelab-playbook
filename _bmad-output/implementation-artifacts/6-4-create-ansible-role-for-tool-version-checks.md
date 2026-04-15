# Story 6.4: Create Ansible Role for Tool Version Checks

**Status:** Done
**Implements:** FR26, FR27
**Target repo:** homelab-infra
**Date completed:** 2026-04-01

## Files Created

- `ansible/roles/tool-version-check/defaults/main.yml` — Role defaults with `tool_version_check_*` prefix
- `ansible/roles/tool-version-check/tasks/main.yml` — Deploy script + systemd units
- `ansible/roles/tool-version-check/handlers/main.yml` — systemd daemon reload + timer restart
- `ansible/roles/tool-version-check/templates/tool-check.sh.j2` — Version check script
- `ansible/roles/tool-version-check/templates/tool-check.service.j2` — Systemd oneshot service
- `ansible/roles/tool-version-check/templates/tool-check.timer.j2` — Daily timer at 05:30

## Implementation Notes

### Pattern Alignment
- Follows identical structure to `apt-check` role (Story 6.3)
- Systemd timers per ARCH-3 (not crontab)
- Structured logging per ARCH-9: `[ISO8601] [OK/WARN/FAIL] tool-check: message`
- sendmail-first with nc fallback for SMTP delivery (D-506/D-614 pattern)
- Noise suppression: no email when all tools are current

### Tool Check Strategy
All four tools use GitHub API `releases/latest` endpoint for latest version detection:
- **Terraform:** `terraform version -json` parsed via JSON key extraction
- **Ansible:** `ansible --version` parsed via regex for `ansible.*core` version
- **Node.js:** `node --version` with leading `v` stripped
- **Docker:** `docker --version` parsed via regex for `Docker version` string

### Schedule Staggering
- 05:30 daily (30min after apt-check at 05:00, hours before Diun at 06:00/06:30)
- 300s random delay to avoid thundering herd

### Key Design Decisions
- D-616: Used `binary` field in tool config to decouple display name from command name (e.g., `nodejs` display, `node` binary)
- D-617: Changed Node.js latest version source from `resolve.nodejs.org/lts` to GitHub API for consistency
- D-618: TimeoutStartSec=300 (5 minutes) — shorter than apt-check since no package cache updates needed
- D-619: Schedule at 05:30 daily, staggered from apt-check (05:00) and Diun (06:00)

## Acceptance Criteria Verification

| Criteria | Status |
|----------|--------|
| Checks Terraform, Ansible, Node.js, Docker installed versions | Pass |
| Compares against latest releases via GitHub API | Pass |
| Sends email listing outdated tools | Pass |
| No email when all tools current | Pass |
| Uses systemd timers (ARCH-3) | Pass |
| Variables prefixed `tool_version_check_` | Pass |
| All tasks tagged `tool-version-check` | Pass |
| Structured logging prefix (ARCH-9) | Pass |
