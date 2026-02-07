# Story 2.6: Plex Library Auto-Scan Test

**Epic:** Epic 2: Media Pipeline Validation & Automated Fixes
**Story:** 2.6 (Plex Library Auto-Scan)

## Goal

Create a test `tests/pipeline/test_plex_autoscan.py` that verifies Plex Media Server is configured to automatically scan libraries for new media, ensuring new downloads appear without manual intervention.

## Acceptance Criteria

1.  **Test File:** `tests/pipeline/test_plex_autoscan.py` exists.
2.  **Library List:** Query Plex for all configured libraries.
3.  **Auto-Scan Check:** For each library, verify:
    *   "Scan my library automatically" is enabled.
    *   "Run a partial scan when changes are detected" is enabled (optional, depending on Plex version).
4.  **Library Path Check (Optional):** Verify library paths include the expected media directories (e.g., `/media/movies`, `/media/tv`).
5.  **Failure Reporting:** If auto-scan is disabled, report which library has it disabled.

## Technical Approach

### 1. Plex API
*   GET `/library/sections` to list all libraries.
*   For each library, check settings:
    *   Look for `enableAutomaticAdd` or similar field.
    *   Check library `Location` array for expected paths.

### 2. Plex Library Settings
Plex stores library settings in the library object returned by `/library/sections`. Key fields:
*   `scanner` - The scanner type (e.g., "Plex Movie Scanner").
*   `refreshing` - Boolean indicating if currently scanning.
*   `Location` - Array of `path` objects.

Auto-scan settings may require additional API calls to `/library/sections/{id}/prefs` if not in the main response.

## Dependencies

*   `conftest.py` fixtures (Story 2.1)

## Definition of Done

*   [ ] `tests/pipeline/test_plex_autoscan.py` created.
*   [ ] Test verifies Plex has at least one library.
*   [ ] Test checks auto-scan settings for each library.
*   [ ] Failure messages identify which library has auto-scan disabled.
