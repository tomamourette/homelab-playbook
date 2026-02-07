"""Service health check tests for all 6 media stack services.

Verifies each service is running, reachable via HTTP, and accepting
API authentication. Failures report which service failed and why
(e.g. connection refused vs 401 Unauthorized).
"""

import requests


class TestServiceHealth:
    """Smoke tests verifying each media service is healthy."""

    def test_overseerr_health(self, overseerr_client):
        """Verify Overseerr is reachable via /api/v1/status (public endpoint)."""
        try:
            resp = overseerr_client.get("/api/v1/status")
        except requests.RequestException as exc:
            raise AssertionError(f"Overseerr unreachable: {exc}") from exc

        assert resp.status_code == 200, (
            f"Overseerr returned HTTP {resp.status_code}: {resp.text[:200]}"
        )
        data = resp.json()
        assert data.get("version"), (
            "Overseerr /api/v1/status response missing 'version' field"
        )

    def test_radarr_health(self, radarr_client):
        """Verify Radarr is reachable and API key is accepted."""
        try:
            resp = radarr_client.get("/api/v3/system/status")
        except requests.RequestException as exc:
            raise AssertionError(f"Radarr unreachable: {exc}") from exc

        assert resp.status_code == 200, (
            f"Radarr returned HTTP {resp.status_code}: {resp.text[:200]}"
        )

    def test_sonarr_health(self, sonarr_client):
        """Verify Sonarr is reachable and API key is accepted."""
        try:
            resp = sonarr_client.get("/api/v3/system/status")
        except requests.RequestException as exc:
            raise AssertionError(f"Sonarr unreachable: {exc}") from exc

        assert resp.status_code == 200, (
            f"Sonarr returned HTTP {resp.status_code}: {resp.text[:200]}"
        )

    def test_prowlarr_health(self, prowlarr_client):
        """Verify Prowlarr is reachable and API key is accepted."""
        try:
            resp = prowlarr_client.get("/api/v1/system/status")
        except requests.RequestException as exc:
            raise AssertionError(f"Prowlarr unreachable: {exc}") from exc

        assert resp.status_code == 200, (
            f"Prowlarr returned HTTP {resp.status_code}: {resp.text[:200]}"
        )

    def test_plex_health(self, plex_client):
        """Verify Plex is reachable and token is accepted."""
        try:
            resp = plex_client.get("/status/sessions")
        except requests.RequestException as exc:
            raise AssertionError(f"Plex unreachable: {exc}") from exc

        assert resp.status_code == 200, (
            f"Plex returned HTTP {resp.status_code}: {resp.text[:200]}"
        )

    def test_qbittorrent_health(self, qbittorrent_client):
        """Verify qBittorrent is reachable and login succeeds."""
        try:
            login_resp = qbittorrent_client.login()
        except requests.RequestException as exc:
            raise AssertionError(f"qBittorrent unreachable: {exc}") from exc

        assert login_resp.status_code == 200, (
            f"qBittorrent login returned HTTP {login_resp.status_code}: "
            f"{login_resp.text[:200]}"
        )
        assert login_resp.text.strip() == "Ok.", (
            f"qBittorrent login failed: {login_resp.text[:200]}"
        )

        # After successful login, verify the API is accessible
        try:
            resp = qbittorrent_client.get("/api/v2/app/version")
        except requests.RequestException as exc:
            raise AssertionError(
                f"qBittorrent API unreachable after login: {exc}"
            ) from exc

        assert resp.status_code == 200, (
            f"qBittorrent /api/v2/app/version returned HTTP {resp.status_code}: "
            f"{resp.text[:200]}"
        )
