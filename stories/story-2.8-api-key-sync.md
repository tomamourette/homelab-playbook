# Story 2.8: API Key Synchronization Fix Generator

**Epic:** Epic 2: Media Pipeline Validation & Automated Fixes
**Story:** 2.8 (API Key Synchronization Fix Generator)

## Goal

Create a tool/script that detects API key authentication failures from test results and automatically generates Pull Requests to update the affected service configurations with the correct API keys.

## Acceptance Criteria

1.  **Detection:** Identify integration failures caused by invalid API keys (based on `pytest` output or specific health check failures).
2.  **Extraction:** Extract the current valid API key from the target service (e.g., Radarr, Sonarr, Prowlarr) using its internal configuration file or a known secure source.
3.  **Remediation:** Update the corresponding environment variable in the target repository's Docker Compose or `.env` file.
4.  **PR Generation:** Create a Pull Request in the target repository (`homelab-apps` or `homelab-infra`) with the updated configuration.
5.  **Documentation:** The PR description clearly identifies which service integration was fixed and why.

## Technical Approach

### 1. Failure Analysis
*   Parse `pytest` JSON output or scan logs for `401 Unauthorized` or specific "Invalid API Key" error messages.

### 2. API Key Extraction
*   Connect to the target container/host via SSH.
*   Read the service configuration file (e.g., `/config/config.xml` for *arr services).
*   Extract the `<ApiKey>` value.

### 3. File Update
*   Locate the service definition in `homelab-apps`.
*   Update the `RADARR_API_KEY` (or similar) variable.

### 4. Git Workflow
*   Checkout a fix branch: `fix/api-key-sync-<service>`.
*   Commit and push.
*   Open PR via API.

## Dependencies

*   Story 1.5 (PR Generation logic)
*   Story 2.2 (Service health checks)

## Definition of Done

*   [ ] Fix generator script created in `tools/remediation/`.
*   [ ] Script can extract API keys from Radarr/Sonarr/Prowlarr config files.
*   [ ] Script can update target repo files.
*   [ ] Script generates a valid PR for an API key mismatch.
