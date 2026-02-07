# Story 2.7: End-to-End Pipeline Test

**Epic:** Epic 2: Media Pipeline Validation & Automated Fixes
**Story:** 2.7 (End-to-End Pipeline Test)

## Goal

Create an end-to-end test `tests/pipeline/test_end_to_end.py` that validates a complete media request flow through the entire automation pipeline, ensuring all integrations work together.

## Acceptance Criteria

1.  **Test File:** `tests/pipeline/test_end_to_end.py` exists.
2.  **Test Scope:** The test validates the pipeline flow:
    *   (Optional) Request media via Overseerr API.
    *   Verify Radarr/Sonarr receives the request.
    *   (Simulated/Dry-Run) Verify search triggers via *arr → Prowlarr.
    *   (Manual Verification) Confirm download initiation in qBittorrent.
    *   (Manual Verification) Confirm import to Plex folder.
    *   (Manual Verification) Verify Plex library includes new media.
3.  **Dry-Run Mode:** The test should support a "dry-run" mode that checks integration readiness without triggering actual downloads.
4.  **Step-by-Step Reporting:** The test outputs detailed progress for each pipeline stage.
5.  **Failure Diagnostics:** If a step fails, report which specific integration point broke.

## Technical Approach

### 1. Request Simulation (Optional)
*   POST to Overseerr `/api/v1/request` with a test movie/show.
*   OR: Query Radarr/Sonarr for existing pending requests.

### 2. Validation Stages
*   **Stage 1:** Verify Overseerr → Radarr/Sonarr handoff.
*   **Stage 2:** Check Radarr/Sonarr search history (via `/api/v3/history`).
*   **Stage 3:** Check qBittorrent for active downloads.
*   **Stage 4:** Check *arr import activity.
*   **Stage 5:** Check Plex library scan logs.

### 3. Dry-Run Mode
Use `pytest.skip()` or a fixture to bypass actual request creation, instead validating that:
*   All API endpoints are reachable.
*   Authentication works.
*   Configuration is correct.

### 4. Manual Steps
For stages that require long wait times (download completion, import), the test should:
*   Print clear instructions for manual verification.
*   Use `pytest.mark.manual` or similar to indicate human intervention needed.

## Dependencies

*   `conftest.py` fixtures (Story 2.1)
*   Stories 2.2-2.6 (integration layer tests)

## Definition of Done

*   [ ] `tests/pipeline/test_end_to_end.py` created.
*   [ ] Test validates all pipeline stages.
*   [ ] Dry-run mode works without triggering downloads.
*   [ ] Progress reporting shows each stage clearly.
*   [ ] Failure messages identify which integration failed.
