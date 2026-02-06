"""Configuration drift comparison engine.

This module compares running Docker container configurations against git baseline
configurations to identify drift and classify severity.
"""

import logging
from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime


# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


class DriftSeverity(Enum):
    """Classification of drift severity."""
    BREAKING = "breaking"      # Changes that break functionality (image tag, critical env vars)
    FUNCTIONAL = "functional"  # Changes that affect behavior (ports, non-critical env vars)
    COSMETIC = "cosmetic"      # Changes with no functional impact (labels, ordering)
    INFORMATIONAL = "informational"  # Differences that are expected/acceptable


@dataclass
class DriftItem:
    """Individual configuration drift item.
    
    Attributes:
        field_path: Dot-notation path to the drifted field (e.g., 'labels.app.version')
        baseline_value: Value from git repository
        running_value: Value from running container
        severity: Classification of drift impact
        description: Human-readable description of the drift
    """
    field_path: str
    baseline_value: Any
    running_value: Any
    severity: DriftSeverity
    description: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'field_path': self.field_path,
            'baseline_value': self.baseline_value,
            'running_value': self.running_value,
            'severity': self.severity.value,
            'description': self.description
        }


@dataclass
class ServiceDrift:
    """Drift analysis for a single service/container.
    
    Attributes:
        service_name: Name of the service
        stack_name: Stack the service belongs to
        container_id: Running container ID (short)
        has_drift: Whether any drift was detected
        drift_items: List of specific drift items found
        matched: Whether running container matched a git baseline
        baseline_missing: True if running but not in git
        container_missing: True if in git but not running
    """
    service_name: str
    stack_name: Optional[str]
    container_id: Optional[str]
    has_drift: bool
    drift_items: List[DriftItem]
    matched: bool
    baseline_missing: bool = False
    container_missing: bool = False
    
    def get_severity_counts(self) -> Dict[str, int]:
        """Get count of drift items by severity."""
        counts = {
            'breaking': 0,
            'functional': 0,
            'cosmetic': 0,
            'informational': 0
        }
        for item in self.drift_items:
            counts[item.severity.value] += 1
        return counts
    
    def has_breaking_drift(self) -> bool:
        """Check if service has any breaking drift."""
        return any(item.severity == DriftSeverity.BREAKING for item in self.drift_items)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'service_name': self.service_name,
            'stack_name': self.stack_name,
            'container_id': self.container_id,
            'has_drift': self.has_drift,
            'matched': self.matched,
            'baseline_missing': self.baseline_missing,
            'container_missing': self.container_missing,
            'drift_items': [item.to_dict() for item in self.drift_items],
            'severity_counts': self.get_severity_counts()
        }


@dataclass
class DriftReport:
    """Complete drift analysis report.
    
    Attributes:
        timestamp: When the analysis was performed
        services_analyzed: Number of services analyzed
        services_with_drift: Number of services with drift detected
        total_drift_items: Total number of drift items across all services
        service_drifts: List of ServiceDrift objects
        baseline_host: Host where running configs were inspected
        baseline_repo: Git repository used for baselines
    """
    timestamp: str
    services_analyzed: int
    services_with_drift: int
    total_drift_items: int
    service_drifts: List[ServiceDrift]
    baseline_host: Optional[str] = None
    baseline_repo: Optional[str] = None
    
    def get_severity_summary(self) -> Dict[str, int]:
        """Get total count of drift items by severity across all services."""
        summary = {
            'breaking': 0,
            'functional': 0,
            'cosmetic': 0,
            'informational': 0
        }
        for service_drift in self.service_drifts:
            counts = service_drift.get_severity_counts()
            for severity, count in counts.items():
                summary[severity] += count
        return summary
    
    def get_breaking_services(self) -> List[ServiceDrift]:
        """Get list of services with breaking drift."""
        return [sd for sd in self.service_drifts if sd.has_breaking_drift()]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'timestamp': self.timestamp,
            'services_analyzed': self.services_analyzed,
            'services_with_drift': self.services_with_drift,
            'total_drift_items': self.total_drift_items,
            'baseline_host': self.baseline_host,
            'baseline_repo': self.baseline_repo,
            'severity_summary': self.get_severity_summary(),
            'breaking_services': len(self.get_breaking_services()),
            'service_drifts': [sd.to_dict() for sd in self.service_drifts]
        }


class DriftComparator:
    """Compare running configurations against git baselines to detect drift.
    
    This class implements deep comparison logic with severity classification
    and structured diff output.
    """
    
    # Fields to ignore during comparison (ephemeral/runtime-only)
    EPHEMERAL_FIELDS = {
        'container_id',
        'created',
        'started',
        'compose_file'  # Path to compose file, not part of config
    }
    
    # Image tag patterns that indicate breaking changes
    BREAKING_TAG_PATTERNS = {
        'major_version',  # nginx:1.x vs nginx:2.x
        'specific_to_latest'  # nginx:1.20 vs nginx:latest
    }
    
    def __init__(self):
        """Initialize drift comparator."""
        logger.info("Initialized DriftComparator")
    
    def normalize_value(self, value: Any) -> Any:
        """Normalize values for comparison.
        
        Handles:
        - Empty strings vs None
        - List ordering (for certain fields)
        - String representations of numbers
        
        Args:
            value: Value to normalize
        
        Returns:
            Normalized value
        """
        if value == "" or value is None:
            return None
        
        # Normalize boolean strings
        if isinstance(value, str):
            if value.lower() in ('true', 'false'):
                return value.lower() == 'true'
        
        return value
    
    def compare_images(self, baseline_image: str, running_image: str) -> Tuple[bool, DriftSeverity]:
        """Compare image specifications and determine severity.
        
        Args:
            baseline_image: Image from git baseline
            running_image: Image from running container
        
        Returns:
            Tuple of (has_drift, severity)
        """
        if baseline_image == running_image:
            return (False, DriftSeverity.INFORMATIONAL)
        
        # Parse image name and tag
        def parse_image(image: str) -> Tuple[str, str]:
            if ':' in image:
                name, tag = image.rsplit(':', 1)
            else:
                name, tag = image, 'latest'
            return (name, tag)
        
        baseline_name, baseline_tag = parse_image(baseline_image)
        running_name, running_tag = parse_image(running_image)
        
        # Different image names = breaking
        if baseline_name != running_name:
            return (True, DriftSeverity.BREAKING)
        
        # Check if tags differ
        if baseline_tag != running_tag:
            # Using 'latest' when baseline specifies version = breaking
            if baseline_tag != 'latest' and running_tag == 'latest':
                return (True, DriftSeverity.BREAKING)
            
            # Major version change = breaking
            baseline_major = baseline_tag.split('.')[0] if '.' in baseline_tag else baseline_tag
            running_major = running_tag.split('.')[0] if '.' in running_tag else running_tag
            
            if baseline_major != running_major and baseline_major.isdigit() and running_major.isdigit():
                return (True, DriftSeverity.BREAKING)
            
            # Minor version drift = functional
            return (True, DriftSeverity.FUNCTIONAL)
        
        return (False, DriftSeverity.INFORMATIONAL)
    
    def classify_field_severity(self, field_path: str, baseline_value: Any, running_value: Any) -> DriftSeverity:
        """Classify severity of a field-level drift.
        
        Args:
            field_path: Dot-notation path to field
            baseline_value: Value from git baseline
            running_value: Value from running container
        
        Returns:
            Drift severity classification
        """
        # Image drift handled separately
        if field_path == 'image':
            _, severity = self.compare_images(str(baseline_value), str(running_value))
            return severity
        
        # Critical environment variables = breaking
        critical_env_vars = {
            'DATABASE_URL', 'DB_HOST', 'DB_PORT',
            'REDIS_URL', 'REDIS_HOST',
            'API_KEY', 'API_URL',
            'VPN_', 'TUNNEL_'
        }
        
        if field_path.startswith('environment.'):
            env_var = field_path.split('.', 1)[1]
            if any(env_var.startswith(critical) for critical in critical_env_vars):
                return DriftSeverity.BREAKING
            # Other environment variables = functional
            return DriftSeverity.FUNCTIONAL
        
        # Ports = functional
        if 'ports' in field_path:
            return DriftSeverity.FUNCTIONAL
        
        # Volumes/mounts = functional (could break data access)
        if 'volumes' in field_path or 'mounts' in field_path:
            return DriftSeverity.FUNCTIONAL
        
        # Networks = functional
        if 'networks' in field_path:
            return DriftSeverity.FUNCTIONAL
        
        # Labels = cosmetic (unless Traefik routing labels)
        if field_path.startswith('labels.'):
            label_key = field_path.split('.', 1)[1]
            if label_key.startswith('traefik.http.routers') or label_key.startswith('traefik.http.services'):
                return DriftSeverity.FUNCTIONAL
            return DriftSeverity.COSMETIC
        
        # Default = functional (conservative approach)
        return DriftSeverity.FUNCTIONAL
    
    def deep_compare(
        self,
        baseline: Dict[str, Any],
        running: Dict[str, Any],
        path: str = ""
    ) -> List[DriftItem]:
        """Recursively compare two configuration dictionaries.
        
        Args:
            baseline: Configuration from git baseline
            running: Configuration from running container
            path: Current path in dot notation (for nested dicts)
        
        Returns:
            List of DriftItem objects for all detected differences
        """
        drift_items = []
        
        # Get all keys from both dicts
        all_keys = set(baseline.keys()) | set(running.keys())
        
        for key in all_keys:
            # Skip ephemeral fields
            if key in self.EPHEMERAL_FIELDS:
                continue
            
            current_path = f"{path}.{key}" if path else key
            
            baseline_val = baseline.get(key)
            running_val = running.get(key)
            
            # Normalize values
            baseline_val = self.normalize_value(baseline_val)
            running_val = self.normalize_value(running_val)
            
            # Both None = no drift
            if baseline_val is None and running_val is None:
                continue
            
            # One is None = drift
            if baseline_val is None or running_val is None:
                severity = self.classify_field_severity(current_path, baseline_val, running_val)
                description = f"Field '{current_path}': "
                if baseline_val is None:
                    description += f"present in running ({running_val}) but missing in baseline"
                else:
                    description += f"present in baseline ({baseline_val}) but missing in running"
                
                drift_items.append(DriftItem(
                    field_path=current_path,
                    baseline_value=baseline_val,
                    running_value=running_val,
                    severity=severity,
                    description=description
                ))
                continue
            
            # Recursive comparison for nested dicts
            if isinstance(baseline_val, dict) and isinstance(running_val, dict):
                nested_drifts = self.deep_compare(baseline_val, running_val, current_path)
                drift_items.extend(nested_drifts)
                continue
            
            # List comparison (order-insensitive for certain fields)
            if isinstance(baseline_val, list) and isinstance(running_val, list):
                # For now, treat lists as ordered (simple comparison)
                # TODO: Make order-insensitive for certain fields (networks, volumes)
                if baseline_val != running_val:
                    severity = self.classify_field_severity(current_path, baseline_val, running_val)
                    drift_items.append(DriftItem(
                        field_path=current_path,
                        baseline_value=baseline_val,
                        running_value=running_val,
                        severity=severity,
                        description=f"List '{current_path}' differs between baseline and running"
                    ))
                continue
            
            # Direct value comparison
            if baseline_val != running_val:
                severity = self.classify_field_severity(current_path, baseline_val, running_val)
                drift_items.append(DriftItem(
                    field_path=current_path,
                    baseline_value=baseline_val,
                    running_value=running_val,
                    severity=severity,
                    description=f"Field '{current_path}' changed from '{baseline_val}' to '{running_val}'"
                ))
        
        return drift_items
    
    def match_container_to_baseline(
        self,
        container_name: str,
        baselines: List[Any]
    ) -> Optional[Any]:
        """Match a running container to its git baseline by name.
        
        Args:
            container_name: Name of the running container
            baselines: List of GitBaselineConfig objects
        
        Returns:
            Matching baseline config or None if not found
        """
        # Direct name match
        for baseline in baselines:
            if baseline.name == container_name:
                return baseline
        
        # Try matching with stack prefix removed (e.g., 'pihole_pihole' -> 'pihole')
        for baseline in baselines:
            if container_name.startswith(f"{baseline.stack_name}_"):
                suffix = container_name[len(baseline.stack_name) + 1:]
                if suffix == baseline.name:
                    return baseline
        
        return None
    
    def compare_configurations(
        self,
        running_containers: List[Any],
        git_baselines: List[Any]
    ) -> DriftReport:
        """Compare running container configurations against git baselines.
        
        Args:
            running_containers: List of ContainerInfo objects from docker_inspector
            git_baselines: List of GitBaselineConfig objects from git_config_loader
        
        Returns:
            DriftReport with complete analysis
        """
        logger.info(
            f"Comparing {len(running_containers)} running container(s) "
            f"against {len(git_baselines)} git baseline(s)"
        )
        
        service_drifts = []
        services_with_drift = 0
        total_drift_items = 0
        
        # Track which baselines were matched
        matched_baselines = set()
        
        # Compare each running container
        for container in running_containers:
            baseline = self.match_container_to_baseline(container.name, git_baselines)
            
            if baseline is None:
                # Running but not in git = baseline missing
                service_drifts.append(ServiceDrift(
                    service_name=container.name,
                    stack_name=None,
                    container_id=container.container_id[:12],
                    has_drift=True,
                    drift_items=[],
                    matched=False,
                    baseline_missing=True
                ))
                services_with_drift += 1
                logger.warning(f"Container '{container.name}' running but not found in git baselines")
                continue
            
            # Mark baseline as matched
            matched_baselines.add(baseline.name)
            
            # Convert to dicts for comparison
            container_dict = container.to_dict()
            baseline_dict = baseline.to_dict()
            
            # Perform deep comparison
            drift_items = self.deep_compare(baseline_dict, container_dict)
            
            has_drift = len(drift_items) > 0
            if has_drift:
                services_with_drift += 1
                total_drift_items += len(drift_items)
                logger.info(f"Service '{container.name}' has {len(drift_items)} drift item(s)")
            
            service_drifts.append(ServiceDrift(
                service_name=container.name,
                stack_name=baseline.stack_name,
                container_id=container.container_id[:12],
                has_drift=has_drift,
                drift_items=drift_items,
                matched=True
            ))
        
        # Check for baselines without running containers
        for baseline in git_baselines:
            if baseline.name not in matched_baselines:
                # In git but not running = container missing
                service_drifts.append(ServiceDrift(
                    service_name=baseline.name,
                    stack_name=baseline.stack_name,
                    container_id=None,
                    has_drift=True,
                    drift_items=[],
                    matched=False,
                    container_missing=True
                ))
                services_with_drift += 1
                logger.warning(f"Baseline '{baseline.name}' in git but container not running")
        
        report = DriftReport(
            timestamp=datetime.utcnow().isoformat(),
            services_analyzed=len(running_containers) + len(git_baselines) - len(matched_baselines),
            services_with_drift=services_with_drift,
            total_drift_items=total_drift_items,
            service_drifts=service_drifts
        )
        
        logger.info(
            f"Drift analysis complete: {services_with_drift}/{report.services_analyzed} "
            f"service(s) with drift, {total_drift_items} total drift item(s)"
        )
        
        return report


def compare_drift(running_containers: List[Any], git_baselines: List[Any]) -> Dict[str, Any]:
    """Convenience function to perform drift comparison.
    
    Args:
        running_containers: List of ContainerInfo objects
        git_baselines: List of GitBaselineConfig objects
    
    Returns:
        Dictionary representation of DriftReport
    """
    comparator = DriftComparator()
    report = comparator.compare_configurations(running_containers, git_baselines)
    return report.to_dict()
