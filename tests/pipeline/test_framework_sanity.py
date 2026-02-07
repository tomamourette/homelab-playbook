"""Sanity tests to verify the pytest framework and fixtures load correctly.

These tests do NOT make actual API calls. They validate that the test
harness is properly configured: config loads, fixtures instantiate,
and client objects have the expected attributes.
"""

from tests.pipeline.utils.api_client import MediaClient, PlexClient, QBittorrentClient


class TestConfigLoading:
    """Verify that configuration loads from environment."""

    def test_config_fixture_returns_dict(self, config):
        assert isinstance(config, dict), "config fixture should return a dict"

    def test_config_has_all_required_keys(self, config):
        required_keys = [
            "OVERSEERR_URL",
            "OVERSEERR_API_KEY",
            "RADARR_URL",
            "RADARR_API_KEY",
            "SONARR_URL",
            "SONARR_API_KEY",
            "PROWLARR_URL",
            "PROWLARR_API_KEY",
            "QBITTORRENT_URL",
            "QBITTORRENT_USERNAME",
            "QBITTORRENT_PASSWORD",
            "PLEX_URL",
            "PLEX_TOKEN",
        ]
        for key in required_keys:
            assert key in config, f"Missing config key: {key}"


class TestFixtureInstantiation:
    """Verify that all service fixtures instantiate correctly."""

    def test_overseerr_client_is_media_client(self, overseerr_client):
        assert isinstance(overseerr_client, MediaClient)

    def test_radarr_client_is_media_client(self, radarr_client):
        assert isinstance(radarr_client, MediaClient)

    def test_sonarr_client_is_media_client(self, sonarr_client):
        assert isinstance(sonarr_client, MediaClient)

    def test_prowlarr_client_is_media_client(self, prowlarr_client):
        assert isinstance(prowlarr_client, MediaClient)

    def test_qbittorrent_client_is_correct_type(self, qbittorrent_client):
        assert isinstance(qbittorrent_client, QBittorrentClient)

    def test_plex_client_is_correct_type(self, plex_client):
        assert isinstance(plex_client, PlexClient)


class TestClientAttributes:
    """Verify that client objects have expected attributes."""

    def test_media_client_has_session(self, radarr_client):
        assert hasattr(radarr_client, "session")
        assert hasattr(radarr_client, "base_url")
        assert hasattr(radarr_client, "api_key")

    def test_media_client_has_http_methods(self, radarr_client):
        assert callable(getattr(radarr_client, "get", None))
        assert callable(getattr(radarr_client, "post", None))
        assert callable(getattr(radarr_client, "put", None))
        assert callable(getattr(radarr_client, "delete", None))

    def test_qbittorrent_client_has_login(self, qbittorrent_client):
        assert callable(getattr(qbittorrent_client, "login", None))
        assert hasattr(qbittorrent_client, "session")

    def test_plex_client_has_session(self, plex_client):
        assert hasattr(plex_client, "session")
        assert hasattr(plex_client, "token")

    def test_media_client_sets_api_key_header(self, radarr_client):
        assert radarr_client.session.headers.get("X-Api-Key") == radarr_client.api_key

    def test_plex_client_sets_token_header(self, plex_client):
        assert plex_client.session.headers.get("X-Plex-Token") == plex_client.token
