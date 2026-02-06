"""Unit tests for drift_comparator.py module."""

import pytest
from unittest.mock import Mock, MagicMock
from datetime import datetime

from drift_comparator import (
    DriftSeverity,
    DriftItem,
    ServiceDrift,
    DriftReport,
    DriftComparator,
    compare_drift
)


class TestDriftSeverity:
    """Test suite for DriftSeverity enum."""
    
    def test_severity_values(self):
        """Test that all severity levels have correct values."""
        assert DriftSeverity.BREAKING.value == "breaking"
        assert DriftSeverity.FUNCTIONAL.value == "functional"
        assert DriftSeverity.COSMETIC.value == "cosmetic"
        assert DriftSeverity.INFORMATIONAL.value == "informational"


class TestDriftItem:
    """Test suite for DriftItem dataclass."""
    
    def test_drift_item_creation(self):
        """Test DriftItem initialization."""
        item = DriftItem(
            field_path="labels.app",
            baseline_value="web",
            running_value="api",
            severity=DriftSeverity.COSMETIC,
            description="Label changed"
        )
        
        assert item.field_path == "labels.app"
        assert item.baseline_value == "web"
        assert item.running_value == "api"
        assert item.severity == DriftSeverity.COSMETIC
    
    def test_drift_item_to_dict(self):
        """Test DriftItem to_dict conversion."""
        item = DriftItem(
            field_path="image",
            baseline_value="nginx:1.0",
            running_value="nginx:2.0",
            severity=DriftSeverity.BREAKING,
            description="Major version change"
        )
        
        result = item.to_dict()
        
        assert isinstance(result, dict)
        assert result['field_path'] == "image"
        assert result['severity'] == "breaking"


class TestServiceDrift:
    """Test suite for ServiceDrift dataclass."""
    
    def test_service_drift_creation(self):
        """Test ServiceDrift initialization."""
        drift = ServiceDrift(
            service_name="pihole",
            stack_name="dns-pihole",
            container_id="abc123",
            has_drift=True,
            drift_items=[],
            matched=True
        )
        
        assert drift.service_name == "pihole"
        assert drift.has_drift is True
        assert drift.matched is True
    
    def test_get_severity_counts(self):
        """Test severity count aggregation."""
        items = [
            DriftItem("field1", "a", "b", DriftSeverity.BREAKING, ""),
            DriftItem("field2", "c", "d", DriftSeverity.BREAKING, ""),
            DriftItem("field3", "e", "f", DriftSeverity.FUNCTIONAL, ""),
            DriftItem("field4", "g", "h", DriftSeverity.COSMETIC, "")
        ]
        
        drift = ServiceDrift(
            service_name="test",
            stack_name="test-stack",
            container_id="abc",
            has_drift=True,
            drift_items=items,
            matched=True
        )
        
        counts = drift.get_severity_counts()
        
        assert counts['breaking'] == 2
        assert counts['functional'] == 1
        assert counts['cosmetic'] == 1
        assert counts['informational'] == 0
    
    def test_has_breaking_drift_true(self):
        """Test has_breaking_drift when breaking drift exists."""
        items = [
            DriftItem("field1", "a", "b", DriftSeverity.BREAKING, ""),
            DriftItem("field2", "c", "d", DriftSeverity.FUNCTIONAL, "")
        ]
        
        drift = ServiceDrift(
            service_name="test",
            stack_name="test",
            container_id="abc",
            has_drift=True,
            drift_items=items,
            matched=True
        )
        
        assert drift.has_breaking_drift() is True
    
    def test_has_breaking_drift_false(self):
        """Test has_breaking_drift when no breaking drift."""
        items = [
            DriftItem("field1", "a", "b", DriftSeverity.FUNCTIONAL, ""),
            DriftItem("field2", "c", "d", DriftSeverity.COSMETIC, "")
        ]
        
        drift = ServiceDrift(
            service_name="test",
            stack_name="test",
            container_id="abc",
            has_drift=True,
            drift_items=items,
            matched=True
        )
        
        assert drift.has_breaking_drift() is False
    
    def test_to_dict(self):
        """Test ServiceDrift to_dict conversion."""
        drift = ServiceDrift(
            service_name="test",
            stack_name="test-stack",
            container_id="abc123",
            has_drift=False,
            drift_items=[],
            matched=True
        )
        
        result = drift.to_dict()
        
        assert isinstance(result, dict)
        assert result['service_name'] == "test"
        assert result['has_drift'] is False
        assert 'severity_counts' in result


class TestDriftReport:
    """Test suite for DriftReport dataclass."""
    
    def test_drift_report_creation(self):
        """Test DriftReport initialization."""
        report = DriftReport(
            timestamp="2026-02-06T10:00:00",
            services_analyzed=10,
            services_with_drift=3,
            total_drift_items=8,
            service_drifts=[]
        )
        
        assert report.services_analyzed == 10
        assert report.services_with_drift == 3
        assert report.total_drift_items == 8
    
    def test_get_severity_summary(self):
        """Test severity summary aggregation across services."""
        service1_items = [
            DriftItem("f1", "a", "b", DriftSeverity.BREAKING, ""),
            DriftItem("f2", "c", "d", DriftSeverity.FUNCTIONAL, "")
        ]
        
        service2_items = [
            DriftItem("f3", "e", "f", DriftSeverity.BREAKING, ""),
            DriftItem("f4", "g", "h", DriftSeverity.COSMETIC, "")
        ]
        
        service_drifts = [
            ServiceDrift("svc1", "stack1", "abc", True, service1_items, True),
            ServiceDrift("svc2", "stack2", "def", True, service2_items, True)
        ]
        
        report = DriftReport(
            timestamp="2026-02-06T10:00:00",
            services_analyzed=2,
            services_with_drift=2,
            total_drift_items=4,
            service_drifts=service_drifts
        )
        
        summary = report.get_severity_summary()
        
        assert summary['breaking'] == 2
        assert summary['functional'] == 1
        assert summary['cosmetic'] == 1
        assert summary['informational'] == 0
    
    def test_get_breaking_services(self):
        """Test filtering services with breaking drift."""
        breaking_items = [DriftItem("f1", "a", "b", DriftSeverity.BREAKING, "")]
        cosmetic_items = [DriftItem("f2", "c", "d", DriftSeverity.COSMETIC, "")]
        
        service_drifts = [
            ServiceDrift("svc1", "stack1", "abc", True, breaking_items, True),
            ServiceDrift("svc2", "stack2", "def", True, cosmetic_items, True),
            ServiceDrift("svc3", "stack3", "ghi", False, [], True)
        ]
        
        report = DriftReport(
            timestamp="2026-02-06T10:00:00",
            services_analyzed=3,
            services_with_drift=2,
            total_drift_items=2,
            service_drifts=service_drifts
        )
        
        breaking = report.get_breaking_services()
        
        assert len(breaking) == 1
        assert breaking[0].service_name == "svc1"
    
    def test_to_dict(self):
        """Test DriftReport to_dict conversion."""
        report = DriftReport(
            timestamp="2026-02-06T10:00:00",
            services_analyzed=5,
            services_with_drift=2,
            total_drift_items=10,
            service_drifts=[],
            baseline_host="192.168.1.1",
            baseline_repo="/path/to/repo"
        )
        
        result = report.to_dict()
        
        assert isinstance(result, dict)
        assert result['services_analyzed'] == 5
        assert 'severity_summary' in result
        assert 'breaking_services' in result


class TestDriftComparatorNormalize:
    """Test suite for normalize_value method."""
    
    def test_normalize_empty_string_to_none(self):
        """Test that empty strings become None."""
        comparator = DriftComparator()
        
        assert comparator.normalize_value("") is None
    
    def test_normalize_none_stays_none(self):
        """Test that None remains None."""
        comparator = DriftComparator()
        
        assert comparator.normalize_value(None) is None
    
    def test_normalize_boolean_strings(self):
        """Test boolean string normalization."""
        comparator = DriftComparator()
        
        assert comparator.normalize_value("true") is True
        assert comparator.normalize_value("True") is True
        assert comparator.normalize_value("TRUE") is True
        assert comparator.normalize_value("false") is False
        assert comparator.normalize_value("False") is False
    
    def test_normalize_regular_string_unchanged(self):
        """Test that regular strings remain unchanged."""
        comparator = DriftComparator()
        
        assert comparator.normalize_value("hello") == "hello"
        assert comparator.normalize_value("123") == "123"


class TestDriftComparatorCompareImages:
    """Test suite for compare_images method."""
    
    def test_same_image_no_drift(self):
        """Test that identical images show no drift."""
        comparator = DriftComparator()
        
        has_drift, severity = comparator.compare_images("nginx:1.20", "nginx:1.20")
        
        assert has_drift is False
    
    def test_different_image_names_breaking(self):
        """Test that different image names are breaking."""
        comparator = DriftComparator()
        
        has_drift, severity = comparator.compare_images("nginx:1.20", "apache:2.4")
        
        assert has_drift is True
        assert severity == DriftSeverity.BREAKING
    
    def test_version_to_latest_breaking(self):
        """Test that specific version to latest is breaking."""
        comparator = DriftComparator()
        
        has_drift, severity = comparator.compare_images("nginx:1.20", "nginx:latest")
        
        assert has_drift is True
        assert severity == DriftSeverity.BREAKING
    
    def test_major_version_change_breaking(self):
        """Test that major version changes are breaking."""
        comparator = DriftComparator()
        
        has_drift, severity = comparator.compare_images("nginx:1.20", "nginx:2.4")
        
        assert has_drift is True
        assert severity == DriftSeverity.BREAKING
    
    def test_minor_version_change_functional(self):
        """Test that minor version changes are functional."""
        comparator = DriftComparator()
        
        has_drift, severity = comparator.compare_images("nginx:1.20", "nginx:1.21")
        
        assert has_drift is True
        assert severity == DriftSeverity.FUNCTIONAL
    
    def test_image_without_tag(self):
        """Test images without explicit tags (defaults to latest)."""
        comparator = DriftComparator()
        
        has_drift, severity = comparator.compare_images("nginx", "nginx:latest")
        
        assert has_drift is False


class TestDriftComparatorClassifySeverity:
    """Test suite for classify_field_severity method."""
    
    def test_critical_env_var_breaking(self):
        """Test that critical environment variables are breaking."""
        comparator = DriftComparator()
        
        assert comparator.classify_field_severity(
            "environment.DATABASE_URL", "old", "new"
        ) == DriftSeverity.BREAKING
        
        assert comparator.classify_field_severity(
            "environment.API_KEY", "old", "new"
        ) == DriftSeverity.BREAKING
        
        assert comparator.classify_field_severity(
            "environment.VPN_CONFIG", "old", "new"
        ) == DriftSeverity.BREAKING
    
    def test_non_critical_env_var_functional(self):
        """Test that non-critical env vars are functional."""
        comparator = DriftComparator()
        
        assert comparator.classify_field_severity(
            "environment.LOG_LEVEL", "INFO", "DEBUG"
        ) == DriftSeverity.FUNCTIONAL
    
    def test_ports_functional(self):
        """Test that port changes are functional."""
        comparator = DriftComparator()
        
        assert comparator.classify_field_severity(
            "ports.80/tcp", "8080", "8081"
        ) == DriftSeverity.FUNCTIONAL
    
    def test_volumes_functional(self):
        """Test that volume changes are functional."""
        comparator = DriftComparator()
        
        assert comparator.classify_field_severity(
            "volumes.0", "/data1", "/data2"
        ) == DriftSeverity.FUNCTIONAL
    
    def test_networks_functional(self):
        """Test that network changes are functional."""
        comparator = DriftComparator()
        
        assert comparator.classify_field_severity(
            "networks.proxy", {"aliases": []}, {"aliases": ["web"]}
        ) == DriftSeverity.FUNCTIONAL
    
    def test_traefik_routing_labels_functional(self):
        """Test that Traefik routing labels are functional."""
        comparator = DriftComparator()
        
        assert comparator.classify_field_severity(
            "labels.traefik.http.routers.service.rule", "old", "new"
        ) == DriftSeverity.FUNCTIONAL
        
        assert comparator.classify_field_severity(
            "labels.traefik.http.services.service.loadbalancer.server.port", "80", "8080"
        ) == DriftSeverity.FUNCTIONAL
    
    def test_non_traefik_labels_cosmetic(self):
        """Test that non-Traefik labels are cosmetic."""
        comparator = DriftComparator()
        
        assert comparator.classify_field_severity(
            "labels.app.version", "1.0", "1.1"
        ) == DriftSeverity.COSMETIC


class TestDriftComparatorDeepCompare:
    """Test suite for deep_compare method."""
    
    def test_identical_configs_no_drift(self):
        """Test that identical configurations show no drift."""
        comparator = DriftComparator()
        
        baseline = {"image": "nginx:1.20", "labels": {"app": "web"}}
        running = {"image": "nginx:1.20", "labels": {"app": "web"}}
        
        drift_items = comparator.deep_compare(baseline, running)
        
        assert len(drift_items) == 0
    
    def test_simple_value_difference(self):
        """Test detection of simple value differences."""
        comparator = DriftComparator()
        
        baseline = {"image": "nginx:1.20"}
        running = {"image": "nginx:1.21"}
        
        drift_items = comparator.deep_compare(baseline, running)
        
        assert len(drift_items) == 1
        assert drift_items[0].field_path == "image"
        assert drift_items[0].baseline_value == "nginx:1.20"
        assert drift_items[0].running_value == "nginx:1.21"
    
    def test_nested_dict_difference(self):
        """Test detection of differences in nested dictionaries."""
        comparator = DriftComparator()
        
        baseline = {"labels": {"app": "web", "version": "1.0"}}
        running = {"labels": {"app": "web", "version": "2.0"}}
        
        drift_items = comparator.deep_compare(baseline, running)
        
        assert len(drift_items) == 1
        assert drift_items[0].field_path == "labels.version"
    
    def test_field_missing_in_running(self):
        """Test detection when field exists in baseline but not running."""
        comparator = DriftComparator()
        
        baseline = {"image": "nginx:1.20", "ports": ["80:80"]}
        running = {"image": "nginx:1.20"}
        
        drift_items = comparator.deep_compare(baseline, running)
        
        assert len(drift_items) == 1
        assert "missing in running" in drift_items[0].description
    
    def test_field_missing_in_baseline(self):
        """Test detection when field exists in running but not baseline."""
        comparator = DriftComparator()
        
        baseline = {"image": "nginx:1.20"}
        running = {"image": "nginx:1.20", "ports": ["80:80"]}
        
        drift_items = comparator.deep_compare(baseline, running)
        
        assert len(drift_items) == 1
        assert "missing in baseline" in drift_items[0].description
    
    def test_list_difference(self):
        """Test detection of list differences."""
        comparator = DriftComparator()
        
        baseline = {"volumes": ["/data:/app/data"]}
        running = {"volumes": ["/data:/app/data", "/logs:/app/logs"]}
        
        drift_items = comparator.deep_compare(baseline, running)
        
        assert len(drift_items) == 1
        assert "volumes" in drift_items[0].field_path
    
    def test_ephemeral_fields_ignored(self):
        """Test that ephemeral fields are filtered out."""
        comparator = DriftComparator()
        
        baseline = {"image": "nginx:1.20", "created": "2024-01-01"}
        running = {"image": "nginx:1.20", "created": "2024-01-02"}
        
        drift_items = comparator.deep_compare(baseline, running)
        
        # 'created' should be in EPHEMERAL_FIELDS and ignored
        assert len(drift_items) == 0
    
    def test_none_vs_empty_string_normalized(self):
        """Test that None and empty string are treated as equivalent."""
        comparator = DriftComparator()
        
        baseline = {"env_var": None}
        running = {"env_var": ""}
        
        drift_items = comparator.deep_compare(baseline, running)
        
        assert len(drift_items) == 0


class TestDriftComparatorMatchContainer:
    """Test suite for match_container_to_baseline method."""
    
    def test_direct_name_match(self):
        """Test direct container name matching."""
        comparator = DriftComparator()
        
        mock_baseline = Mock()
        mock_baseline.name = "pihole"
        mock_baseline.stack_name = "dns-pihole"
        
        result = comparator.match_container_to_baseline("pihole", [mock_baseline])
        
        assert result == mock_baseline
    
    def test_stack_prefix_match(self):
        """Test matching with stack prefix."""
        comparator = DriftComparator()
        
        mock_baseline = Mock()
        mock_baseline.name = "pihole"
        mock_baseline.stack_name = "dns-pihole"
        
        result = comparator.match_container_to_baseline("dns-pihole_pihole", [mock_baseline])
        
        assert result == mock_baseline
    
    def test_no_match(self):
        """Test when no match is found."""
        comparator = DriftComparator()
        
        mock_baseline = Mock()
        mock_baseline.name = "pihole"
        mock_baseline.stack_name = "dns-pihole"
        
        result = comparator.match_container_to_baseline("nginx", [mock_baseline])
        
        assert result is None


class TestDriftComparatorCompareConfigurations:
    """Test suite for compare_configurations method."""
    
    def test_all_containers_matched_no_drift(self):
        """Test scenario where all containers match and have no drift."""
        comparator = DriftComparator()
        
        # Mock running container
        mock_container = Mock()
        mock_container.name = "pihole"
        mock_container.container_id = "abc123def456"
        mock_container.to_dict.return_value = {
            "name": "pihole",
            "image": "pihole/pihole:2023.05"
        }
        
        # Mock baseline
        mock_baseline = Mock()
        mock_baseline.name = "pihole"
        mock_baseline.stack_name = "dns-pihole"
        mock_baseline.to_dict.return_value = {
            "name": "pihole",
            "image": "pihole/pihole:2023.05"
        }
        
        report = comparator.compare_configurations([mock_container], [mock_baseline])
        
        assert report.services_analyzed == 1
        assert report.services_with_drift == 0
        assert report.total_drift_items == 0
    
    def test_container_running_not_in_git(self):
        """Test when container is running but not found in git."""
        comparator = DriftComparator()
        
        mock_container = Mock()
        mock_container.name = "orphan-service"
        mock_container.container_id = "abc123def456"
        mock_container.to_dict.return_value = {"name": "orphan-service"}
        
        report = comparator.compare_configurations([mock_container], [])
        
        assert report.services_analyzed == 1
        assert report.services_with_drift == 1
        service_drift = report.service_drifts[0]
        assert service_drift.baseline_missing is True
        assert service_drift.matched is False
    
    def test_baseline_in_git_not_running(self):
        """Test when baseline exists in git but container not running."""
        comparator = DriftComparator()
        
        mock_baseline = Mock()
        mock_baseline.name = "stopped-service"
        mock_baseline.stack_name = "test-stack"
        
        report = comparator.compare_configurations([], [mock_baseline])
        
        assert report.services_analyzed == 1
        assert report.services_with_drift == 1
        service_drift = report.service_drifts[0]
        assert service_drift.container_missing is True
        assert service_drift.matched is False
    
    def test_drift_detected_with_severity(self):
        """Test drift detection with proper severity classification."""
        comparator = DriftComparator()
        
        mock_container = Mock()
        mock_container.name = "pihole"
        mock_container.container_id = "abc123def456"
        mock_container.to_dict.return_value = {
            "name": "pihole",
            "image": "pihole/pihole:2024.01",  # Different version
            "labels": {"app": "dns"}
        }
        
        mock_baseline = Mock()
        mock_baseline.name = "pihole"
        mock_baseline.stack_name = "dns-pihole"
        mock_baseline.to_dict.return_value = {
            "name": "pihole",
            "image": "pihole/pihole:2023.05",
            "labels": {"app": "dns"}
        }
        
        report = comparator.compare_configurations([mock_container], [mock_baseline])
        
        assert report.services_analyzed == 1
        assert report.services_with_drift == 1
        assert report.total_drift_items > 0
        
        # Check that image drift was detected
        service_drift = report.service_drifts[0]
        assert service_drift.has_drift is True
        assert any(item.field_path == "image" for item in service_drift.drift_items)


class TestCompareDriftConvenience:
    """Test suite for compare_drift convenience function."""
    
    def test_compare_drift_returns_dict(self):
        """Test that compare_drift returns dictionary representation."""
        mock_container = Mock()
        mock_container.name = "test"
        mock_container.container_id = "abc123"
        mock_container.to_dict.return_value = {"name": "test", "image": "nginx:1.20"}
        
        mock_baseline = Mock()
        mock_baseline.name = "test"
        mock_baseline.stack_name = "test-stack"
        mock_baseline.to_dict.return_value = {"name": "test", "image": "nginx:1.20"}
        
        result = compare_drift([mock_container], [mock_baseline])
        
        assert isinstance(result, dict)
        assert 'timestamp' in result
        assert 'services_analyzed' in result
        assert 'service_drifts' in result
