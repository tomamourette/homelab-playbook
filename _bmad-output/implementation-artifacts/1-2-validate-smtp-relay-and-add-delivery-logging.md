# Story 1.2: Validate SMTP Relay and Add Delivery Logging

**Epic:** 1 - SMTP Relay
**Status:** done
**Implements:** FR31
**Target repo:** homelab-apps

---

## User Story

**As a** homelab operator,
**I want** to verify the SMTP relay sends email successfully and logs failed deliveries,
**So that** I have confidence notifications will work before deploying downstream services.

---

## Acceptance Criteria

### AC1: End-to-end email delivery validation
**Given** the smtp-relay container is running
**When** a test email is sent via `swaks` or `sendmail` from the host using `localhost:25`
**Then** the email arrives at the configured recipient address

### AC2: Failed delivery logging
**Given** the relay encounters a delivery failure (invalid credentials, upstream down)
**When** the relay attempts to send
**Then** the failure is logged to the container's stdout/stderr
**And** the operator can view the failure via `docker logs smtp-relay`

### AC3: Stack targets entry
**Given** the smtp-relay stack is deployed
**When** `stack-targets.yml` is checked
**Then** it includes the smtp-relay stack with its target host (ct-docker-01)

---

## Tasks

- [x] Add Postfix mail log volume mount for persistent log access
- [x] Configure Postfix to log to stdout (verify boky/postfix default behavior)
- [x] Create validation script `stacks/smtp-relay/scripts/validate-smtp.sh`
  - [x] Send test email via localhost:25
  - [x] Check delivery status in logs
  - [x] Display recent delivery failures
  - [x] Usage instructions for operator
- [x] Update `stack-targets.yml` to include smtp-relay on ct-docker-01
- [x] Verify docker logs capture Postfix delivery success/failure messages

---

## Dev Notes

### Postfix Logging in boky/postfix

The `boky/postfix` image routes Postfix logs to stdout by default via rsyslog configuration. This means:
- `docker logs smtp-relay` shows all mail delivery activity
- The json-file logging driver (already configured in Story 1.1) captures and rotates these logs
- No additional syslog configuration needed for FR31 compliance

### Delivery Failure Visibility

Postfix logs include:
- `status=sent` for successful deliveries
- `status=deferred` for temporary failures (retry later)
- `status=bounced` for permanent failures (bad address, rejected)
- Connection errors to upstream relay (auth failures, network issues)

All visible via `docker logs smtp-relay` or `docker logs smtp-relay 2>&1 | grep -E "status=(deferred|bounced)"`.

### Validation Script

The validation script provides a repeatable way to:
1. Confirm SMTP relay is accepting connections
2. Send a test email
3. Check delivery status in logs
4. Surface any recent failures

Requires `swaks` (Swiss Army Knife for SMTP) or falls back to basic `nc`-based SMTP test.

### stack-targets.yml

Adding smtp-relay to the ct-docker-01 endpoint list. This enables CI/CD to trigger the correct Portainer webhook for this stack.

---

## Testing Strategy

### Manual Verification

1. `docker compose up -d` - verify container starts with new config
2. `docker logs smtp-relay` - verify Postfix logs are visible
3. Run `scripts/validate-smtp.sh` - confirm end-to-end delivery
4. Simulate failure (invalid upstream creds) - confirm failure appears in `docker logs`
5. Verify `stack-targets.yml` includes smtp-relay entry

---

## File List

| File | Action | Path |
|------|--------|------|
| docker-compose.yml | Modified | `stacks/smtp-relay/docker-compose.yml` |
| validate-smtp.sh | Created | `stacks/smtp-relay/scripts/validate-smtp.sh` |
| stack-targets.yml | Modified | `stack-targets.yml` |

---

## Change Log

| Date | Change | Author |
|------|--------|--------|
| 2026-04-01 | Story created (Phase 1: CREATE-STORY) | Claude |
| 2026-04-01 | Implementation complete (Phase 2: DEV-STORY) | Claude |
| 2026-04-01 | Code review and fixes applied (Phase 3: CODE-REVIEW) | Claude |

---

## Review Findings

| # | Severity | Finding | Resolution |
|---|----------|---------|------------|
| R1 | Medium | Log volume `/var/log:rw` is overly broad — exposes entire container log directory and could conflict with rsyslog. | Scoped to `/var/log/mail:rw` which is where Postfix writes mail.log specifically. |
| R2 | Medium | Validation script uses `$recipient` in grep regex — email metacharacters (e.g., `+`) would break matching. | Changed to `grep -F` for fixed-string matching of the recipient address. |
| R3 | Medium | nc fallback in validation script sends `\n` only — SMTP protocol (RFC 5321) requires `\r\n` line endings. | Replaced `echo` with `printf` using explicit `\r\n` CRLF endings. |
| R4 | Low | nc availability not checked before use in status command. | Accepted — nc is a standard tool on Debian/Ubuntu; validation script already documents prerequisites. |

### Review Compliance Checklist

- [x] FR31: Failed deliveries logged to stdout and visible via `docker logs smtp-relay` and `validate-smtp.sh failures`
- [x] Architecture patterns: Docker Compose conventions followed (log volume uses /opt/appdata/ path)
- [x] Security: No hardcoded secrets, no external port exposure, script uses 127.0.0.1 only
- [x] stack-targets.yml: smtp-relay added to ct-docker-01 endpoint
- [x] Validation script: covers status, test, logs, and failure inspection use cases
