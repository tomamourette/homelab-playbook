"""Drift Detection Tool for Docker Containers.

This package provides tools to inspect Docker containers on remote hosts
via SSH and extract their runtime configurations for drift analysis.
"""

from docker_inspector import (
    DockerInspector,
    ContainerInfo,
    SSHConnectionError,
    DockerConnectionError,
    ContainerInspectionError,
    inspect_host,
    inspect_multiple_hosts,
)

from config import Config, load_config

from git_config_loader import (
    GitConfigLoader,
    GitBaselineConfig,
    GitConfigError,
    ComposeFileNotFoundError,
    ComposeParseError,
    load_git_baselines,
)

from drift_comparator import (
    DriftComparator,
    DriftReport,
    ServiceDrift,
    DriftItem,
    DriftSeverity,
    compare_drift,
)

from drift_report_generator import (
    DriftReportGenerator,
    generate_markdown_report,
    save_markdown_report,
)

from pr_generator import (
    PRGenerator,
    PRGenerationError,
    GitOperationError,
    generate_prs_from_drift_report,
)

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
    "GitConfigLoader",
    "GitBaselineConfig",
    "GitConfigError",
    "ComposeFileNotFoundError",
    "ComposeParseError",
    "load_git_baselines",
    "DriftComparator",
    "DriftReport",
    "ServiceDrift",
    "DriftItem",
    "DriftSeverity",
    "compare_drift",
    "DriftReportGenerator",
    "generate_markdown_report",
    "save_markdown_report",
    "PRGenerator",
    "PRGenerationError",
    "GitOperationError",
    "generate_prs_from_drift_report",
]
