"""Unit tests for drift_report_generator.py module."""

import pytest
from pathlib import Path
from unittest.mock import Mock, MagicMock, mock_open, patch
import tempfile

from drift_report_generator import (
    DriftReportGenerator,
    generate_markdown_report,
    save_markdown_report
)


class TestDriftReportGenerator:
    """Test suite for DriftReportGenerator class."""
    
    def test_init(self):
        """Test DriftReportGenerator initialization."""
        generator = DriftReportGenerator()
        assert generator is not None
    
    def test_severity_emoji_mapping(self):
        """Test that all severity levels have emoji."""
        generator = DriftReportGenerator()
        assert 'breaking' in generator.SEVERITY_EMOJI
        assert 'functional' in generator.SEVERITY_EMOJI
        assert 'cosmetic' in generator.SEVERITY_EMOJI
        assert 'informational' in generator.SEVERITY_EMOJI
    
    def test_severity_description_mapping(self):
        """Test that all severity levels have descriptions."""
        generator = DriftReportGenerator()
        assert 'breaking' in generator.SEVERITY_DESC
        assert 'functional' in generator.SEVERITY_DESC
        assert 'cosmetic' in generator.SEVERITY_DESC
        assert 'informational' in generator.SEVERITY_DESC


class TestFormatValue:
    """Test suite for format_value method."""
    
    def test_format_none_value(self):
        """Test formatting None values."""
        generator = DriftReportGenerator()
        result = generator.format_value(None)
        assert result == "*[not set]*"
    
    def test_format_short_string(self):
        """Test formatting short strings."""
        generator = DriftReportGenerator()
        result = generator.format_value("short value")
        assert result == "short value"
    
    def test_format_long_string_truncation(self):
        """Test truncation of long strings."""
        generator = DriftReportGenerator()
        long_value = "a" * 100
        result = generator.format_value(long_value, max_length=80)
        assert len(result) <= 80
        assert result.endswith("...")
    
    def test_format_integer(self):
        """Test formatting integers."""
        generator = DriftReportGenerator()
        result = generator.format_value(12345)
        assert result == "12345"
    
    def test_format_list(self):
        """Test formatting lists."""
        generator = DriftReportGenerator()
        result = generator.format_value([1, 2, 3])
        assert result == "[1, 2, 3]"
    
    def test_format_dict(self):
        """Test formatting dictionaries."""
        generator = DriftReportGenerator()
        result = generator.format_value({"key": "value"})
        assert "key" in result
        assert "value" in result


class TestGenerateExecutiveSummary:
    """Test suite for generate_executive_summary method."""
    
    def test_summary_no_drift(self):
        """Test executive summary when no drift detected."""
        generator = DriftReportGenerator()
        
        report_data = {
            'services_analyzed': 5,
            'services_with_drift': 0,
            'total_drift_items': 0,
            'severity_summary': {
                'breaking': 0,
                'functional': 0,
                'cosmetic': 0,
                'informational': 0
            },
            'breaking_services': 0
        }
        
        result = generator.generate_executive_summary(report_data)
        
        assert "## Executive Summary" in result
        assert "No configuration drift detected" in result
        assert "5 service(s)" in result
    
    def test_summary_with_drift(self):
        """Test executive summary when drift detected."""
        generator = DriftReportGenerator()
        
        report_data = {
            'services_analyzed': 5,
            'services_with_drift': 2,
            'total_drift_items': 8,
            'severity_summary': {
                'breaking': 1,
                'functional': 5,
                'cosmetic': 2,
                'informational': 0
            },
            'breaking_services': 1
        }
        
        result = generator.generate_executive_summary(report_data)
        
        assert "## Executive Summary" in result
        assert "Configuration drift detected" in result
        assert "2 of 5 service(s)" in result
        assert "Total drift items: **8**" in result
    
    def test_summary_with_breaking_drift(self):
        """Test executive summary includes critical alert for breaking drift."""
        generator = DriftReportGenerator()
        
        report_data = {
            'services_analyzed': 3,
            'services_with_drift': 1,
            'total_drift_items': 3,
            'severity_summary': {
                'breaking': 3,
                'functional': 0,
                'cosmetic': 0,
                'informational': 0
            },
            'breaking_services': 1
        }
        
        result = generator.generate_executive_summary(report_data)
        
        assert "CRITICAL" in result
        assert "BREAKING drift" in result
    
    def test_summary_includes_severity_table(self):
        """Test that summary includes severity breakdown table."""
        generator = DriftReportGenerator()
        
        report_data = {
            'services_analyzed': 5,
            'services_with_drift': 2,
            'total_drift_items': 10,
            'severity_summary': {
                'breaking': 2,
                'functional': 5,
                'cosmetic': 3,
                'informational': 0
            },
            'breaking_services': 1
        }
        
        result = generator.generate_executive_summary(report_data)
        
        assert "### Drift by Severity" in result
        assert "| Severity | Count | Description |" in result
        assert "**2**" in result  # Breaking count
        assert "**5**" in result  # Functional count


class TestGenerateServiceDetail:
    """Test suite for generate_service_detail method."""
    
    def test_service_no_drift(self):
        """Test service detail for service without drift."""
        generator = DriftReportGenerator()
        
        service_drift = {
            'service_name': 'nginx',
            'stack_name': 'web-stack',
            'container_id': 'abc123',
            'has_drift': False,
            'drift_items': [],
            'matched': True,
            'baseline_missing': False,
            'container_missing': False,
            'severity_counts': {
                'breaking': 0,
                'functional': 0,
                'cosmetic': 0,
                'informational': 0
            }
        }
        
        result = generator.generate_service_detail(service_drift)
        
        assert "### nginx" in result
        assert "**Stack**: web-stack" in result
        assert "No drift detected" in result
    
    def test_service_baseline_missing(self):
        """Test service detail for running container not in git."""
        generator = DriftReportGenerator()
        
        service_drift = {
            'service_name': 'orphan-service',
            'stack_name': None,
            'container_id': 'abc123',
            'has_drift': True,
            'drift_items': [],
            'matched': False,
            'baseline_missing': True,
            'container_missing': False,
            'severity_counts': {}
        }
        
        result = generator.generate_service_detail(service_drift)
        
        assert "### orphan-service" in result
        assert "Running but NOT found in git" in result
        assert "Add this service to git" in result
    
    def test_service_container_missing(self):
        """Test service detail for baseline in git but not running."""
        generator = DriftReportGenerator()
        
        service_drift = {
            'service_name': 'stopped-service',
            'stack_name': 'test-stack',
            'container_id': None,
            'has_drift': True,
            'drift_items': [],
            'matched': False,
            'baseline_missing': False,
            'container_missing': True,
            'severity_counts': {}
        }
        
        result = generator.generate_service_detail(service_drift)
        
        assert "### stopped-service" in result
        assert "Defined in git but NOT running" in result
        assert "Deploy this service" in result
    
    def test_service_with_drift_items(self):
        """Test service detail with actual drift items."""
        generator = DriftReportGenerator()
        
        service_drift = {
            'service_name': 'pihole',
            'stack_name': 'dns-pihole',
            'container_id': 'abc123',
            'has_drift': True,
            'drift_items': [
                {
                    'field_path': 'image',
                    'baseline_value': 'pihole/pihole:2023.05',
                    'running_value': 'pihole/pihole:2024.01',
                    'severity': 'breaking',
                    'description': 'Image changed'
                },
                {
                    'field_path': 'labels.app.version',
                    'baseline_value': '1.0',
                    'running_value': '1.1',
                    'severity': 'cosmetic',
                    'description': 'Label changed'
                }
            ],
            'matched': True,
            'baseline_missing': False,
            'container_missing': False,
            'severity_counts': {
                'breaking': 1,
                'functional': 0,
                'cosmetic': 1,
                'informational': 0
            }
        }
        
        result = generator.generate_service_detail(service_drift)
        
        assert "### pihole" in result
        assert "Drift detected" in result
        assert "#### Configuration Differences" in result
        assert "**image**" in result
        assert "pihole/pihole:2023.05" in result
        assert "pihole/pihole:2024.01" in result
    
    def test_service_breaking_drift_priority(self):
        """Test that breaking drift gets HIGH priority recommendation."""
        generator = DriftReportGenerator()
        
        service_drift = {
            'service_name': 'test',
            'stack_name': 'test-stack',
            'container_id': 'abc123',
            'has_drift': True,
            'drift_items': [{
                'field_path': 'environment.DATABASE_URL',
                'baseline_value': 'old',
                'running_value': 'new',
                'severity': 'breaking',
                'description': 'Critical env var changed'
            }],
            'matched': True,
            'baseline_missing': False,
            'container_missing': False,
            'severity_counts': {
                'breaking': 1,
                'functional': 0,
                'cosmetic': 0,
                'informational': 0
            }
        }
        
        result = generator.generate_service_detail(service_drift)
        
        assert "Priority: HIGH" in result
        assert "Breaking changes detected" in result
    
    def test_service_functional_drift_priority(self):
        """Test that functional drift gets MEDIUM priority recommendation."""
        generator = DriftReportGenerator()
        
        service_drift = {
            'service_name': 'test',
            'stack_name': 'test-stack',
            'container_id': 'abc123',
            'has_drift': True,
            'drift_items': [{
                'field_path': 'ports.80/tcp',
                'baseline_value': '8080',
                'running_value': '8081',
                'severity': 'functional',
                'description': 'Port changed'
            }],
            'matched': True,
            'baseline_missing': False,
            'container_missing': False,
            'severity_counts': {
                'breaking': 0,
                'functional': 1,
                'cosmetic': 0,
                'informational': 0
            }
        }
        
        result = generator.generate_service_detail(service_drift)
        
        assert "Priority: MEDIUM" in result
        assert "Functional changes detected" in result


class TestGenerateRecommendations:
    """Test suite for generate_recommendations method."""
    
    def test_recommendations_no_drift(self):
        """Test recommendations when no drift detected."""
        generator = DriftReportGenerator()
        
        report_data = {
            'services_with_drift': 0,
            'breaking_services': 0
        }
        
        result = generator.generate_recommendations(report_data)
        
        assert "## Recommendations" in result
        assert "No action required" in result
    
    def test_recommendations_with_breaking_drift(self):
        """Test recommendations include breaking services priority."""
        generator = DriftReportGenerator()
        
        report_data = {
            'services_with_drift': 3,
            'breaking_services': 1
        }
        
        result = generator.generate_recommendations(report_data)
        
        assert "## Recommendations" in result
        assert "Immediate Actions" in result
        assert "1 service(s) with BREAKING drift" in result
    
    def test_recommendations_include_process_improvements(self):
        """Test that recommendations include process improvements."""
        generator = DriftReportGenerator()
        
        report_data = {
            'services_with_drift': 2,
            'breaking_services': 0
        }
        
        result = generator.generate_recommendations(report_data)
        
        assert "Process Improvements" in result
        assert "Automate drift detection" in result
        assert "PR workflow" in result


class TestGenerateMetadata:
    """Test suite for generate_metadata method."""
    
    def test_metadata_generation(self):
        """Test metadata section generation."""
        generator = DriftReportGenerator()
        
        report_data = {
            'timestamp': '2026-02-06T07:00:00',
            'baseline_host': '192.168.1.100',
            'baseline_repo': '/path/to/repo'
        }
        
        result = generator.generate_metadata(report_data)
        
        assert "---" in result
        assert "2026-02-06T07:00:00" in result
        assert "192.168.1.100" in result
        assert "/path/to/repo" in result


class TestGenerateMarkdownReport:
    """Test suite for generate_markdown_report method."""
    
    def test_complete_report_generation(self):
        """Test complete Markdown report generation."""
        generator = DriftReportGenerator()
        
        report_data = {
            'timestamp': '2026-02-06T07:00:00',
            'services_analyzed': 3,
            'services_with_drift': 1,
            'total_drift_items': 2,
            'baseline_host': '192.168.1.100',
            'baseline_repo': '/path/to/repo',
            'severity_summary': {
                'breaking': 1,
                'functional': 1,
                'cosmetic': 0,
                'informational': 0
            },
            'breaking_services': 1,
            'service_drifts': [
                {
                    'service_name': 'test-service',
                    'stack_name': 'test-stack',
                    'container_id': 'abc123',
                    'has_drift': True,
                    'drift_items': [{
                        'field_path': 'image',
                        'baseline_value': 'nginx:1.0',
                        'running_value': 'nginx:2.0',
                        'severity': 'breaking',
                        'description': 'Image changed'
                    }],
                    'matched': True,
                    'baseline_missing': False,
                    'container_missing': False,
                    'severity_counts': {
                        'breaking': 1,
                        'functional': 0,
                        'cosmetic': 0,
                        'informational': 0
                    }
                }
            ]
        }
        
        result = generator.generate_markdown_report(report_data)
        
        # Check main sections
        assert "# Configuration Drift Report" in result
        assert "## Executive Summary" in result
        assert "## Service Details" in result
        assert "## Recommendations" in result
        
        # Check service details
        assert "### test-service" in result
        assert "abc123" in result
        
        # Check footer
        assert "Report generated by Drift Detection Tool" in result
    
    def test_report_groups_drifted_services_first(self):
        """Test that drifted services are shown before clean services."""
        generator = DriftReportGenerator()
        
        report_data = {
            'timestamp': '2026-02-06T07:00:00',
            'services_analyzed': 2,
            'services_with_drift': 1,
            'total_drift_items': 1,
            'baseline_host': 'host',
            'baseline_repo': 'repo',
            'severity_summary': {
                'breaking': 0,
                'functional': 1,
                'cosmetic': 0,
                'informational': 0
            },
            'breaking_services': 0,
            'service_drifts': [
                {
                    'service_name': 'clean-service',
                    'stack_name': 'stack1',
                    'container_id': 'abc',
                    'has_drift': False,
                    'drift_items': [],
                    'matched': True,
                    'baseline_missing': False,
                    'container_missing': False,
                    'severity_counts': {
                        'breaking': 0,
                        'functional': 0,
                        'cosmetic': 0,
                        'informational': 0
                    }
                },
                {
                    'service_name': 'drifted-service',
                    'stack_name': 'stack2',
                    'container_id': 'def',
                    'has_drift': True,
                    'drift_items': [{
                        'field_path': 'test',
                        'baseline_value': 'a',
                        'running_value': 'b',
                        'severity': 'functional',
                        'description': 'test'
                    }],
                    'matched': True,
                    'baseline_missing': False,
                    'container_missing': False,
                    'severity_counts': {
                        'breaking': 0,
                        'functional': 1,
                        'cosmetic': 0,
                        'informational': 0
                    }
                }
            ]
        }
        
        result = generator.generate_markdown_report(report_data)
        
        # Drifted services should appear before clean services
        drifted_pos = result.find('drifted-service')
        clean_pos = result.find('clean-service')
        assert drifted_pos < clean_pos
    
    def test_report_uses_collapsible_for_clean_services(self):
        """Test that clean services use collapsible details section."""
        generator = DriftReportGenerator()
        
        report_data = {
            'timestamp': '2026-02-06T07:00:00',
            'services_analyzed': 1,
            'services_with_drift': 0,
            'total_drift_items': 0,
            'baseline_host': 'host',
            'baseline_repo': 'repo',
            'severity_summary': {
                'breaking': 0,
                'functional': 0,
                'cosmetic': 0,
                'informational': 0
            },
            'breaking_services': 0,
            'service_drifts': [
                {
                    'service_name': 'clean-service',
                    'stack_name': 'stack1',
                    'container_id': 'abc',
                    'has_drift': False,
                    'drift_items': [],
                    'matched': True,
                    'baseline_missing': False,
                    'container_missing': False,
                    'severity_counts': {
                        'breaking': 0,
                        'functional': 0,
                        'cosmetic': 0,
                        'informational': 0
                    }
                }
            ]
        }
        
        result = generator.generate_markdown_report(report_data)
        
        assert "<details>" in result
        assert "Click to expand clean services" in result


class TestSaveMarkdownReport:
    """Test suite for save_markdown_report method."""
    
    def test_save_report_creates_directory(self):
        """Test that save_markdown_report creates output directory."""
        generator = DriftReportGenerator()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "reports"
            
            report_data = {
                'timestamp': '2026-02-06T07:00:00',
                'services_analyzed': 1,
                'services_with_drift': 0,
                'total_drift_items': 0,
                'severity_summary': {
                    'breaking': 0,
                    'functional': 0,
                    'cosmetic': 0,
                    'informational': 0
                },
                'breaking_services': 0,
                'service_drifts': []
            }
            
            result_path = generator.save_markdown_report(report_data, output_dir)
            
            assert output_dir.exists()
            assert result_path.exists()
    
    def test_save_report_with_custom_filename(self):
        """Test saving report with custom filename."""
        generator = DriftReportGenerator()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            
            report_data = {
                'timestamp': '2026-02-06T07:00:00',
                'services_analyzed': 1,
                'services_with_drift': 0,
                'total_drift_items': 0,
                'severity_summary': {
                    'breaking': 0,
                    'functional': 0,
                    'cosmetic': 0,
                    'informational': 0
                },
                'breaking_services': 0,
                'service_drifts': []
            }
            
            result_path = generator.save_markdown_report(
                report_data,
                output_dir,
                filename="custom-report.md"
            )
            
            assert result_path.name == "custom-report.md"
            assert result_path.exists()
    
    def test_save_report_default_filename_format(self):
        """Test that default filename follows drift-YYYY-MM-DD-HH-MM-SS.md format."""
        generator = DriftReportGenerator()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            
            report_data = {
                'timestamp': '2026-02-06T07:00:00',
                'services_analyzed': 1,
                'services_with_drift': 0,
                'total_drift_items': 0,
                'severity_summary': {
                    'breaking': 0,
                    'functional': 0,
                    'cosmetic': 0,
                    'informational': 0
                },
                'breaking_services': 0,
                'service_drifts': []
            }
            
            result_path = generator.save_markdown_report(report_data, output_dir)
            
            assert result_path.name.startswith("drift-")
            assert result_path.name.endswith(".md")


class TestConvenienceFunctions:
    """Test suite for convenience functions."""
    
    def test_generate_markdown_report_function(self):
        """Test generate_markdown_report convenience function."""
        report_data = {
            'timestamp': '2026-02-06T07:00:00',
            'services_analyzed': 1,
            'services_with_drift': 0,
            'total_drift_items': 0,
            'severity_summary': {
                'breaking': 0,
                'functional': 0,
                'cosmetic': 0,
                'informational': 0
            },
            'breaking_services': 0,
            'service_drifts': []
        }
        
        result = generate_markdown_report(report_data)
        
        assert isinstance(result, str)
        assert "# Configuration Drift Report" in result
    
    def test_save_markdown_report_function(self):
        """Test save_markdown_report convenience function."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            
            report_data = {
                'timestamp': '2026-02-06T07:00:00',
                'services_analyzed': 1,
                'services_with_drift': 0,
                'total_drift_items': 0,
                'severity_summary': {
                    'breaking': 0,
                    'functional': 0,
                    'cosmetic': 0,
                    'informational': 0
                },
                'breaking_services': 0,
                'service_drifts': []
            }
            
            result_path = save_markdown_report(report_data, output_dir)
            
            assert isinstance(result_path, Path)
            assert result_path.exists()
