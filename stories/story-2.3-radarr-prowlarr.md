# Story 2.3: Radarr-Prowlarr Integration Test

**Epic:** Epic 2: Media Pipeline Validation & Automated Fixes
**Story:** 2.3 (Radarr-Prowlarr Integration)

## Goal

Create an integration test `tests/pipeline/test_radarr_prowlarr.py` that verifies Radarr is correctly configured to use Prowlarr as its indexer source. This validates the "Search" capability of the media pipeline.

## Acceptance Criteria

1.  **Test File:** `tests/pipeline/test_radarr_prowlarr.py` exists.
2.  **Indexer Config Check:** The test queries Radarr's `/api/v3/indexer` endpoint and asserts that at least one indexer is present (or specifically a Prowlarr-managed one).
3.  **Search Validation:** The test triggers a search for a known movie (e.g., "Sintel" or a specific TMDB ID) via Radarr's API to confirm it can talk to the indexers.
    *   *Alternative:* If triggering a full search is too heavy/async, verify the "Test" endpoint for the indexer returns success.
4.  **Failure Diagnosis:** If the test fails, report whether it's due to "No Indexers Configured" or "Indexer Connection Failed".

## Technical Approach

### 1. Indexer Verification
*   GET `/api/v3/indexer`
*   Loop through results. Look for `implementation: "Torznab"` or name containing "Prowlarr".
*   Assert `enable: true`.

### 2. Connection Test (Preferred over Full Search)
Radarr has a `test` endpoint for indexers.
*   POST `/api/v3/indexer/test` with the indexer's ID/body.
*   Assert response is valid.

### 3. Fixtures
Reuse `radarr_client` and `prowlarr_client`.

## Dependencies

*   `conftest.py` fixtures (Story 2.1)

## Definition of Done

*   [ ] `tests/pipeline/test_radarr_prowlarr.py` created.
*   [ ] Test verifies Radarr has active indexers.
*   [ ] Test verifies those indexers are reachable (via Radarr's test endpoint).
