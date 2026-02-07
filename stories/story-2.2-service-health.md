# Story 2.2: Service Health Check Tests

**Epic:** Epic 2: Media Pipeline Validation & Automated Fixes
**Story:** 2.2 (Service Health Checks)

## Goal

Create a test suite `tests/pipeline/test_service_health.py` that verifies all 6 media services are running, reachable via HTTP, and accepting API authentication. This provides the "smoke test" layer for the infrastructure.

## Acceptance Criteria

1.  **Test File:** `tests/pipeline/test_service_health.py` exists.
2.  **Overseerr Test:** Verify `/api/v1/status` returns 200 (public endpoint).
3.  **Radarr Test:** Verify `/api/v3/system/status` returns 200 (requires API Key).
4.  **Sonarr Test:** Verify `/api/v3/system/status` returns 200 (requires API Key).
5.  **Prowlarr Test:** Verify `/api/v1/system/status` returns 200 (requires API Key).
6.  **Plex Test:** Verify `/status/sessions` returns 200 (requires Token).
7.  **qBittorrent Test:** Verify `/api/v2/app/version` returns 200 (requires Login).
8.  **Output:** Failures must report *which* service failed (e.g., "Radarr connection refused" vs "Radarr 401 Unauthorized").

## Technical Approach

Use the fixtures created in Story 2.1 (`overseerr_client`, `radarr_client`, etc.).

### Test Structure
```python
def test_overseerr_health(overseerr_client):
    """Verify Overseerr is reachable."""
    resp = overseerr_client.get("/api/v1/status")
    assert resp.status_code == 200
    assert resp.json()["version"]  # Basic payload check
```

### qBittorrent Specifics
qBittorrent requires a 2-step login. The `qbittorrent_client` fixture (from Story 2.1) should ideally handle this auto-login, or the test needs to call `.login()` explicitly if the client doesn't do it on init. *Refinement:* Check `api_client.py` implementation — if `QBittorrentClient` has a `login()` method, the fixture should probably call it or the test must.

## Dependencies

*   `conftest.py` fixtures (Story 2.1)

## Definition of Done

*   [ ] `tests/pipeline/test_service_health.py` created.
*   [ ] All 6 tests pass when services are up.
*   [ ] Tests fail with clear errors when services are down/unauthorized.
