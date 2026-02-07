"""Reusable API client for homelab media services."""

from urllib.parse import urljoin

import requests


class MediaClient:
    """HTTP client pre-configured with base URL and API key header.

    Args:
        base_url: Service base URL (e.g. http://192.168.50.161:7878).
        api_key: API key sent via X-Api-Key header.
        timeout: Request timeout in seconds.
    """

    def __init__(self, base_url: str, api_key: str, timeout: int = 30) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "X-Api-Key": api_key,
            "Accept": "application/json",
        })

    def get(self, path: str, **kwargs) -> requests.Response:
        """Send a GET request to the service API."""
        url = f"{self.base_url}/{path.lstrip('/')}"
        kwargs.setdefault("timeout", self.timeout)
        return self.session.get(url, **kwargs)

    def post(self, path: str, **kwargs) -> requests.Response:
        """Send a POST request to the service API."""
        url = f"{self.base_url}/{path.lstrip('/')}"
        kwargs.setdefault("timeout", self.timeout)
        return self.session.post(url, **kwargs)

    def put(self, path: str, **kwargs) -> requests.Response:
        """Send a PUT request to the service API."""
        url = f"{self.base_url}/{path.lstrip('/')}"
        kwargs.setdefault("timeout", self.timeout)
        return self.session.put(url, **kwargs)

    def delete(self, path: str, **kwargs) -> requests.Response:
        """Send a DELETE request to the service API."""
        url = f"{self.base_url}/{path.lstrip('/')}"
        kwargs.setdefault("timeout", self.timeout)
        return self.session.delete(url, **kwargs)


class QBittorrentClient:
    """HTTP client for qBittorrent Web API (cookie-based auth).

    Args:
        base_url: qBittorrent Web UI URL (e.g. http://192.168.50.161:8080).
        username: Login username.
        password: Login password.
        timeout: Request timeout in seconds.
    """

    def __init__(
        self, base_url: str, username: str, password: str, timeout: int = 30
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password
        self.timeout = timeout
        self.session = requests.Session()

    def login(self) -> requests.Response:
        """Authenticate and store session cookie."""
        url = f"{self.base_url}/api/v2/auth/login"
        return self.session.post(
            url,
            data={"username": self.username, "password": self.password},
            timeout=self.timeout,
        )

    def get(self, path: str, **kwargs) -> requests.Response:
        """Send a GET request to the qBittorrent API."""
        url = f"{self.base_url}/{path.lstrip('/')}"
        kwargs.setdefault("timeout", self.timeout)
        return self.session.get(url, **kwargs)

    def post(self, path: str, **kwargs) -> requests.Response:
        """Send a POST request to the qBittorrent API."""
        url = f"{self.base_url}/{path.lstrip('/')}"
        kwargs.setdefault("timeout", self.timeout)
        return self.session.post(url, **kwargs)


class PlexClient:
    """HTTP client for Plex Media Server API (token-based auth).

    Args:
        base_url: Plex server URL (e.g. http://192.168.50.161:32400).
        token: Plex authentication token.
        timeout: Request timeout in seconds.
    """

    def __init__(self, base_url: str, token: str, timeout: int = 30) -> None:
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "X-Plex-Token": token,
            "Accept": "application/json",
        })

    def get(self, path: str, **kwargs) -> requests.Response:
        """Send a GET request to the Plex API."""
        url = f"{self.base_url}/{path.lstrip('/')}"
        kwargs.setdefault("timeout", self.timeout)
        return self.session.get(url, **kwargs)

    def post(self, path: str, **kwargs) -> requests.Response:
        """Send a POST request to the Plex API."""
        url = f"{self.base_url}/{path.lstrip('/')}"
        kwargs.setdefault("timeout", self.timeout)
        return self.session.post(url, **kwargs)
