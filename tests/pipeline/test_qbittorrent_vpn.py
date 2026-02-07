"""qBittorrent VPN routing validation tests.

Verifies qBittorrent traffic is routed through the Gluetun VPN container,
ensuring download traffic is secure and IP-masked.

Acceptance criteria:
  - qBittorrent container uses Gluetun's network (network_mode: service:gluetun).
  - External IP visible to qBittorrent is NOT in the home network range (192.168.x.x).
  - Gluetun container is running and healthy.
"""

import ipaddress
import re
from collections.abc import Generator

import docker
import pytest


@pytest.fixture(scope="module")
def docker_client(config) -> Generator[docker.DockerClient]:
    """Docker client connected to the media host (ct-media-01)."""
    host = config["DOCKER_HOST_MEDIA"]
    if not host:
        pytest.skip("DOCKER_HOST_MEDIA not configured")
    client = docker.DockerClient(base_url=host, timeout=30)
    yield client
    client.close()


@pytest.fixture(scope="module")
def gluetun_container(docker_client, config):
    """Return the Gluetun container object."""
    name = config["GLUETUN_CONTAINER_NAME"]
    try:
        return docker_client.containers.get(name)
    except docker.errors.NotFound:
        pytest.fail(f"Gluetun unhealthy – container '{name}' not found")
    except docker.errors.APIError as exc:
        pytest.fail(f"Gluetun unhealthy – Docker API error: {exc}")


@pytest.fixture(scope="module")
def qbittorrent_container(docker_client, config):
    """Return the qBittorrent container object."""
    name = config["QBITTORRENT_CONTAINER_NAME"]
    try:
        return docker_client.containers.get(name)
    except docker.errors.NotFound:
        pytest.fail(f"qBittorrent container '{name}' not found")
    except docker.errors.APIError as exc:
        pytest.fail(f"Docker API error: {exc}")


def _is_private_ip(ip_str: str) -> bool:
    """Return True if the IP address is in a private/reserved range."""
    try:
        addr = ipaddress.ip_address(ip_str.strip())
    except ValueError:
        return False
    return addr.is_private


class TestGluetunHealth:
    """Verify the Gluetun VPN container is running and healthy."""

    def test_gluetun_running(self, gluetun_container):
        """Gluetun container must be in 'running' state."""
        status = gluetun_container.status
        assert status == "running", (
            f"Gluetun unhealthy – container status is '{status}', expected 'running'"
        )

    def test_gluetun_health_check(self, gluetun_container):
        """Gluetun health check should report healthy (if configured)."""
        gluetun_container.reload()
        health = gluetun_container.attrs.get("State", {}).get("Health")
        if health is None:
            pytest.skip("Gluetun has no healthcheck configured")

        health_status = health.get("Status", "unknown")
        assert health_status == "healthy", (
            f"Gluetun unhealthy – healthcheck status is '{health_status}'"
        )


class TestQBittorrentNetworkMode:
    """Verify qBittorrent routes through Gluetun's network namespace."""

    def test_network_mode_uses_gluetun(
        self, qbittorrent_container, gluetun_container
    ):
        """qBittorrent must use container:<gluetun-id> network mode."""
        qbt_attrs = qbittorrent_container.attrs
        network_mode = (
            qbt_attrs.get("HostConfig", {}).get("NetworkMode", "")
        )

        gluetun_id = gluetun_container.id
        gluetun_name = gluetun_container.name

        # Docker expresses "service:gluetun" as "container:<id>" or
        # "container:<name>" at runtime.
        valid_modes = {
            f"container:{gluetun_id}",
            f"container:{gluetun_name}",
        }

        assert network_mode in valid_modes, (
            f"VPN not configured – qBittorrent NetworkMode is '{network_mode}', "
            f"expected one of {valid_modes}. "
            "qBittorrent is NOT routing through the Gluetun VPN container."
        )


class TestVPNIPLeak:
    """Verify the external IP seen by qBittorrent is NOT the home network IP."""

    def test_external_ip_not_home_network(self, qbittorrent_container):
        """External IP from inside the qBittorrent container must not be private."""
        result = qbittorrent_container.exec_run(
            ["wget", "-qO-", "https://ifconfig.me"],
            demux=True,
        )
        stdout = result.output[0] if result.output[0] else b""
        stderr = result.output[1] if result.output[1] else b""

        if result.exit_code != 0:
            # wget may not be available; try curl as fallback
            result = qbittorrent_container.exec_run(
                ["curl", "-s", "https://ifconfig.me"],
                demux=True,
            )
            stdout = result.output[0] if result.output[0] else b""
            stderr = result.output[1] if result.output[1] else b""

        assert result.exit_code == 0, (
            f"VPN leak detected – could not determine external IP. "
            f"Exit code: {result.exit_code}, stderr: {stderr.decode(errors='replace')}"
        )

        external_ip = stdout.decode().strip()
        assert external_ip, (
            "VPN leak detected – external IP query returned empty response"
        )

        # Validate it looks like an IP address
        assert re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", external_ip), (
            f"VPN leak detected – unexpected response from IP check: "
            f"'{external_ip[:100]}'"
        )

        assert not _is_private_ip(external_ip), (
            f"VPN leak detected – qBittorrent external IP is {external_ip}, "
            "which is a private/home network address. "
            "Traffic is NOT routing through the VPN."
        )
