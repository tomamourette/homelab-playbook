"""Download path validation tests.

Verifies download paths are correctly aligned between qBittorrent and
*arr services (Radarr/Sonarr), ensuring completed downloads can be
detected and imported.

Radarr/Sonarr qBittorrent download clients do NOT have a directory
override field.  Instead they configure a *category* (movieCategory /
tvCategory).  qBittorrent then downloads into ``save_path/<category>``.
So the correct validation is:

  1. qBittorrent has a non-empty default save_path.
  2. Radarr/Sonarr have a qBittorrent download client with a category set.
  3. That category exists inside qBittorrent.
  4. The category's savePath in qBittorrent is consistent with the
     default save_path (either empty — meaning "use default" — or an
     absolute path rooted at save_path).

Acceptance criteria:
  - qBittorrent's default save_path is retrieved via API.
  - Radarr's movieCategory exists as a qBittorrent category.
  - Sonarr's tvCategory exists as a qBittorrent category.
  - Category save paths are consistent with qBittorrent's save_path.
  - Mismatches report which service disagrees and what the expected path is.
"""

import requests


def _normalize_path(path: str) -> str:
    """Normalize a path by stripping whitespace and trailing slashes."""
    return path.strip().rstrip("/")


def _login_qbittorrent(qbittorrent_client):
    """Log in to qBittorrent, raising AssertionError on failure."""
    try:
        login_resp = qbittorrent_client.login()
    except requests.RequestException as exc:
        raise AssertionError(f"qBittorrent unreachable: {exc}") from exc

    assert login_resp.status_code == 200, (
        f"qBittorrent login failed (HTTP {login_resp.status_code}): "
        f"{login_resp.text[:200]}"
    )


def _get_qbittorrent_save_path(qbittorrent_client) -> str:
    """Retrieve the default save_path from qBittorrent preferences."""
    _login_qbittorrent(qbittorrent_client)

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


def _get_qbittorrent_categories(qbittorrent_client) -> dict:
    """Retrieve configured categories from qBittorrent.

    Returns a dict mapping category name → category info dict.
    Each info dict has at least a ``savePath`` key (may be empty string
    meaning "use default save_path/<category>").
    """
    _login_qbittorrent(qbittorrent_client)

    try:
        resp = qbittorrent_client.get("/api/v2/torrents/categories")
    except requests.RequestException as exc:
        raise AssertionError(
            f"qBittorrent categories endpoint unreachable: {exc}"
        ) from exc

    assert resp.status_code == 200, (
        f"qBittorrent /api/v2/torrents/categories returned "
        f"HTTP {resp.status_code}: {resp.text[:200]}"
    )

    return resp.json()


def _get_arr_qbt_clients(arr_client, service_name: str) -> tuple[list[dict], list]:
    """Return all qBittorrent download clients from a *arr service."""
    try:
        resp = arr_client.get("/api/v3/downloadclient")
    except requests.RequestException as exc:
        raise AssertionError(f"{service_name} unreachable: {exc}") from exc

    assert resp.status_code == 200, (
        f"{service_name} /api/v3/downloadclient returned "
        f"HTTP {resp.status_code}: {resp.text[:200]}"
    )

    clients = resp.json()
    qbt_clients = [
        c for c in clients
        if c.get("implementation") == "QBittorrent"
    ]
    return qbt_clients, clients


def _get_field(client_obj: dict, field_name: str) -> str:
    """Extract a named field value from a *arr download client object."""
    for field in client_obj.get("fields", []):
        if field.get("name") == field_name:
            return field.get("value", "") or ""
    return ""


class TestQBittorrentSavePath:
    """Verify qBittorrent's default download directory is configured."""

    def test_qbittorrent_has_save_path(self, qbittorrent_client):
        """qBittorrent must have a non-empty default save_path."""
        save_path = _get_qbittorrent_save_path(qbittorrent_client)
        assert save_path.startswith("/"), (
            f"qBittorrent save_path '{save_path}' is not an absolute path"
        )


class TestRadarrDownloadPath:
    """Verify Radarr's download client category exists in qBittorrent."""

    def test_radarr_has_qbittorrent_client(self, radarr_client):
        """Radarr must have a qBittorrent download client configured."""
        qbt_clients, all_clients = _get_arr_qbt_clients(radarr_client, "Radarr")
        assert len(qbt_clients) > 0, (
            "Radarr has no qBittorrent download client configured. "
            f"Found {len(all_clients)} download client(s) but none use the "
            "QBittorrent implementation."
        )

    def test_radarr_category_exists_in_qbittorrent(
        self, radarr_client, qbittorrent_client
    ):
        """Radarr's movieCategory must exist as a qBittorrent category."""
        qbt_save_path = _normalize_path(
            _get_qbittorrent_save_path(qbittorrent_client)
        )
        qbt_categories = _get_qbittorrent_categories(qbittorrent_client)

        qbt_clients, _ = _get_arr_qbt_clients(radarr_client, "Radarr")
        assert len(qbt_clients) > 0, (
            "Radarr has no qBittorrent download client – cannot validate path"
        )

        for client_obj in qbt_clients:
            client_name = client_obj.get("name", "unnamed")
            category = _get_field(client_obj, "movieCategory")

            assert category, (
                f"Radarr download client '{client_name}' has no movieCategory "
                f"configured. Without a category, downloads go to qBittorrent's "
                f"default save_path with no separation between movies and other "
                f"content. Set movieCategory in Radarr's download client settings."
            )

            assert category in qbt_categories, (
                f"Radarr download client '{client_name}' uses movieCategory "
                f"'{category}' but qBittorrent has no matching category. "
                f"Available qBittorrent categories: "
                f"{list(qbt_categories.keys()) or '(none)'}. "
                f"Create the '{category}' category in qBittorrent."
            )

            cat_save_path = qbt_categories[category].get("savePath", "")
            if cat_save_path:
                normalized_cat_path = _normalize_path(cat_save_path)
                assert normalized_cat_path.startswith(qbt_save_path), (
                    f"Path mismatch – qBittorrent category '{category}' has "
                    f"savePath '{cat_save_path}' which is not under the default "
                    f"save_path '{qbt_save_path}'. Radarr download client "
                    f"'{client_name}' uses this category and expects downloads "
                    f"to land under '{qbt_save_path}'."
                )


class TestSonarrDownloadPath:
    """Verify Sonarr's download client category exists in qBittorrent."""

    def test_sonarr_has_qbittorrent_client(self, sonarr_client):
        """Sonarr must have a qBittorrent download client configured."""
        qbt_clients, all_clients = _get_arr_qbt_clients(sonarr_client, "Sonarr")
        assert len(qbt_clients) > 0, (
            "Sonarr has no qBittorrent download client configured. "
            f"Found {len(all_clients)} download client(s) but none use the "
            "QBittorrent implementation."
        )

    def test_sonarr_category_exists_in_qbittorrent(
        self, sonarr_client, qbittorrent_client
    ):
        """Sonarr's tvCategory must exist as a qBittorrent category."""
        qbt_save_path = _normalize_path(
            _get_qbittorrent_save_path(qbittorrent_client)
        )
        qbt_categories = _get_qbittorrent_categories(qbittorrent_client)

        qbt_clients, _ = _get_arr_qbt_clients(sonarr_client, "Sonarr")
        assert len(qbt_clients) > 0, (
            "Sonarr has no qBittorrent download client – cannot validate path"
        )

        for client_obj in qbt_clients:
            client_name = client_obj.get("name", "unnamed")
            category = _get_field(client_obj, "tvCategory")

            assert category, (
                f"Sonarr download client '{client_name}' has no tvCategory "
                f"configured. Without a category, downloads go to qBittorrent's "
                f"default save_path with no separation between TV and other "
                f"content. Set tvCategory in Sonarr's download client settings."
            )

            assert category in qbt_categories, (
                f"Sonarr download client '{client_name}' uses tvCategory "
                f"'{category}' but qBittorrent has no matching category. "
                f"Available qBittorrent categories: "
                f"{list(qbt_categories.keys()) or '(none)'}. "
                f"Create the '{category}' category in qBittorrent."
            )

            cat_save_path = qbt_categories[category].get("savePath", "")
            if cat_save_path:
                normalized_cat_path = _normalize_path(cat_save_path)
                assert normalized_cat_path.startswith(qbt_save_path), (
                    f"Path mismatch – qBittorrent category '{category}' has "
                    f"savePath '{cat_save_path}' which is not under the default "
                    f"save_path '{qbt_save_path}'. Sonarr download client "
                    f"'{client_name}' uses this category and expects downloads "
                    f"to land under '{qbt_save_path}'."
                )
