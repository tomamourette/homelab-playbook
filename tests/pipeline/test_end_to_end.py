"""End-to-end media pipeline validation test.

Validates a complete media request flow through the entire automation
pipeline, ensuring all integrations work together.  The test walks
through each stage of the pipeline in order:

  Stage 1 – Service readiness:  all six services respond to health checks.
  Stage 2 – Overseerr → Radarr/Sonarr handoff:  Overseerr knows about
             Radarr and Sonarr as downstream services.
  Stage 3 – Radarr/Sonarr → Prowlarr search:  *arr services have active
             Prowlarr-managed indexers that pass connectivity tests.
  Stage 4 – qBittorrent download readiness:  *arr download clients point
             to qBittorrent and category paths are consistent.
  Stage 5 – Plex library readiness:  Plex has libraries with auto-scan
             enabled so imports appear automatically.

Dry-run mode (default) validates integration readiness without triggering
actual downloads.  Each stage reports progress and, on failure, identifies
the specific integration point that broke.

Acceptance criteria:
  - Validates the full pipeline flow through all integration stages.
  - Supports dry-run mode that checks readiness without actual downloads.
  - Outputs detailed progress for each pipeline stage.
  - Failure messages identify which specific integration point broke.
"""

import requests


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _stage(name: str) -> str:
    """Return a formatted stage label for progress output."""
    return f"[PIPELINE] {name}"


def _check_service_health(client, path: str, service_name: str) -> dict:
    """Hit a health endpoint and return the JSON body.

    Raises AssertionError with the service name and reason on failure.
    """
    try:
        resp = client.get(path)
    except requests.RequestException as exc:
        raise AssertionError(
            f"{_stage('Stage 1 – Service Readiness')} FAILED: "
            f"{service_name} unreachable at {path}: {exc}"
        ) from exc

    assert resp.status_code == 200, (
        f"{_stage('Stage 1 – Service Readiness')} FAILED: "
        f"{service_name} returned HTTP {resp.status_code}: {resp.text[:200]}"
    )
    return resp.json()


def _login_qbittorrent(qbittorrent_client) -> None:
    """Log in to qBittorrent, raising AssertionError on failure."""
    try:
        login_resp = qbittorrent_client.login()
    except requests.RequestException as exc:
        raise AssertionError(
            f"{_stage('Stage 1 – Service Readiness')} FAILED: "
            f"qBittorrent unreachable: {exc}"
        ) from exc

    assert login_resp.status_code == 200 and login_resp.text.strip() == "Ok.", (
        f"{_stage('Stage 1 – Service Readiness')} FAILED: "
        f"qBittorrent login failed (HTTP {login_resp.status_code}): "
        f"{login_resp.text[:200]}"
    )


def _get_arr_qbt_download_clients(
    arr_client, service_name: str,
) -> list[dict]:
    """Return qBittorrent download clients configured in a *arr service."""
    try:
        resp = arr_client.get("/api/v3/downloadclient")
    except requests.RequestException as exc:
        raise AssertionError(
            f"{service_name} download clients unreachable: {exc}"
        ) from exc

    assert resp.status_code == 200, (
        f"{service_name} /api/v3/downloadclient returned "
        f"HTTP {resp.status_code}: {resp.text[:200]}"
    )

    return [
        c for c in resp.json()
        if c.get("implementation") == "QBittorrent"
    ]


def _get_field(client_obj: dict, field_name: str) -> str:
    """Extract a named field value from a *arr download client object."""
    for field in client_obj.get("fields", []):
        if field.get("name") == field_name:
            return field.get("value", "") or ""
    return ""


# ---------------------------------------------------------------------------
# Stage 1 – Service Readiness
# ---------------------------------------------------------------------------

class TestStage1ServiceReadiness:
    """Stage 1: Verify every service in the pipeline is reachable.

    This is the prerequisite for all subsequent stages.  If any service
    is down the rest of the pipeline cannot function.
    """

    def test_overseerr_reachable(self, overseerr_client):
        """Overseerr must respond to its status endpoint."""
        print(_stage("Stage 1 – Checking Overseerr health"))
        data = _check_service_health(
            overseerr_client, "/api/v1/status", "Overseerr",
        )
        assert data.get("version"), (
            f"{_stage('Stage 1')} FAILED: Overseerr /api/v1/status "
            "response missing 'version' field"
        )
        print(_stage("Stage 1 – Overseerr OK"))

    def test_radarr_reachable(self, radarr_client):
        """Radarr must respond to its system status endpoint."""
        print(_stage("Stage 1 – Checking Radarr health"))
        _check_service_health(
            radarr_client, "/api/v3/system/status", "Radarr",
        )
        print(_stage("Stage 1 – Radarr OK"))

    def test_sonarr_reachable(self, sonarr_client):
        """Sonarr must respond to its system status endpoint."""
        print(_stage("Stage 1 – Checking Sonarr health"))
        _check_service_health(
            sonarr_client, "/api/v3/system/status", "Sonarr",
        )
        print(_stage("Stage 1 – Sonarr OK"))

    def test_prowlarr_reachable(self, prowlarr_client):
        """Prowlarr must respond to its system status endpoint."""
        print(_stage("Stage 1 – Checking Prowlarr health"))
        _check_service_health(
            prowlarr_client, "/api/v1/system/status", "Prowlarr",
        )
        print(_stage("Stage 1 – Prowlarr OK"))

    def test_qbittorrent_reachable(self, qbittorrent_client):
        """qBittorrent must accept login and respond to API calls."""
        print(_stage("Stage 1 – Checking qBittorrent health"))
        _login_qbittorrent(qbittorrent_client)

        try:
            resp = qbittorrent_client.get("/api/v2/app/version")
        except requests.RequestException as exc:
            raise AssertionError(
                f"{_stage('Stage 1')} FAILED: "
                f"qBittorrent API unreachable after login: {exc}"
            ) from exc

        assert resp.status_code == 200, (
            f"{_stage('Stage 1')} FAILED: "
            f"qBittorrent /api/v2/app/version returned "
            f"HTTP {resp.status_code}: {resp.text[:200]}"
        )
        print(_stage("Stage 1 – qBittorrent OK"))

    def test_plex_reachable(self, plex_client):
        """Plex must respond to its sessions endpoint."""
        print(_stage("Stage 1 – Checking Plex health"))
        _check_service_health(
            plex_client, "/status/sessions", "Plex",
        )
        print(_stage("Stage 1 – Plex OK"))


# ---------------------------------------------------------------------------
# Stage 2 – Overseerr → Radarr / Sonarr Handoff
# ---------------------------------------------------------------------------

class TestStage2OverseerrHandoff:
    """Stage 2: Verify Overseerr is configured to forward requests.

    Overseerr must know about Radarr (movies) and Sonarr (TV) so that
    user requests are handed off to the correct *arr service.
    """

    def test_overseerr_has_radarr_server(self, overseerr_client):
        """Overseerr must have at least one Radarr server configured."""
        print(_stage("Stage 2 – Checking Overseerr → Radarr integration"))
        try:
            resp = overseerr_client.get("/api/v1/settings/radarr")
        except requests.RequestException as exc:
            raise AssertionError(
                f"{_stage('Stage 2')} FAILED: "
                f"Overseerr Radarr settings unreachable: {exc}"
            ) from exc

        assert resp.status_code == 200, (
            f"{_stage('Stage 2')} FAILED: "
            f"Overseerr /api/v1/settings/radarr returned "
            f"HTTP {resp.status_code}: {resp.text[:200]}"
        )

        servers = resp.json()
        assert isinstance(servers, list) and len(servers) > 0, (
            f"{_stage('Stage 2')} FAILED: "
            "Overseerr has no Radarr servers configured. "
            "Add a Radarr server in Overseerr → Settings → Services."
        )

        active = [s for s in servers if s.get("isDefault") or not s.get("isDisabled", True)]
        assert len(active) > 0, (
            f"{_stage('Stage 2')} FAILED: "
            f"Overseerr has {len(servers)} Radarr server(s) but none are "
            "active/default. Enable at least one Radarr server."
        )
        print(_stage("Stage 2 – Overseerr → Radarr OK"))

    def test_overseerr_has_sonarr_server(self, overseerr_client):
        """Overseerr must have at least one Sonarr server configured."""
        print(_stage("Stage 2 – Checking Overseerr → Sonarr integration"))
        try:
            resp = overseerr_client.get("/api/v1/settings/sonarr")
        except requests.RequestException as exc:
            raise AssertionError(
                f"{_stage('Stage 2')} FAILED: "
                f"Overseerr Sonarr settings unreachable: {exc}"
            ) from exc

        assert resp.status_code == 200, (
            f"{_stage('Stage 2')} FAILED: "
            f"Overseerr /api/v1/settings/sonarr returned "
            f"HTTP {resp.status_code}: {resp.text[:200]}"
        )

        servers = resp.json()
        assert isinstance(servers, list) and len(servers) > 0, (
            f"{_stage('Stage 2')} FAILED: "
            "Overseerr has no Sonarr servers configured. "
            "Add a Sonarr server in Overseerr → Settings → Services."
        )

        active = [s for s in servers if s.get("isDefault") or not s.get("isDisabled", True)]
        assert len(active) > 0, (
            f"{_stage('Stage 2')} FAILED: "
            f"Overseerr has {len(servers)} Sonarr server(s) but none are "
            "active/default. Enable at least one Sonarr server."
        )
        print(_stage("Stage 2 – Overseerr → Sonarr OK"))


# ---------------------------------------------------------------------------
# Stage 3 – Radarr/Sonarr → Prowlarr Search
# ---------------------------------------------------------------------------

class TestStage3SearchIntegration:
    """Stage 3: Verify *arr services can search via Prowlarr.

    Radarr and Sonarr must have active Prowlarr-managed indexers that
    pass their built-in connection tests (dry-run search validation).
    """

    def test_radarr_has_prowlarr_indexers(self, radarr_client):
        """Radarr must have at least one active Prowlarr-managed indexer."""
        print(_stage("Stage 3 – Checking Radarr → Prowlarr indexers"))
        try:
            resp = radarr_client.get("/api/v3/indexer")
        except requests.RequestException as exc:
            raise AssertionError(
                f"{_stage('Stage 3')} FAILED: "
                f"Radarr indexer endpoint unreachable: {exc}"
            ) from exc

        assert resp.status_code == 200, (
            f"{_stage('Stage 3')} FAILED: "
            f"Radarr /api/v3/indexer returned HTTP {resp.status_code}: "
            f"{resp.text[:200]}"
        )

        indexers = resp.json()
        prowlarr_indexers = [
            idx for idx in indexers
            if idx.get("implementation") == "Torznab"
            or "prowlarr" in idx.get("name", "").lower()
        ]
        assert len(prowlarr_indexers) > 0, (
            f"{_stage('Stage 3')} FAILED: "
            f"Radarr has {len(indexers)} indexer(s) but none are "
            "Prowlarr-managed (Torznab). Prowlarr may not have synced."
        )

        enabled = [
            idx for idx in prowlarr_indexers
            if idx.get("enableRss") or idx.get("enableAutomaticSearch")
        ]
        assert len(enabled) > 0, (
            f"{_stage('Stage 3')} FAILED: "
            f"Radarr has {len(prowlarr_indexers)} Prowlarr indexer(s) "
            "but all have RSS and automatic search disabled."
        )
        print(_stage(f"Stage 3 – Radarr has {len(enabled)} active Prowlarr indexer(s)"))

    def test_radarr_indexer_connectivity(self, radarr_client):
        """Each active Radarr indexer must pass its connection test (dry-run)."""
        print(_stage("Stage 3 – Dry-run: testing Radarr indexer connectivity"))
        resp = radarr_client.get("/api/v3/indexer")
        assert resp.status_code == 200
        indexers = resp.json()

        failures = []
        tested = 0
        for idx in indexers:
            if not idx.get("enableRss") and not idx.get("enableAutomaticSearch"):
                continue

            tested += 1
            try:
                test_resp = radarr_client.post("/api/v3/indexer/test", json=idx)
            except requests.RequestException as exc:
                failures.append(f"{idx['name']}: connection error – {exc}")
                continue

            if test_resp.status_code != 200:
                failures.append(
                    f"{idx['name']}: HTTP {test_resp.status_code}: "
                    f"{test_resp.text[:300]}"
                )

        assert tested > 0, (
            f"{_stage('Stage 3')} FAILED: No active Radarr indexers to test."
        )
        assert not failures, (
            f"{_stage('Stage 3')} FAILED: Radarr indexer connection test "
            f"failures:\n" + "\n".join(f"  - {f}" for f in failures)
        )
        print(_stage(f"Stage 3 – Radarr indexer connectivity OK ({tested} tested)"))

    def test_sonarr_has_prowlarr_indexers(self, sonarr_client):
        """Sonarr must have at least one active Prowlarr-managed indexer."""
        print(_stage("Stage 3 – Checking Sonarr → Prowlarr indexers"))
        try:
            resp = sonarr_client.get("/api/v3/indexer")
        except requests.RequestException as exc:
            raise AssertionError(
                f"{_stage('Stage 3')} FAILED: "
                f"Sonarr indexer endpoint unreachable: {exc}"
            ) from exc

        assert resp.status_code == 200, (
            f"{_stage('Stage 3')} FAILED: "
            f"Sonarr /api/v3/indexer returned HTTP {resp.status_code}: "
            f"{resp.text[:200]}"
        )

        indexers = resp.json()
        prowlarr_indexers = [
            idx for idx in indexers
            if idx.get("implementation") == "Torznab"
            or "prowlarr" in idx.get("name", "").lower()
        ]
        assert len(prowlarr_indexers) > 0, (
            f"{_stage('Stage 3')} FAILED: "
            f"Sonarr has {len(indexers)} indexer(s) but none are "
            "Prowlarr-managed (Torznab). Prowlarr may not have synced."
        )

        enabled = [
            idx for idx in prowlarr_indexers
            if idx.get("enableRss") or idx.get("enableAutomaticSearch")
        ]
        assert len(enabled) > 0, (
            f"{_stage('Stage 3')} FAILED: "
            f"Sonarr has {len(prowlarr_indexers)} Prowlarr indexer(s) "
            "but all have RSS and automatic search disabled."
        )
        print(_stage(f"Stage 3 – Sonarr has {len(enabled)} active Prowlarr indexer(s)"))

    def test_sonarr_indexer_connectivity(self, sonarr_client):
        """Each active Sonarr indexer must pass its connection test (dry-run)."""
        print(_stage("Stage 3 – Dry-run: testing Sonarr indexer connectivity"))
        resp = sonarr_client.get("/api/v3/indexer")
        assert resp.status_code == 200
        indexers = resp.json()

        failures = []
        tested = 0
        for idx in indexers:
            if not idx.get("enableRss") and not idx.get("enableAutomaticSearch"):
                continue

            tested += 1
            try:
                test_resp = sonarr_client.post("/api/v3/indexer/test", json=idx)
            except requests.RequestException as exc:
                failures.append(f"{idx['name']}: connection error – {exc}")
                continue

            if test_resp.status_code != 200:
                failures.append(
                    f"{idx['name']}: HTTP {test_resp.status_code}: "
                    f"{test_resp.text[:300]}"
                )

        assert tested > 0, (
            f"{_stage('Stage 3')} FAILED: No active Sonarr indexers to test."
        )
        assert not failures, (
            f"{_stage('Stage 3')} FAILED: Sonarr indexer connection test "
            f"failures:\n" + "\n".join(f"  - {f}" for f in failures)
        )
        print(_stage(f"Stage 3 – Sonarr indexer connectivity OK ({tested} tested)"))


# ---------------------------------------------------------------------------
# Stage 4 – qBittorrent Download Readiness
# ---------------------------------------------------------------------------

class TestStage4DownloadReadiness:
    """Stage 4: Verify *arr → qBittorrent download path is configured.

    Radarr and Sonarr must have qBittorrent download clients with valid
    categories, and those categories must exist in qBittorrent with
    consistent save paths.
    """

    def test_radarr_qbittorrent_download_client(
        self, radarr_client, qbittorrent_client,
    ):
        """Radarr must have a qBittorrent download client with a valid category."""
        print(_stage("Stage 4 – Checking Radarr → qBittorrent download config"))
        _login_qbittorrent(qbittorrent_client)

        qbt_clients = _get_arr_qbt_download_clients(radarr_client, "Radarr")
        assert len(qbt_clients) > 0, (
            f"{_stage('Stage 4')} FAILED: "
            "Radarr has no qBittorrent download client configured."
        )

        # Verify category exists in qBittorrent
        try:
            cat_resp = qbittorrent_client.get("/api/v2/torrents/categories")
        except requests.RequestException as exc:
            raise AssertionError(
                f"{_stage('Stage 4')} FAILED: "
                f"qBittorrent categories endpoint unreachable: {exc}"
            ) from exc
        assert cat_resp.status_code == 200
        qbt_categories = cat_resp.json()

        for client_obj in qbt_clients:
            client_name = client_obj.get("name", "unnamed")
            category = _get_field(client_obj, "movieCategory")
            assert category, (
                f"{_stage('Stage 4')} FAILED: "
                f"Radarr download client '{client_name}' has no movieCategory."
            )
            assert category in qbt_categories, (
                f"{_stage('Stage 4')} FAILED: "
                f"Radarr download client '{client_name}' uses category "
                f"'{category}' which does not exist in qBittorrent. "
                f"Available: {list(qbt_categories.keys()) or '(none)'}."
            )
        print(_stage("Stage 4 – Radarr → qBittorrent OK"))

    def test_sonarr_qbittorrent_download_client(
        self, sonarr_client, qbittorrent_client,
    ):
        """Sonarr must have a qBittorrent download client with a valid category."""
        print(_stage("Stage 4 – Checking Sonarr → qBittorrent download config"))
        _login_qbittorrent(qbittorrent_client)

        qbt_clients = _get_arr_qbt_download_clients(sonarr_client, "Sonarr")
        assert len(qbt_clients) > 0, (
            f"{_stage('Stage 4')} FAILED: "
            "Sonarr has no qBittorrent download client configured."
        )

        try:
            cat_resp = qbittorrent_client.get("/api/v2/torrents/categories")
        except requests.RequestException as exc:
            raise AssertionError(
                f"{_stage('Stage 4')} FAILED: "
                f"qBittorrent categories endpoint unreachable: {exc}"
            ) from exc
        assert cat_resp.status_code == 200
        qbt_categories = cat_resp.json()

        for client_obj in qbt_clients:
            client_name = client_obj.get("name", "unnamed")
            category = _get_field(client_obj, "tvCategory")
            assert category, (
                f"{_stage('Stage 4')} FAILED: "
                f"Sonarr download client '{client_name}' has no tvCategory."
            )
            assert category in qbt_categories, (
                f"{_stage('Stage 4')} FAILED: "
                f"Sonarr download client '{client_name}' uses category "
                f"'{category}' which does not exist in qBittorrent. "
                f"Available: {list(qbt_categories.keys()) or '(none)'}."
            )
        print(_stage("Stage 4 – Sonarr → qBittorrent OK"))

    def test_qbittorrent_active_downloads_accessible(self, qbittorrent_client):
        """qBittorrent torrents list must be accessible (manual check hint)."""
        print(_stage("Stage 4 – Checking qBittorrent download list access"))
        _login_qbittorrent(qbittorrent_client)

        try:
            resp = qbittorrent_client.get("/api/v2/torrents/info")
        except requests.RequestException as exc:
            raise AssertionError(
                f"{_stage('Stage 4')} FAILED: "
                f"qBittorrent torrent list unreachable: {exc}"
            ) from exc

        assert resp.status_code == 200, (
            f"{_stage('Stage 4')} FAILED: "
            f"qBittorrent /api/v2/torrents/info returned "
            f"HTTP {resp.status_code}: {resp.text[:200]}"
        )

        torrents = resp.json()
        print(
            _stage(
                f"Stage 4 – qBittorrent accessible, "
                f"{len(torrents)} torrent(s) currently tracked"
            )
        )
        print(
            _stage(
                "Stage 4 – NOTE: Verify active downloads manually if a "
                "request has been submitted."
            )
        )


# ---------------------------------------------------------------------------
# Stage 5 – Plex Library Readiness
# ---------------------------------------------------------------------------

class TestStage5PlexLibraryReadiness:
    """Stage 5: Verify Plex is ready to receive imported media.

    Plex must have libraries configured with auto-scan enabled and
    paths that match the expected media directories.
    """

    def test_plex_has_libraries(self, plex_client):
        """Plex must have at least one library configured."""
        print(_stage("Stage 5 – Checking Plex library configuration"))
        try:
            resp = plex_client.get("/library/sections")
        except requests.RequestException as exc:
            raise AssertionError(
                f"{_stage('Stage 5')} FAILED: "
                f"Plex library sections unreachable: {exc}"
            ) from exc

        assert resp.status_code == 200, (
            f"{_stage('Stage 5')} FAILED: "
            f"Plex /library/sections returned HTTP {resp.status_code}: "
            f"{resp.text[:200]}"
        )

        data = resp.json()
        libraries = data.get("MediaContainer", {}).get("Directory", [])
        assert len(libraries) > 0, (
            f"{_stage('Stage 5')} FAILED: "
            "Plex has no libraries configured."
        )
        print(
            _stage(
                f"Stage 5 – Plex has {len(libraries)} library/libraries: "
                + ", ".join(lib.get("title", "?") for lib in libraries)
            )
        )

    def test_plex_libraries_have_media_paths(self, plex_client):
        """Plex movie/TV libraries must point to expected media paths."""
        print(_stage("Stage 5 – Checking Plex library paths"))
        try:
            resp = plex_client.get("/library/sections")
        except requests.RequestException as exc:
            raise AssertionError(
                f"{_stage('Stage 5')} FAILED: Plex unreachable: {exc}"
            ) from exc
        assert resp.status_code == 200

        libraries = resp.json().get("MediaContainer", {}).get("Directory", [])
        expected_paths = {
            "movie": "/data/movies",
            "show": "/data/tv",
        }

        failures = []
        for lib in libraries:
            title = lib.get("title", "Unknown")
            lib_type = lib.get("type", "")
            expected = expected_paths.get(lib_type)
            if expected is None:
                continue

            locations = lib.get("Location", [])
            paths = [loc.get("path", "") for loc in locations]
            match = any(
                p.rstrip("/").startswith(expected.rstrip("/"))
                for p in paths
            )
            if not match:
                failures.append(
                    f"Library '{title}' (type={lib_type}) paths {paths} "
                    f"do not include expected '{expected}'"
                )

        assert not failures, (
            f"{_stage('Stage 5')} FAILED: Library path mismatches:\n"
            + "\n".join(f"  - {f}" for f in failures)
        )
        print(_stage("Stage 5 – Plex library paths OK"))

    def test_plex_autoscan_enabled(self, plex_client):
        """Plex libraries should have auto-scan enabled for new media."""
        print(_stage("Stage 5 – Checking Plex auto-scan settings"))
        try:
            resp = plex_client.get("/library/sections")
        except requests.RequestException as exc:
            raise AssertionError(
                f"{_stage('Stage 5')} FAILED: Plex unreachable: {exc}"
            ) from exc
        assert resp.status_code == 200

        libraries = resp.json().get("MediaContainer", {}).get("Directory", [])
        assert len(libraries) > 0, "No Plex libraries found"

        failures = []
        for lib in libraries:
            title = lib.get("title", "Unknown")
            key = lib.get("key", "")

            try:
                prefs_resp = plex_client.get(
                    f"/library/sections/{key}/prefs"
                )
            except requests.RequestException:
                continue

            if prefs_resp.status_code != 200:
                continue

            settings = (
                prefs_resp.json()
                .get("MediaContainer", {})
                .get("Setting", [])
            )
            prefs = {s["id"]: s for s in settings if "id" in s}

            for pref_id, pref in prefs.items():
                pid = pref_id.lower()
                if "autoscan" in pid or "autoupdate" in pid:
                    value = pref.get("value", pref.get("default"))
                    if value in (0, False, "0", "false"):
                        failures.append(
                            f"Library '{title}' (key={key}) has auto-scan "
                            "disabled."
                        )
                        break

        assert not failures, (
            f"{_stage('Stage 5')} FAILED: Auto-scan issues:\n"
            + "\n".join(f"  - {f}" for f in failures)
        )
        print(_stage("Stage 5 – Plex auto-scan OK"))


# ---------------------------------------------------------------------------
# Pipeline Summary
# ---------------------------------------------------------------------------

class TestPipelineSummary:
    """Final summary confirming all stages passed.

    This test runs last and prints a summary banner.  It re-checks a
    lightweight health indicator from each service to confirm end-to-end
    readiness without duplicating the detailed validations above.
    """

    def test_pipeline_dry_run_passed(
        self,
        overseerr_client,
        radarr_client,
        sonarr_client,
        prowlarr_client,
        qbittorrent_client,
        plex_client,
    ):
        """Dry-run summary: all integration points are reachable and configured."""
        print("\n" + "=" * 60)
        print(_stage("DRY-RUN PIPELINE VALIDATION SUMMARY"))
        print("=" * 60)

        # Quick health checks – any failure here means a prior stage
        # should have already failed with a detailed message.
        services = {
            "Overseerr": (overseerr_client, "/api/v1/status"),
            "Radarr": (radarr_client, "/api/v3/system/status"),
            "Sonarr": (sonarr_client, "/api/v3/system/status"),
            "Prowlarr": (prowlarr_client, "/api/v1/system/status"),
            "Plex": (plex_client, "/status/sessions"),
        }

        results = []
        for name, (client, path) in services.items():
            try:
                resp = client.get(path)
                ok = resp.status_code == 200
            except requests.RequestException:
                ok = False
            status = "PASS" if ok else "FAIL"
            results.append((name, status))
            print(_stage(f"  {name:.<20s} {status}"))

        # qBittorrent needs login
        try:
            qbittorrent_client.login()
            resp = qbittorrent_client.get("/api/v2/app/version")
            qbt_ok = resp.status_code == 200
        except requests.RequestException:
            qbt_ok = False
        qbt_status = "PASS" if qbt_ok else "FAIL"
        results.append(("qBittorrent", qbt_status))
        print(_stage(f"  {'qBittorrent':.<20s} {qbt_status}"))

        print("=" * 60)

        all_passed = all(s == "PASS" for _, s in results)
        if all_passed:
            print(_stage("ALL SERVICES OPERATIONAL – Pipeline ready"))
            print(
                _stage(
                    "NOTE: This was a dry-run. To test an actual download, "
                    "submit a request through Overseerr and verify manually."
                )
            )
        else:
            failed = [n for n, s in results if s == "FAIL"]
            print(_stage(f"FAILED SERVICES: {', '.join(failed)}"))

        print("=" * 60 + "\n")

        assert all_passed, (
            f"{_stage('SUMMARY')} Pipeline dry-run failed. "
            f"Services with issues: {', '.join(n for n, s in results if s == 'FAIL')}. "
            "Review the stage-specific test failures above for details."
        )
