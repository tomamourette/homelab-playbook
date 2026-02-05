"""Drift Detection Tool for Docker Containers.

This package provides tools to inspect Docker containers on remote hosts
via SSH and extract their runtime configurations for drift analysis.
"""

from .docker_inspector import (
    DockerInspector,
    ContainerInfo,
    SSHConnectionError,
    DockerConnectionError,
    ContainerInspectionError,
    inspect_host,
    inspect_multiple_hosts,
)

from .config import Config, load_config

__version__ = "0.1.0"
__all__ = [
    "DockerInspector",
    "ContainerInfo",
    "SSHConnectionError",
    "DockerConnectionError",
    "ContainerInspectionError",
    "inspect_host",
    "inspect_multiple_hosts",
    "Config",
    "load_config",
]
