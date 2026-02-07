"""Reusable API client for homelab media services."""

import requests


class BaseClient:
    """Base HTTP client with shared request methods.

    Subclasses must set ``base_url``, ``timeout``, and ``session``
    before calling the HTTP helpers.
    """

    base_url: str
    timeout: int
    session: requests.Session

    def _build_url(self, path: str) -> str:
        return f"{self.base_url}/{path.lstrip('/')}"

    def get(self, path: str, **kwargs) -> requests.Response:
        """Send a GET request."""
        kwargs.setdefault("timeout", self.timeout)
        return self.session.get(self._build_url(path), **kwargs)

    def post(self, path: str, **kwargs) -> requests.Response:
        """Send a POST request."""
        kwargs.setdefault("timeout", self.timeout)
        return self.session.post(self._build_url(path), **kwargs)


class MediaClient(BaseClient):
    """HTTP client pre-configured with base URL and API key header.

    Args:
        base_url: Service base URL (e.g. http://192.168.x.x:7878).
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

    def put(self, path: str, **kwargs) -> requests.Response:
        """Send a PUT request to the service API."""
        kwargs.setdefault("timeout", self.timeout)
        return self.session.put(self._build_url(path), **kwargs)

    def delete(self, path: str, **kwargs) -> requests.Response:
        """Send a DELETE request to the service API."""
        kwargs.setdefault("timeout", self.timeout)
        return self.session.delete(self._build_url(path), **kwargs)


class QBittorrentClient(BaseClient):
    """HTTP client for qBittorrent Web API (cookie-based auth).

    Args:
        base_url: qBittorrent Web UI URL (e.g. http://192.168.x.x:8080).
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


class PlexClient(BaseClient):
    """HTTP client for Plex Media Server API (token-based auth).

    Args:
        base_url: Plex server URL (e.g. http://192.168.x.x:32400).
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
