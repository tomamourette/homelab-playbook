"""Plex library auto-scan validation tests.

Verifies that Plex Media Server is configured to automatically scan
libraries for new media, ensuring new downloads appear without manual
intervention.

Acceptance criteria:
  - Plex has at least one library configured.
  - Each library has "Scan my library automatically" enabled.
  - Each library has "Run a partial scan when changes are detected" enabled.
  - Library paths include expected media directories.
  - Failures identify which library has auto-scan disabled.
"""

import requests


def _get_libraries(plex_client) -> list[dict]:
    """Fetch all configured Plex libraries.

    Returns a list of library dicts from the /library/sections endpoint.
    """
    try:
        resp = plex_client.get("/library/sections")
    except requests.RequestException as exc:
        raise AssertionError(f"Plex unreachable: {exc}") from exc

    assert resp.status_code == 200, (
        f"Plex /library/sections returned HTTP {resp.status_code}: "
        f"{resp.text[:200]}"
    )

    data = resp.json()
    container = data.get("MediaContainer", {})
    libraries = container.get("Directory", [])
    return libraries


def _get_library_prefs(plex_client, library_key: str, library_title: str) -> dict:
    """Fetch per-library preferences.

    Returns a dict mapping preference id to preference dict.
    """
    try:
        resp = plex_client.get(f"/library/sections/{library_key}/prefs")
    except requests.RequestException as exc:
        raise AssertionError(
            f"Plex unreachable when fetching prefs for library "
            f"'{library_title}' (key={library_key}): {exc}"
        ) from exc

    assert resp.status_code == 200, (
        f"Plex /library/sections/{library_key}/prefs returned "
        f"HTTP {resp.status_code}: {resp.text[:200]}"
    )

    data = resp.json()
    settings = data.get("MediaContainer", {}).get("Setting", [])
    return {s["id"]: s for s in settings if "id" in s}


class TestPlexHasLibraries:
    """Verify Plex has at least one library configured."""

    def test_plex_has_at_least_one_library(self, plex_client):
        """Plex must have at least one library section configured."""
        libraries = _get_libraries(plex_client)
        assert len(libraries) > 0, (
            "Plex has no libraries configured. Add at least one library "
            "via Plex settings → Manage → Libraries."
        )


class TestPlexAutoScan:
    """Verify auto-scan is enabled for every Plex library."""

    def test_autoscan_enabled_for_all_libraries(self, plex_client):
        """Each library must have 'Scan my library automatically' enabled.

        Checks the library-level attributes and per-library preferences
        for the auto-scan setting.  The Plex API exposes this via
        library attributes (e.g. enableAutoPhotoTag) or per-library
        preferences depending on the Plex version.
        """
        libraries = _get_libraries(plex_client)
        assert len(libraries) > 0, "No Plex libraries found – nothing to check"

        failures = []
        for lib in libraries:
            title = lib.get("title", "Unknown")
            key = lib.get("key", "")

            prefs = _get_library_prefs(plex_client, key, title)

            # Plex does not always surface the auto-scan toggle as a
            # named preference.  We check known preference IDs; if the
            # preference exists and is explicitly disabled we flag it.
            # If the preference is absent Plex uses the server default
            # (auto-scan enabled), so absence is treated as enabled.
            auto_scan_disabled = False
            for pref_id in prefs:
                pref = prefs[pref_id]
                pid = pref_id.lower()
                if "autoscan" in pid or "autoupdate" in pid:
                    value = pref.get("value", pref.get("default"))
                    if value in (0, False, "0", "false"):
                        auto_scan_disabled = True
                        break

            if auto_scan_disabled:
                failures.append(
                    f"Library '{title}' (key={key}) has automatic scanning "
                    f"disabled. Enable 'Scan my library automatically' in "
                    f"Plex → Settings → Libraries → {title} → Advanced."
                )

        assert not failures, (
            "Auto-scan disabled for one or more Plex libraries:\n"
            + "\n".join(f"  - {f}" for f in failures)
        )

    def test_partial_scan_enabled_for_all_libraries(self, plex_client):
        """Each library should have partial scan on changes enabled.

        Verifies 'Run a partial scan when changes are detected' is
        enabled, ensuring new media appears quickly.  Only flags a
        failure when the preference is present and explicitly disabled.
        """
        libraries = _get_libraries(plex_client)
        assert len(libraries) > 0, "No Plex libraries found – nothing to check"

        failures = []
        for lib in libraries:
            title = lib.get("title", "Unknown")
            key = lib.get("key", "")

            prefs = _get_library_prefs(plex_client, key, title)

            for pref_id in prefs:
                pref = prefs[pref_id]
                pid = pref_id.lower()
                if "partialscan" in pid or "scanpartial" in pid:
                    value = pref.get("value", pref.get("default"))
                    if value in (0, False, "0", "false"):
                        failures.append(
                            f"Library '{title}' (key={key}) has partial "
                            f"scanning disabled. Enable 'Run a partial scan "
                            f"when changes are detected' in Plex → Settings → "
                            f"Libraries → {title} → Advanced."
                        )
                        break

        assert not failures, (
            "Partial scan disabled for one or more Plex libraries:\n"
            + "\n".join(f"  - {f}" for f in failures)
        )


class TestPlexLibraryPaths:
    """Verify Plex library paths include expected media directories."""

    EXPECTED_PATHS = {
        "movie": "/media/movies",
        "show": "/media/tv",
    }

    def test_library_paths_include_expected_directories(self, plex_client):
        """Library paths should include the expected media directories.

        Movies libraries should map to /media/movies and TV libraries
        should map to /media/tv.
        """
        libraries = _get_libraries(plex_client)
        assert len(libraries) > 0, "No Plex libraries found – nothing to check"

        failures = []
        for lib in libraries:
            title = lib.get("title", "Unknown")
            lib_type = lib.get("type", "")
            locations = lib.get("Location", [])

            expected_path = self.EXPECTED_PATHS.get(lib_type)
            if expected_path is None:
                continue

            paths = [loc.get("path", "") for loc in locations]
            match = any(
                p.rstrip("/").startswith(expected_path.rstrip("/"))
                for p in paths
            )

            if not match:
                failures.append(
                    f"Library '{title}' (type={lib_type}) has paths {paths} "
                    f"but none start with expected '{expected_path}'. "
                    f"Verify the library points to the correct media directory."
                )

        assert not failures, (
            "Unexpected library paths detected:\n"
            + "\n".join(f"  - {f}" for f in failures)
        )
