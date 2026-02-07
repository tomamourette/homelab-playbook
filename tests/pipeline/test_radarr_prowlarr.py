"""Radarr-Prowlarr integration tests.

Verifies Radarr is correctly configured to use Prowlarr as its indexer
source. This validates the "Search" capability of the media pipeline.

Acceptance criteria:
  - Radarr has at least one active indexer (Prowlarr-managed).
  - Each active indexer passes Radarr's built-in connection test.
"""

import requests


class TestRadarrIndexerConfig:
    """Verify Radarr has active Prowlarr-managed indexers."""

    def test_radarr_has_indexers(self, radarr_client):
        """Radarr must have at least one indexer configured."""
        try:
            resp = radarr_client.get("/api/v3/indexer")
        except requests.RequestException as exc:
            raise AssertionError(f"Radarr unreachable: {exc}") from exc

        assert resp.status_code == 200, (
            f"Radarr /api/v3/indexer returned HTTP {resp.status_code}: "
            f"{resp.text[:200]}"
        )

        indexers = resp.json()
        assert isinstance(indexers, list), (
            "Expected a list from /api/v3/indexer"
        )
        assert len(indexers) > 0, (
            "No Indexers Configured – Radarr has zero indexers. "
            "Prowlarr may not have synced its indexers to Radarr."
        )

    def test_radarr_has_prowlarr_indexer(self, radarr_client):
        """At least one indexer should be Prowlarr-managed (Torznab)."""
        resp = radarr_client.get("/api/v3/indexer")
        assert resp.status_code == 200
        indexers = resp.json()

        prowlarr_indexers = [
            idx for idx in indexers
            if idx.get("implementation") == "Torznab"
            or "prowlarr" in idx.get("name", "").lower()
        ]
        assert len(prowlarr_indexers) > 0, (
            "No Prowlarr-managed indexers found. Radarr has "
            f"{len(indexers)} indexer(s) but none use Torznab or "
            "contain 'prowlarr' in their name."
        )

    def test_radarr_indexers_enabled(self, radarr_client):
        """All Prowlarr-managed indexers should be enabled."""
        resp = radarr_client.get("/api/v3/indexer")
        assert resp.status_code == 200
        indexers = resp.json()

        prowlarr_indexers = [
            idx for idx in indexers
            if idx.get("implementation") == "Torznab"
            or "prowlarr" in idx.get("name", "").lower()
        ]
        disabled = [
            idx["name"] for idx in prowlarr_indexers
            if not idx.get("enableRss") and not idx.get("enableAutomaticSearch")
        ]
        assert len(disabled) == 0, (
            f"Disabled Prowlarr indexers: {disabled}. "
            "These indexers exist but have both RSS and automatic search disabled."
        )


class TestRadarrIndexerConnectivity:
    """Verify Radarr can reach its configured indexers."""

    def test_indexer_connection(self, radarr_client):
        """Each active indexer must pass Radarr's built-in connection test."""
        resp = radarr_client.get("/api/v3/indexer")
        assert resp.status_code == 200
        indexers = resp.json()
        assert len(indexers) > 0, (
            "No Indexers Configured – cannot test connectivity."
        )

        failures = []
        for idx in indexers:
            if not idx.get("enableRss") and not idx.get("enableAutomaticSearch"):
                continue

            try:
                test_resp = radarr_client.post(
                    "/api/v3/indexer/test",
                    json=idx,
                )
            except requests.RequestException as exc:
                failures.append(f"{idx['name']}: connection error – {exc}")
                continue

            if test_resp.status_code != 200:
                body = test_resp.text[:300]
                failures.append(
                    f"{idx['name']}: Indexer Connection Failed – "
                    f"HTTP {test_resp.status_code}: {body}"
                )

        assert len(failures) == 0, (
            "Indexer connection test failures:\n"
            + "\n".join(f"  - {f}" for f in failures)
        )
