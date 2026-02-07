# Story 2.5: Download Path Validation Test

**Epic:** Epic 2: Media Pipeline Validation & Automated Fixes
**Story:** 2.5 (Download Path Validation)

## Goal

Create a test `tests/pipeline/test_download_paths.py` that verifies download paths are correctly aligned between qBittorrent and *arr services (Radarr/Sonarr), ensuring completed downloads can be detected and imported.

## Acceptance Criteria

1.  **Test File:** `tests/pipeline/test_download_paths.py` exists.
2.  **qBittorrent Path Check:** Query qBittorrent's default download directory via `/api/v2/app/preferences`.
3.  **Radarr Path Check:** Query Radarr's download client settings and verify the path matches qBittorrent.
4.  **Sonarr Path Check:** Query Sonarr's download client settings and verify the path matches qBittorrent.
5.  **Failure Reporting:** If paths don't match, report which service has the mismatch and what the expected path should be.

## Technical Approach

### 1. qBittorrent API
*   GET `/api/v2/app/preferences`
*   Extract `save_path` field.

### 2. Radarr API
*   GET `/api/v3/downloadclient`
*   Find the qBittorrent download client entry.
*   Check the configured path.

### 3. Sonarr API
*   GET `/api/v3/downloadclient`
*   Find the qBittorrent download client entry.
*   Check the configured path.

### 4. Path Comparison
*   Assert paths match exactly, or
*   Allow for trailing slash differences, or
*   Check if they resolve to the same mount point.

## Dependencies

*   `conftest.py` fixtures (Story 2.1)

## Definition of Done

*   [ ] `tests/pipeline/test_download_paths.py` created.
*   [ ] Test verifies qBittorrent's save path.
*   [ ] Test verifies Radarr's download client path matches qBittorrent.
*   [ ] Test verifies Sonarr's download client path matches qBittorrent.
*   [ ] Failure messages identify which service has the mismatch.
