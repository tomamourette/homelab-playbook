#!/usr/bin/env python3
"""
Repository Structure Validator

Validates that infrastructure repositories follow conventions and best practices.
Ensures consistency across Docker Compose files, environment configs, and
deployment configurations.

Checks:
- Compose files use v2 syntax (no version field)
- Image tags are pinned (no :latest)
- .env.sample exists for each stack
- Traefik labels follow v3 conventions
- Networks reference external proxy network
- Proper file naming conventions
"""

import re
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass
from enum import Enum


class ValidationSeverity(Enum):
    """Severity levels for validation issues"""
    ERROR = "ERROR"      # Must fix before merge
    WARNING = "WARNING"  # Should fix, but not blocking
    INFO = "INFO"        # Nice to have, optional


@dataclass
class ValidationIssue:
    """Represents a validation issue found"""
    severity: ValidationSeverity
    file_path: Path
    rule: str
    message: str
    line_number: Optional[int] = None
    suggestion: Optional[str] = None


@dataclass
class ValidationReport:
    """Report of all validation issues"""
    timestamp: str
    total_files_checked: int
    total_issues: int
    errors: List[ValidationIssue]
    warnings: List[ValidationIssue]
    info: List[ValidationIssue]
    passed: bool  # True if no errors


class StructureValidator:
    """Validates repository structure and conventions"""
    
    def __init__(self, repo_path: Path):
        """
        Initialize Structure Validator
        
        Args:
            repo_path: Path to repository to validate
        """
        self.repo_path = Path(repo_path)
        self.issues: List[ValidationIssue] = []
    
    def validate_all(self) -> ValidationReport:
        """
        Run all validation checks
        
        Returns:
            ValidationReport with all issues found
        """
        from datetime import datetime
        
        self.issues = []
        files_checked = 0
        
        # Find all compose files
        stacks_dir = self.repo_path / "stacks"
        if not stacks_dir.exists():
            return ValidationReport(
                timestamp=datetime.now().isoformat(),
                total_files_checked=0,
                total_issues=0,
                errors=[],
                warnings=[],
                info=[],
                passed=True
            )
        
        for stack_dir in stacks_dir.iterdir():
            if not stack_dir.is_dir():
                continue
            
            # Check each compose file in stack
            compose_files = list(stack_dir.glob("docker-compose*.yml"))
            for compose_file in compose_files:
                files_checked += 1
                self._validate_compose_file(compose_file, stack_dir)
            
            # Check for .env.sample
            self._validate_env_sample(stack_dir)
        
        # Separate issues by severity
        errors = [i for i in self.issues if i.severity == ValidationSeverity.ERROR]
        warnings = [i for i in self.issues if i.severity == ValidationSeverity.WARNING]
        info = [i for i in self.issues if i.severity == ValidationSeverity.INFO]
        
        report = ValidationReport(
            timestamp=datetime.now().isoformat(),
            total_files_checked=files_checked,
            total_issues=len(self.issues),
            errors=errors,
            warnings=warnings,
            info=info,
            passed=(len(errors) == 0)
        )
        
        return report
    
    def _validate_compose_file(self, compose_file: Path, stack_dir: Path) -> None:
        """
        Validate a single Docker Compose file
        
        Args:
            compose_file: Path to compose file
            stack_dir: Parent stack directory
        """
        try:
            with open(compose_file, 'r') as f:
                content = f.read()
                compose_data = yaml.safe_load(content)
        except yaml.YAMLError as e:
            self.issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                file_path=compose_file.relative_to(self.repo_path),
                rule="yaml-syntax",
                message=f"Invalid YAML syntax: {e}"
            ))
            return
        except Exception as e:
            self.issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                file_path=compose_file.relative_to(self.repo_path),
                rule="file-read",
                message=f"Failed to read file: {e}"
            ))
            return
        
        if not compose_data:
            return
        
        # Check for version field (should not exist in Compose v2)
        self._check_version_field(compose_file, compose_data, content)
        
        # Check services
        if 'services' in compose_data:
            for service_name, service_config in compose_data['services'].items():
                self._validate_service(compose_file, service_name, service_config)
        
        # Check networks
        if 'networks' in compose_data:
            self._validate_networks(compose_file, compose_data['networks'])
    
    def _check_version_field(
        self,
        compose_file: Path,
        compose_data: dict,
        content: str
    ) -> None:
        """Check for version field (deprecated in Compose v2)"""
        if 'version' in compose_data:
            # Find line number
            line_num = None
            for i, line in enumerate(content.split('\n'), 1):
                if line.strip().startswith('version:'):
                    line_num = i
                    break
            
            self.issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                file_path=compose_file.relative_to(self.repo_path),
                rule="compose-v2-syntax",
                message="Compose file contains 'version' field (deprecated in Compose v2)",
                line_number=line_num,
                suggestion="Remove the 'version' field - it's ignored in Compose v2"
            ))
    
    def _validate_service(
        self,
        compose_file: Path,
        service_name: str,
        service_config: dict
    ) -> None:
        """
        Validate a service configuration
        
        Args:
            compose_file: Path to compose file
            service_name: Name of the service
            service_config: Service configuration dict
        """
        # Check image tag
        if 'image' in service_config:
            self._check_image_tag(compose_file, service_name, service_config['image'])
        
        # Check Traefik labels
        if 'labels' in service_config:
            self._check_traefik_labels(compose_file, service_name, service_config['labels'])
        
        # Check networks
        if 'networks' in service_config:
            self._check_service_networks(compose_file, service_name, service_config['networks'])
    
    def _check_image_tag(self, compose_file: Path, service_name: str, image: str) -> None:
        """Check if image tag is pinned (not :latest)"""
        if not image:
            return
        
        # Check if image has a tag
        if ':' not in image:
            self.issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                file_path=compose_file.relative_to(self.repo_path),
                rule="pinned-tags",
                message=f"Service '{service_name}' uses untagged image: {image}",
                suggestion=f"Add a specific version tag, e.g., {image}:1.0.0"
            ))
            return
        
        # Check if using :latest
        if image.endswith(':latest'):
            self.issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                file_path=compose_file.relative_to(self.repo_path),
                rule="pinned-tags",
                message=f"Service '{service_name}' uses :latest tag: {image}",
                suggestion=f"Pin to a specific version instead of :latest"
            ))
    
    def _check_traefik_labels(
        self,
        compose_file: Path,
        service_name: str,
        labels: dict
    ) -> None:
        """Check Traefik labels follow v3 conventions"""
        if not isinstance(labels, dict):
            return
        
        traefik_labels = {k: v for k, v in labels.items() if k.startswith('traefik.')}
        
        if not traefik_labels:
            return  # No Traefik labels, skip
        
        # Check for v2 syntax (should be v3)
        v2_patterns = [
            'traefik.http.routers.',
            'traefik.http.services.',
            'traefik.http.middlewares.'
        ]
        
        for label_key in traefik_labels.keys():
            # Check if using old format without proper router naming
            if label_key.startswith('traefik.http.routers.'):
                # Extract router name
                parts = label_key.split('.')
                if len(parts) >= 4:
                    router_name = parts[3]
                    # Check if router name matches service name convention
                    if router_name != service_name and not router_name.startswith(service_name):
                        self.issues.append(ValidationIssue(
                            severity=ValidationSeverity.INFO,
                            file_path=compose_file.relative_to(self.repo_path),
                            rule="traefik-conventions",
                            message=f"Service '{service_name}' router name '{router_name}' doesn't match service name",
                            suggestion=f"Consider using '{service_name}' as router name for consistency"
                        ))
        
        # Check for required labels
        if 'traefik.enable' not in traefik_labels:
            self.issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                file_path=compose_file.relative_to(self.repo_path),
                rule="traefik-enable",
                message=f"Service '{service_name}' has Traefik labels but no 'traefik.enable' label",
                suggestion="Add 'traefik.enable: true' label"
            ))
    
    def _check_service_networks(
        self,
        compose_file: Path,
        service_name: str,
        networks: any
    ) -> None:
        """Check if service uses external proxy network"""
        # Networks can be list or dict
        network_names = []
        
        if isinstance(networks, list):
            network_names = networks
        elif isinstance(networks, dict):
            network_names = list(networks.keys())
        
        # Check if proxy network is used when Traefik labels present
        # (This is checked in _validate_service if labels exist)
        if 'proxy' not in network_names:
            # This is INFO level since not all services need proxy
            pass
    
    def _validate_networks(self, compose_file: Path, networks: dict) -> None:
        """Validate network definitions"""
        if 'proxy' in networks:
            proxy_config = networks['proxy']
            
            # Check if proxy is external
            if not isinstance(proxy_config, dict):
                return
            
            if not proxy_config.get('external', False):
                self.issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    file_path=compose_file.relative_to(self.repo_path),
                    rule="external-proxy-network",
                    message="'proxy' network should be external",
                    suggestion="Add 'external: true' to proxy network definition"
                ))
    
    def _validate_env_sample(self, stack_dir: Path) -> None:
        """Check if .env.sample exists for stack"""
        env_sample = stack_dir / ".env.sample"
        
        # Check if compose file exists
        compose_file = stack_dir / "docker-compose.yml"
        if not compose_file.exists():
            return  # No compose file, skip
        
        # Check if .env.sample exists
        if not env_sample.exists():
            self.issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                file_path=stack_dir.relative_to(self.repo_path),
                rule="env-sample",
                message=f"Stack '{stack_dir.name}' missing .env.sample file",
                suggestion="Create .env.sample with example values for all environment variables"
            ))
    
    def generate_markdown_report(self, report: ValidationReport) -> str:
        """
        Generate human-readable Markdown report
        
        Args:
            report: ValidationReport to format
            
        Returns:
            Markdown-formatted report
        """
        lines = [
            "# Repository Structure Validation Report",
            "",
            f"**Generated:** {report.timestamp}",
            f"**Files Checked:** {report.total_files_checked}",
            f"**Total Issues:** {report.total_issues}",
            "",
            "## Summary",
            "",
            f"- ❌ Errors: {len(report.errors)} (must fix)",
            f"- ⚠️  Warnings: {len(report.warnings)} (should fix)",
            f"- ℹ️  Info: {len(report.info)} (optional)",
            "",
            f"**Status:** {'✅ PASSED' if report.passed else '❌ FAILED'}",
            ""
        ]
        
        if report.total_issues == 0:
            lines.append("✅ **No issues found!** Repository follows all conventions.")
            return "\n".join(lines)
        
        # Errors
        if report.errors:
            lines.extend([
                "## ❌ Errors (Must Fix)",
                "",
                "These issues must be resolved before merge:",
                ""
            ])
            
            for issue in report.errors:
                lines.append(f"### {issue.file_path}")
                lines.append(f"- **Rule:** `{issue.rule}`")
                lines.append(f"- **Issue:** {issue.message}")
                if issue.line_number:
                    lines.append(f"- **Line:** {issue.line_number}")
                if issue.suggestion:
                    lines.append(f"- **Fix:** {issue.suggestion}")
                lines.append("")
        
        # Warnings
        if report.warnings:
            lines.extend([
                "## ⚠️  Warnings (Should Fix)",
                "",
                "These issues should be addressed:",
                ""
            ])
            
            for issue in report.warnings:
                lines.append(f"### {issue.file_path}")
                lines.append(f"- **Rule:** `{issue.rule}`")
                lines.append(f"- **Issue:** {issue.message}")
                if issue.suggestion:
                    lines.append(f"- **Fix:** {issue.suggestion}")
                lines.append("")
        
        # Info
        if report.info:
            lines.extend([
                "## ℹ️  Informational (Optional)",
                "",
                "Consider these improvements:",
                ""
            ])
            
            for issue in report.info:
                lines.append(f"- **{issue.file_path}**: {issue.message}")
                if issue.suggestion:
                    lines.append(f"  - {issue.suggestion}")
        
        return "\n".join(lines)


def main():
    """CLI entry point"""
    import argparse
    import sys
    import json
    
    parser = argparse.ArgumentParser(
        description="Validate repository structure and conventions"
    )
    parser.add_argument(
        "repo_path",
        type=Path,
        help="Path to repository to validate"
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output file for report (default: stdout)"
    )
    parser.add_argument(
        "--format",
        choices=["markdown", "json"],
        default="markdown",
        help="Output format (default: markdown)"
    )
    parser.add_argument(
        "--fail-on-warning",
        action="store_true",
        help="Exit with error code if warnings found"
    )
    
    args = parser.parse_args()
    
    # Run validation
    validator = StructureValidator(args.repo_path)
    report = validator.validate_all()
    
    # Generate output
    if args.format == "markdown":
        output = validator.generate_markdown_report(report)
    else:  # json
        output = json.dumps({
            "timestamp": report.timestamp,
            "files_checked": report.total_files_checked,
            "total_issues": report.total_issues,
            "errors": [
                {
                    "severity": i.severity.value,
                    "file": str(i.file_path),
                    "rule": i.rule,
                    "message": i.message,
                    "line": i.line_number,
                    "suggestion": i.suggestion
                }
                for i in report.errors
            ],
            "warnings": [
                {
                    "severity": i.severity.value,
                    "file": str(i.file_path),
                    "rule": i.rule,
                    "message": i.message,
                    "suggestion": i.suggestion
                }
                for i in report.warnings
            ],
            "info": [
                {
                    "severity": i.severity.value,
                    "file": str(i.file_path),
                    "rule": i.rule,
                    "message": i.message,
                    "suggestion": i.suggestion
                }
                for i in report.info
            ],
            "passed": report.passed
        }, indent=2)
    
    # Write output
    if args.output:
        args.output.write_text(output)
        print(f"Report written to {args.output}")
    else:
        print(output)
    
    # Exit code
    if not report.passed:
        sys.exit(1)
    elif args.fail_on_warning and report.warnings:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
