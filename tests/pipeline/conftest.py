"""Shared pytest fixtures for media pipeline integration tests.

Loads configuration from a .env file and provides pre-configured
API client fixtures for each service in the media stack.
"""

import os
from collections.abc import Generator
from pathlib import Path

import pytest
from dotenv import load_dotenv

from tests.pipeline.utils.api_client import MediaClient, PlexClient, QBittorrentClient

# Load .env from the tests/pipeline directory
_ENV_PATH = Path(__file__).parent / ".env"
load_dotenv(_ENV_PATH)


@pytest.fixture(scope="session")
def config() -> dict[str, str]:
    """Load all pipeline configuration from environment variables."""
    return {
        # Overseerr
        "OVERSEERR_URL": os.environ.get("OVERSEERR_URL", ""),
        "OVERSEERR_API_KEY": os.environ.get("OVERSEERR_API_KEY", ""),
        # Radarr
        "RADARR_URL": os.environ.get("RADARR_URL", ""),
        "RADARR_API_KEY": os.environ.get("RADARR_API_KEY", ""),
        # Sonarr
        "SONARR_URL": os.environ.get("SONARR_URL", ""),
        "SONARR_API_KEY": os.environ.get("SONARR_API_KEY", ""),
        # Prowlarr
        "PROWLARR_URL": os.environ.get("PROWLARR_URL", ""),
        "PROWLARR_API_KEY": os.environ.get("PROWLARR_API_KEY", ""),
        # qBittorrent
        "QBITTORRENT_URL": os.environ.get("QBITTORRENT_URL", ""),
        "QBITTORRENT_USERNAME": os.environ.get("QBITTORRENT_USERNAME", ""),
        "QBITTORRENT_PASSWORD": os.environ.get("QBITTORRENT_PASSWORD", ""),
        # Plex
        "PLEX_URL": os.environ.get("PLEX_URL", ""),
        "PLEX_TOKEN": os.environ.get("PLEX_TOKEN", ""),
        # Docker (ct-media-01)
        "DOCKER_HOST_MEDIA": os.environ.get("DOCKER_HOST_MEDIA", ""),
        "GLUETUN_CONTAINER_NAME": os.environ.get(
            "GLUETUN_CONTAINER_NAME", "gluetun"
        ),
        "QBITTORRENT_CONTAINER_NAME": os.environ.get(
            "QBITTORRENT_CONTAINER_NAME", "qbittorrent"
        ),
    }


@pytest.fixture(scope="session")
def overseerr_client(config) -> Generator[MediaClient]:
    """Configured API client for Overseerr."""
    client = MediaClient(
        base_url=config["OVERSEERR_URL"],
        api_key=config["OVERSEERR_API_KEY"],
    )
    yield client
    client.session.close()


@pytest.fixture(scope="session")
def radarr_client(config) -> Generator[MediaClient]:
    """Configured API client for Radarr."""
    client = MediaClient(
        base_url=config["RADARR_URL"],
        api_key=config["RADARR_API_KEY"],
    )
    yield client
    client.session.close()


@pytest.fixture(scope="session")
def sonarr_client(config) -> Generator[MediaClient]:
    """Configured API client for Sonarr."""
    client = MediaClient(
        base_url=config["SONARR_URL"],
        api_key=config["SONARR_API_KEY"],
    )
    yield client
    client.session.close()


@pytest.fixture(scope="session")
def prowlarr_client(config) -> Generator[MediaClient]:
    """Configured API client for Prowlarr."""
    client = MediaClient(
        base_url=config["PROWLARR_URL"],
        api_key=config["PROWLARR_API_KEY"],
    )
    yield client
    client.session.close()


@pytest.fixture(scope="session")
def qbittorrent_client(config) -> Generator[QBittorrentClient]:
    """Configured API client for qBittorrent."""
    client = QBittorrentClient(
        base_url=config["QBITTORRENT_URL"],
        username=config["QBITTORRENT_USERNAME"],
        password=config["QBITTORRENT_PASSWORD"],
    )
    yield client
    client.session.close()


@pytest.fixture(scope="session")
def plex_client(config) -> Generator[PlexClient]:
    """Configured API client for Plex."""
    client = PlexClient(
        base_url=config["PLEX_URL"],
        token=config["PLEX_TOKEN"],
    )
    yield client
    client.session.close()
