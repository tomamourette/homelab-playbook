"""Drift report generation in human-readable formats.

This module generates Markdown reports from drift analysis results,
providing executive summaries, detailed per-service diffs, and remediation guidance.
"""

import logging
from typing import Dict, Any, List
from pathlib import Path
from datetime import datetime


# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


class DriftReportGenerator:
    """Generate human-readable drift reports in Markdown format.
    
    This class takes structured drift data and produces formatted reports
    with executive summaries, detailed diffs, and remediation guidance.
    """
    
    # Severity emoji for visual impact
    SEVERITY_EMOJI = {
        'breaking': '🔴',
        'functional': '🟡',
        'cosmetic': '🔵',
        'informational': '⚪'
    }
    
    # Severity descriptions
    SEVERITY_DESC = {
        'breaking': 'BREAKING - Changes that break functionality',
        'functional': 'FUNCTIONAL - Changes that affect behavior',
        'cosmetic': 'COSMETIC - No functional impact',
        'informational': 'INFORMATIONAL - Expected differences'
    }
    
    def __init__(self):
        """Initialize report generator."""
        logger.info("Initialized DriftReportGenerator")
    
    def format_value(self, value: Any, max_length: int = 80) -> str:
        """Format a value for display in report.
        
        Args:
            value: Value to format
            max_length: Maximum length before truncation
        
        Returns:
            Formatted string representation
        """
        if value is None:
            return "*[not set]*"
        
        # Convert to string
        str_value = str(value)
        
        # Truncate if too long
        if len(str_value) > max_length:
            return str_value[:max_length-3] + "..."
        
        return str_value
    
    def generate_executive_summary(self, report_data: Dict[str, Any]) -> str:
        """Generate executive summary section.
        
        Args:
            report_data: Drift report dictionary
        
        Returns:
            Markdown formatted summary
        """
        summary = []
        summary.append("## Executive Summary\n")
        
        # Overall statistics
        total_services = report_data['services_analyzed']
        drifted_services = report_data['services_with_drift']
        total_items = report_data['total_drift_items']
        
        if drifted_services == 0:
            summary.append("✅ **No configuration drift detected!**\n")
            summary.append(f"All {total_services} service(s) match their git baselines.\n")
        else:
            drift_pct = (drifted_services / total_services * 100) if total_services > 0 else 0
            summary.append(f"⚠️  **Configuration drift detected in {drifted_services} of {total_services} service(s) ({drift_pct:.1f}%)**\n")
            summary.append(f"\nTotal drift items: **{total_items}**\n")
        
        # Severity breakdown
        severity_summary = report_data['severity_summary']
        summary.append("\n### Drift by Severity\n")
        summary.append("\n| Severity | Count | Description |\n")
        summary.append("|----------|-------|-------------|\n")
        
        for severity_name, count in severity_summary.items():
            emoji = self.SEVERITY_EMOJI.get(severity_name, '')
            desc = self.SEVERITY_DESC.get(severity_name, '')
            summary.append(f"| {emoji} {severity_name.title()} | **{count}** | {desc} |\n")
        
        # Critical alert for breaking changes
        breaking_count = report_data.get('breaking_services', 0)
        if breaking_count > 0:
            summary.append(f"\n🚨 **CRITICAL**: {breaking_count} service(s) have BREAKING drift that may impact functionality!\n")
        
        return ''.join(summary)
    
    def generate_service_detail(self, service_drift: Dict[str, Any]) -> str:
        """Generate detailed drift section for a single service.
        
        Args:
            service_drift: ServiceDrift dictionary
        
        Returns:
            Markdown formatted service detail
        """
        detail = []
        
        service_name = service_drift['service_name']
        stack_name = service_drift.get('stack_name', 'unknown')
        container_id = service_drift.get('container_id', 'N/A')
        
        # Service header
        detail.append(f"### {service_name}\n")
        detail.append(f"\n**Stack**: {stack_name}  \n")
        detail.append(f"**Container ID**: `{container_id}`  \n")
        
        # Handle special cases
        if service_drift.get('baseline_missing'):
            detail.append("\n❌ **Status**: Running but NOT found in git baselines\n")
            detail.append("\n**Recommended Action**: Add this service to git repository or remove if no longer needed.\n")
            return ''.join(detail)
        
        if service_drift.get('container_missing'):
            detail.append("\n❌ **Status**: Defined in git but NOT running\n")
            detail.append("\n**Recommended Action**: Deploy this service or remove from git if deprecated.\n")
            return ''.join(detail)
        
        # Drift status
        if not service_drift['has_drift']:
            detail.append("\n✅ **Status**: No drift detected\n")
            return ''.join(detail)
        
        # Drift items
        drift_items = service_drift['drift_items']
        severity_counts = service_drift['severity_counts']
        
        detail.append(f"\n⚠️  **Status**: Drift detected ({len(drift_items)} item(s))\n")
        
        # Severity summary for this service
        detail.append("\n**Severity Breakdown**:  \n")
        for severity, count in severity_counts.items():
            if count > 0:
                emoji = self.SEVERITY_EMOJI.get(severity, '')
                detail.append(f"- {emoji} {severity.title()}: {count}  \n")
        
        # Detailed drift items
        detail.append("\n#### Configuration Differences\n")
        
        # Group by severity
        by_severity = {
            'breaking': [],
            'functional': [],
            'cosmetic': [],
            'informational': []
        }
        
        for item in drift_items:
            severity = item['severity']
            by_severity[severity].append(item)
        
        # Output by severity (breaking first)
        for severity in ['breaking', 'functional', 'cosmetic', 'informational']:
            items = by_severity[severity]
            if not items:
                continue
            
            emoji = self.SEVERITY_EMOJI[severity]
            detail.append(f"\n**{emoji} {severity.title()} Changes**\n")
            
            for item in items:
                field_path = item['field_path']
                baseline_val = self.format_value(item['baseline_value'])
                running_val = self.format_value(item['running_value'])
                
                detail.append(f"\n- **{field_path}**\n")
                detail.append(f"  - Baseline: `{baseline_val}`\n")
                detail.append(f"  - Running: `{running_val}`\n")
        
        # Remediation recommendations
        detail.append("\n#### Recommended Actions\n")
        
        has_breaking = severity_counts['breaking'] > 0
        has_functional = severity_counts['functional'] > 0
        
        if has_breaking:
            detail.append("\n🚨 **Priority: HIGH** - Breaking changes detected\n")
            detail.append("1. Review image version and critical environment variable changes\n")
            detail.append("2. Update git baseline to match running configuration (if running config is correct)\n")
            detail.append("3. OR redeploy service from git baseline (if git is correct)\n")
        elif has_functional:
            detail.append("\n⚠️  **Priority: MEDIUM** - Functional changes detected\n")
            detail.append("1. Review port, volume, and network configuration differences\n")
            detail.append("2. Update git baseline to match running configuration\n")
        else:
            detail.append("\n✨ **Priority: LOW** - Cosmetic changes only\n")
            detail.append("1. Update git baseline for documentation accuracy\n")
            detail.append("2. No functional impact expected\n")
        
        return ''.join(detail)
    
    def generate_recommendations(self, report_data: Dict[str, Any]) -> str:
        """Generate overall recommendations section.
        
        Args:
            report_data: Drift report dictionary
        
        Returns:
            Markdown formatted recommendations
        """
        recommendations = []
        recommendations.append("## Recommendations\n")
        
        breaking_services = report_data.get('breaking_services', 0)
        services_with_drift = report_data['services_with_drift']
        
        if services_with_drift == 0:
            recommendations.append("\n✅ No action required - all services match their baselines.\n")
            return ''.join(recommendations)
        
        recommendations.append("\n### Immediate Actions\n")
        
        if breaking_services > 0:
            recommendations.append(f"\n1. **Review {breaking_services} service(s) with BREAKING drift** (highest priority)\n")
            recommendations.append("   - Verify running configurations are correct\n")
            recommendations.append("   - Update git baselines or redeploy services\n")
        
        recommendations.append(f"\n2. **Review all {services_with_drift} drifted service(s)**\n")
        recommendations.append("   - Determine if running config or git baseline is authoritative\n")
        recommendations.append("   - Create Pull Requests to sync git with running state\n")
        
        recommendations.append("\n### Process Improvements\n")
        recommendations.append("\n- **Automate drift detection**: Run this tool regularly (daily/weekly)\n")
        recommendations.append("- **Enforce PR workflow**: All infrastructure changes via Pull Request\n")
        recommendations.append("- **Document decisions**: Capture reasoning for configuration changes in commit messages\n")
        recommendations.append("- **Validate deployments**: Check drift after each deployment\n")
        
        return ''.join(recommendations)
    
    def generate_metadata(self, report_data: Dict[str, Any]) -> str:
        """Generate report metadata section.
        
        Args:
            report_data: Drift report dictionary
        
        Returns:
            Markdown formatted metadata
        """
        metadata = []
        metadata.append("---\n")
        
        timestamp = report_data['timestamp']
        baseline_host = report_data.get('baseline_host', 'N/A')
        baseline_repo = report_data.get('baseline_repo', 'N/A')
        
        metadata.append(f"**Report Generated**: {timestamp}  \n")
        metadata.append(f"**Target Host**: {baseline_host}  \n")
        metadata.append(f"**Baseline Repository**: {baseline_repo}  \n")
        metadata.append("---\n")
        
        return ''.join(metadata)
    
    def generate_markdown_report(self, report_data: Dict[str, Any]) -> str:
        """Generate complete Markdown drift report.
        
        Args:
            report_data: DriftReport dictionary from compare_configurations()
        
        Returns:
            Complete Markdown formatted report
        """
        logger.info("Generating Markdown drift report...")
        
        sections = []
        
        # Title
        sections.append("# Configuration Drift Report\n\n")
        
        # Metadata
        sections.append(self.generate_metadata(report_data))
        sections.append("\n")
        
        # Executive Summary
        sections.append(self.generate_executive_summary(report_data))
        sections.append("\n")
        
        # Service Details
        sections.append("## Service Details\n\n")
        
        service_drifts = report_data.get('service_drifts', [])
        
        # Show drifted services first
        drifted_services = [s for s in service_drifts if s['has_drift']]
        clean_services = [s for s in service_drifts if not s['has_drift']]
        
        if drifted_services:
            sections.append("### Services with Drift\n\n")
            for service_drift in drifted_services:
                sections.append(self.generate_service_detail(service_drift))
                sections.append("\n---\n\n")
        
        if clean_services:
            sections.append("### Services without Drift\n\n")
            sections.append("<details>\n<summary>Click to expand clean services</summary>\n\n")
            for service_drift in clean_services:
                sections.append(self.generate_service_detail(service_drift))
                sections.append("\n")
            sections.append("</details>\n\n")
        
        # Recommendations
        sections.append(self.generate_recommendations(report_data))
        sections.append("\n")
        
        # Footer
        sections.append("---\n")
        sections.append("*Report generated by Drift Detection Tool*\n")
        
        report = ''.join(sections)
        logger.info(f"Generated Markdown report ({len(report)} characters)")
        
        return report
    
    def save_markdown_report(
        self,
        report_data: Dict[str, Any],
        output_dir: Path,
        filename: str = None
    ) -> Path:
        """Generate and save Markdown report to file.
        
        Args:
            report_data: DriftReport dictionary
            output_dir: Directory to save report
            filename: Optional filename (defaults to drift-YYYY-MM-DD-HH-MM-SS.md)
        
        Returns:
            Path to saved report file
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate filename if not provided
        if filename is None:
            timestamp = datetime.utcnow().strftime("%Y-%m-%d-%H-%M-%S")
            filename = f"drift-{timestamp}.md"
        
        report_path = output_dir / filename
        
        # Generate report
        markdown_content = self.generate_markdown_report(report_data)
        
        # Save to file
        with open(report_path, 'w') as f:
            f.write(markdown_content)
        
        logger.info(f"Saved Markdown report to {report_path}")
        
        return report_path


def generate_markdown_report(report_data: Dict[str, Any]) -> str:
    """Convenience function to generate Markdown report.
    
    Args:
        report_data: DriftReport dictionary
    
    Returns:
        Markdown formatted report string
    """
    generator = DriftReportGenerator()
    return generator.generate_markdown_report(report_data)


def save_markdown_report(
    report_data: Dict[str, Any],
    output_dir: Path,
    filename: str = None
) -> Path:
    """Convenience function to save Markdown report.
    
    Args:
        report_data: DriftReport dictionary
        output_dir: Directory to save report
        filename: Optional filename
    
    Returns:
        Path to saved report file
    """
    generator = DriftReportGenerator()
    return generator.save_markdown_report(report_data, output_dir, filename)
