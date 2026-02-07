"""Download path validation tests.

Verifies download paths are correctly aligned between qBittorrent and
*arr services (Radarr/Sonarr), ensuring completed downloads can be
detected and imported.

Acceptance criteria:
  - qBittorrent's default save_path is retrieved via API.
  - Radarr's download client path matches qBittorrent's save_path.
  - Sonarr's download client path matches qBittorrent's save_path.
  - Mismatches report which service disagrees and what the expected path is.
"""

import requests


def _normalize_path(path: str) -> str:
    """Normalize a path by stripping whitespace and trailing slashes."""
    return path.strip().rstrip("/")


def _get_qbittorrent_save_path(qbittorrent_client) -> str:
    """Retrieve the default save_path from qBittorrent preferences."""
    try:
        login_resp = qbittorrent_client.login()
    except requests.RequestException as exc:
        raise AssertionError(f"qBittorrent unreachable: {exc}") from exc

    assert login_resp.status_code == 200, (
        f"qBittorrent login failed (HTTP {login_resp.status_code}): "
        f"{login_resp.text[:200]}"
    )

    try:
        resp = qbittorrent_client.get("/api/v2/app/preferences")
    except requests.RequestException as exc:
        raise AssertionError(
            f"qBittorrent preferences unreachable: {exc}"
        ) from exc

    assert resp.status_code == 200, (
        f"qBittorrent /api/v2/app/preferences returned HTTP {resp.status_code}: "
        f"{resp.text[:200]}"
    )

    prefs = resp.json()
    save_path = prefs.get("save_path", "")
    assert save_path, (
        "qBittorrent preferences response is missing the 'save_path' field"
    )
    return save_path


class TestQBittorrentSavePath:
    """Verify qBittorrent's default download directory is configured."""

    def test_qbittorrent_has_save_path(self, qbittorrent_client):
        """qBittorrent must have a non-empty default save_path."""
        save_path = _get_qbittorrent_save_path(qbittorrent_client)
        assert save_path.startswith("/"), (
            f"qBittorrent save_path '{save_path}' is not an absolute path"
        )


class TestRadarrDownloadPath:
    """Verify Radarr's download client path matches qBittorrent."""

    def test_radarr_has_qbittorrent_client(self, radarr_client):
        """Radarr must have a qBittorrent download client configured."""
        try:
            resp = radarr_client.get("/api/v3/downloadclient")
        except requests.RequestException as exc:
            raise AssertionError(f"Radarr unreachable: {exc}") from exc

        assert resp.status_code == 200, (
            f"Radarr /api/v3/downloadclient returned HTTP {resp.status_code}: "
            f"{resp.text[:200]}"
        )

        clients = resp.json()
        qbt_clients = [
            c for c in clients
            if c.get("implementation") == "QBittorrent"
        ]
        assert len(qbt_clients) > 0, (
            "Radarr has no qBittorrent download client configured. "
            f"Found {len(clients)} download client(s) but none use the "
            "QBittorrent implementation."
        )

    def test_radarr_path_matches_qbittorrent(
        self, radarr_client, qbittorrent_client
    ):
        """Radarr's qBittorrent download path must match qBittorrent's save_path."""
        qbt_save_path = _normalize_path(
            _get_qbittorrent_save_path(qbittorrent_client)
        )

        try:
            resp = radarr_client.get("/api/v3/downloadclient")
        except requests.RequestException as exc:
            raise AssertionError(f"Radarr unreachable: {exc}") from exc

        assert resp.status_code == 200
        clients = resp.json()

        qbt_clients = [
            c for c in clients
            if c.get("implementation") == "QBittorrent"
        ]
        assert len(qbt_clients) > 0, (
            "Radarr has no qBittorrent download client – cannot validate path"
        )

        for qbt_client in qbt_clients:
            client_name = qbt_client.get("name", "unnamed")
            fields = {
                f["name"]: f.get("value", "")
                for f in qbt_client.get("fields", [])
            }

            # The *arr "movieDirectory" or "tvDirectory" field overrides
            # the default save path. If not set, the client uses
            # qBittorrent's save_path directly (optionally with a
            # category subfolder appended).
            arr_path = fields.get("movieDirectory", "") or ""

            if arr_path:
                normalized_arr = _normalize_path(arr_path)
                assert normalized_arr == qbt_save_path, (
                    f"Path mismatch – Radarr download client '{client_name}' "
                    f"has movieDirectory '{arr_path}' but qBittorrent "
                    f"save_path is '{qbt_save_path}'. "
                    f"Expected Radarr to use '{qbt_save_path}'."
                )


class TestSonarrDownloadPath:
    """Verify Sonarr's download client path matches qBittorrent."""

    def test_sonarr_has_qbittorrent_client(self, sonarr_client):
        """Sonarr must have a qBittorrent download client configured."""
        try:
            resp = sonarr_client.get("/api/v3/downloadclient")
        except requests.RequestException as exc:
            raise AssertionError(f"Sonarr unreachable: {exc}") from exc

        assert resp.status_code == 200, (
            f"Sonarr /api/v3/downloadclient returned HTTP {resp.status_code}: "
            f"{resp.text[:200]}"
        )

        clients = resp.json()
        qbt_clients = [
            c for c in clients
            if c.get("implementation") == "QBittorrent"
        ]
        assert len(qbt_clients) > 0, (
            "Sonarr has no qBittorrent download client configured. "
            f"Found {len(clients)} download client(s) but none use the "
            "QBittorrent implementation."
        )

    def test_sonarr_path_matches_qbittorrent(
        self, sonarr_client, qbittorrent_client
    ):
        """Sonarr's qBittorrent download path must match qBittorrent's save_path."""
        qbt_save_path = _normalize_path(
            _get_qbittorrent_save_path(qbittorrent_client)
        )

        try:
            resp = sonarr_client.get("/api/v3/downloadclient")
        except requests.RequestException as exc:
            raise AssertionError(f"Sonarr unreachable: {exc}") from exc

        assert resp.status_code == 200
        clients = resp.json()

        qbt_clients = [
            c for c in clients
            if c.get("implementation") == "QBittorrent"
        ]
        assert len(qbt_clients) > 0, (
            "Sonarr has no qBittorrent download client – cannot validate path"
        )

        for qbt_client in qbt_clients:
            client_name = qbt_client.get("name", "unnamed")
            fields = {
                f["name"]: f.get("value", "")
                for f in qbt_client.get("fields", [])
            }

            arr_path = fields.get("tvDirectory", "") or ""

            if arr_path:
                normalized_arr = _normalize_path(arr_path)
                assert normalized_arr == qbt_save_path, (
                    f"Path mismatch – Sonarr download client '{client_name}' "
                    f"has tvDirectory '{arr_path}' but qBittorrent "
                    f"save_path is '{qbt_save_path}'. "
                    f"Expected Sonarr to use '{qbt_save_path}'."
                )
