#!/usr/bin/env python3
"""
Repository Cleanup Detector

Identifies stale configuration files in git repositories that have no
corresponding running containers. Helps maintain clean infrastructure repos.

Features:
- Detect orphaned compose files
- Find unused .env files
- Check stack-targets.yml deployment mappings
- Generate cleanup reports
- Optional PR generation for file removal (with confirmation)
"""

import os
import yaml
from pathlib import Path
from typing import Dict, List, Set, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

from config import Config
from docker_inspector import DockerInspector
from git_config_loader import GitConfigLoader


@dataclass
class StaleFile:
    """Represents a stale file that should be cleaned up"""
    file_path: Path
    file_type: str  # "compose", "env", "other"
    reason: str
    stack_name: str
    service_names: List[str]


@dataclass
class CleanupReport:
    """Report of stale files found"""
    timestamp: str
    total_stale_files: int
    stale_compose_files: List[StaleFile]
    stale_env_files: List[StaleFile]
    stale_other_files: List[StaleFile]
    running_services: Set[str]
    git_services: Set[str]


class CleanupDetector:
    """Detects stale configuration files in infrastructure repositories"""
    
    def __init__(self, config: Config):
        """
        Initialize Cleanup Detector
        
        Args:
            config: Configuration object with repository paths
        """
        self.config = config
        self.docker_inspector = DockerInspector(config)
        self.git_loader = GitConfigLoader(config.apps_repo_path)
    
    def detect_stale_files(
        self,
        check_deployment_targets: bool = True
    ) -> CleanupReport:
        """
        Detect all stale files in the repository
        
        Args:
            check_deployment_targets: Whether to check stack-targets.yml
            
        Returns:
            CleanupReport with all detected stale files
        """
        # Get running containers
        running_services = self._get_running_services()
        
        # Get services from git
        git_services = self._get_git_services()
        
        # Find stale files
        stale_compose = self._find_stale_compose_files(running_services, git_services)
        stale_env = self._find_stale_env_files(running_services)
        stale_other = []
        
        if check_deployment_targets:
            stale_other.extend(
                self._check_deployment_targets(running_services, git_services)
            )
        
        report = CleanupReport(
            timestamp=datetime.now().isoformat(),
            total_stale_files=len(stale_compose) + len(stale_env) + len(stale_other),
            stale_compose_files=stale_compose,
            stale_env_files=stale_env,
            stale_other_files=stale_other,
            running_services=running_services,
            git_services=git_services
        )
        
        return report
    
    def _get_running_services(self) -> Set[str]:
        """
        Get set of all running service names across all endpoints
        
        Returns:
            Set of service names
        """
        running = set()
        
        for endpoint_name in self.config.endpoints.keys():
            try:
                containers = self.docker_inspector.inspect_endpoint(endpoint_name)
                for container_name in containers.keys():
                    # Extract service name (remove stack prefix if present)
                    service_name = self._extract_service_name(container_name)
                    running.add(service_name)
            except Exception as e:
                print(f"Warning: Failed to inspect {endpoint_name}: {e}")
        
        return running
    
    def _extract_service_name(self, container_name: str) -> str:
        """
        Extract service name from container name
        
        Container names may be:
        - stack_service_1
        - service
        - stack-service-1
        
        Args:
            container_name: Full container name
            
        Returns:
            Extracted service name
        """
        # Remove trailing _N or -N (replica number)
        name = container_name.rstrip('0123456789').rstrip('_-')
        
        # If contains stack prefix, extract service part
        if '_' in name:
            parts = name.split('_')
            if len(parts) >= 2:
                return parts[-1]  # Return last part (service name)
        
        if '-' in name:
            parts = name.split('-')
            if len(parts) >= 2:
                return parts[-1]
        
        return name
    
    def _get_git_services(self) -> Set[str]:
        """
        Get set of all service names defined in git
        
        Returns:
            Set of service names from compose files
        """
        git_services = set()
        
        baselines = self.git_loader.load_all_baselines()
        for baseline in baselines:
            git_services.add(baseline.service_name)
        
        return git_services
    
    def _find_stale_compose_files(
        self,
        running_services: Set[str],
        git_services: Set[str]
    ) -> List[StaleFile]:
        """
        Find compose files with no corresponding running containers
        
        Args:
            running_services: Set of running service names
            git_services: Set of service names from git
            
        Returns:
            List of stale compose files
        """
        stale_files = []
        
        stacks_dir = self.config.apps_repo_path / "stacks"
        if not stacks_dir.exists():
            return stale_files
        
        for stack_dir in stacks_dir.iterdir():
            if not stack_dir.is_dir():
                continue
            
            stack_name = stack_dir.name
            
            # Find all compose files in stack
            compose_files = list(stack_dir.glob("docker-compose*.yml"))
            
            for compose_file in compose_files:
                # Load compose file
                try:
                    with open(compose_file, 'r') as f:
                        compose_data = yaml.safe_load(f)
                except Exception as e:
                    print(f"Warning: Failed to parse {compose_file}: {e}")
                    continue
                
                if 'services' not in compose_data:
                    continue
                
                # Get services defined in this compose file
                defined_services = list(compose_data['services'].keys())
                
                # Check if any service is running
                has_running_service = any(
                    svc in running_services for svc in defined_services
                )
                
                if not has_running_service:
                    stale_files.append(StaleFile(
                        file_path=compose_file.relative_to(self.config.apps_repo_path),
                        file_type="compose",
                        reason="No services from this compose file are currently running",
                        stack_name=stack_name,
                        service_names=defined_services
                    ))
        
        return stale_files
    
    def _find_stale_env_files(self, running_services: Set[str]) -> List[StaleFile]:
        """
        Find .env files for services that are not running
        
        Args:
            running_services: Set of running service names
            
        Returns:
            List of stale .env files
        """
        stale_files = []
        
        stacks_dir = self.config.apps_repo_path / "stacks"
        if not stacks_dir.exists():
            return stale_files
        
        for stack_dir in stacks_dir.iterdir():
            if not stack_dir.is_dir():
                continue
            
            stack_name = stack_dir.name
            
            # Check for .env files (not .env.sample)
            env_files = [f for f in stack_dir.glob(".env*") if f.name != ".env.sample"]
            
            for env_file in env_files:
                # Check if stack has any running services
                # Get services from compose file
                compose_file = stack_dir / "docker-compose.yml"
                if not compose_file.exists():
                    # No compose file, env is definitely stale
                    stale_files.append(StaleFile(
                        file_path=env_file.relative_to(self.config.apps_repo_path),
                        file_type="env",
                        reason="No docker-compose.yml found for this stack",
                        stack_name=stack_name,
                        service_names=[]
                    ))
                    continue
                
                try:
                    with open(compose_file, 'r') as f:
                        compose_data = yaml.safe_load(f)
                except Exception:
                    continue
                
                if 'services' not in compose_data:
                    continue
                
                defined_services = list(compose_data['services'].keys())
                has_running = any(svc in running_services for svc in defined_services)
                
                if not has_running:
                    stale_files.append(StaleFile(
                        file_path=env_file.relative_to(self.config.apps_repo_path),
                        file_type="env",
                        reason="No services from this stack are running",
                        stack_name=stack_name,
                        service_names=defined_services
                    ))
        
        return stale_files
    
    def _check_deployment_targets(
        self,
        running_services: Set[str],
        git_services: Set[str]
    ) -> List[StaleFile]:
        """
        Check stack-targets.yml for stale deployment mappings
        
        Args:
            running_services: Set of running service names
            git_services: Set of service names from git
            
        Returns:
            List of issues found in stack-targets.yml
        """
        stale_files = []
        
        targets_file = self.config.apps_repo_path / "stack-targets.yml"
        if not targets_file.exists():
            return stale_files
        
        try:
            with open(targets_file, 'r') as f:
                targets_data = yaml.safe_load(f)
        except Exception as e:
            print(f"Warning: Failed to parse stack-targets.yml: {e}")
            return stale_files
        
        if not targets_data:
            return stale_files
        
        # Check each stack mapping
        for stack_name, deployment_info in targets_data.items():
            if not isinstance(deployment_info, dict):
                continue
            
            # Check if stack has any running services
            stack_dir = self.config.apps_repo_path / "stacks" / stack_name
            if not stack_dir.exists():
                stale_files.append(StaleFile(
                    file_path=Path("stack-targets.yml"),
                    file_type="deployment_mapping",
                    reason=f"Stack '{stack_name}' directory does not exist",
                    stack_name=stack_name,
                    service_names=[]
                ))
                continue
            
            # Get services for this stack
            compose_file = stack_dir / "docker-compose.yml"
            if not compose_file.exists():
                continue
            
            try:
                with open(compose_file, 'r') as f:
                    compose_data = yaml.safe_load(f)
            except Exception:
                continue
            
            if 'services' not in compose_data:
                continue
            
            defined_services = list(compose_data['services'].keys())
            has_running = any(svc in running_services for svc in defined_services)
            
            if not has_running:
                stale_files.append(StaleFile(
                    file_path=Path("stack-targets.yml"),
                    file_type="deployment_mapping",
                    reason=f"No services from stack '{stack_name}' are running",
                    stack_name=stack_name,
                    service_names=defined_services
                ))
        
        return stale_files
    
    def generate_cleanup_report_markdown(self, report: CleanupReport) -> str:
        """
        Generate human-readable Markdown cleanup report
        
        Args:
            report: CleanupReport to format
            
        Returns:
            Markdown-formatted report
        """
        lines = [
            "# Repository Cleanup Report",
            "",
            f"**Generated:** {report.timestamp}",
            f"**Total Stale Files:** {report.total_stale_files}",
            "",
            "## Summary",
            "",
            f"- Running Services: {len(report.running_services)}",
            f"- Services in Git: {len(report.git_services)}",
            f"- Stale Compose Files: {len(report.stale_compose_files)}",
            f"- Stale .env Files: {len(report.stale_env_files)}",
            f"- Other Issues: {len(report.stale_other_files)}",
            ""
        ]
        
        if report.total_stale_files == 0:
            lines.append("✅ **No stale files detected!** Repository is clean.")
            return "\n".join(lines)
        
        # Stale compose files
        if report.stale_compose_files:
            lines.extend([
                "## 🗑️ Stale Compose Files",
                "",
                "These compose files have no services currently running:",
                ""
            ])
            
            for stale in report.stale_compose_files:
                lines.append(f"### `{stale.file_path}`")
                lines.append(f"- **Stack:** {stale.stack_name}")
                lines.append(f"- **Services:** {', '.join(stale.service_names)}")
                lines.append(f"- **Reason:** {stale.reason}")
                lines.append("")
        
        # Stale .env files
        if report.stale_env_files:
            lines.extend([
                "## 🔐 Stale .env Files",
                "",
                "These .env files belong to stacks with no running services:",
                ""
            ])
            
            for stale in report.stale_env_files:
                lines.append(f"- `{stale.file_path}` ({stale.stack_name})")
                lines.append(f"  - {stale.reason}")
        
        # Other issues
        if report.stale_other_files:
            lines.extend([
                "",
                "## ⚠️ Deployment Mapping Issues",
                "",
                "Issues found in `stack-targets.yml`:",
                ""
            ])
            
            for stale in report.stale_other_files:
                lines.append(f"- **{stale.stack_name}**")
                lines.append(f"  - {stale.reason}")
                if stale.service_names:
                    lines.append(f"  - Services: {', '.join(stale.service_names)}")
                lines.append("")
        
        # Recommendations
        lines.extend([
            "## 💡 Recommendations",
            "",
            "**Conservative Approach:**",
            "1. Review each stale file manually",
            "2. Confirm services are truly decomissioned",
            "3. Check if files are needed for other environments",
            "4. Create PR to remove confirmed stale files",
            "",
            "**Command to generate cleanup PR:**",
            "```bash",
            "python cleanup_detector.py generate-pr --report cleanup-report.json",
            "```",
            ""
        ])
        
        return "\n".join(lines)
    
    def save_cleanup_report(
        self,
        report: CleanupReport,
        output_dir: Path,
        format: str = "both"
    ) -> Tuple[Optional[Path], Optional[Path]]:
        """
        Save cleanup report to disk
        
        Args:
            report: CleanupReport to save
            output_dir: Directory to save reports
            format: Output format ("json", "markdown", "both")
            
        Returns:
            Tuple of (json_path, markdown_path) or (None, None) if failed
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y-%m-%d")
        
        json_path = None
        markdown_path = None
        
        # Save JSON
        if format in ["json", "both"]:
            json_path = output_dir / f"cleanup-report-{timestamp}.json"
            import json
            
            # Convert to serializable format
            report_dict = {
                "timestamp": report.timestamp,
                "total_stale_files": report.total_stale_files,
                "stale_compose_files": [
                    {
                        "file_path": str(f.file_path),
                        "file_type": f.file_type,
                        "reason": f.reason,
                        "stack_name": f.stack_name,
                        "service_names": f.service_names
                    }
                    for f in report.stale_compose_files
                ],
                "stale_env_files": [
                    {
                        "file_path": str(f.file_path),
                        "file_type": f.file_type,
                        "reason": f.reason,
                        "stack_name": f.stack_name,
                        "service_names": f.service_names
                    }
                    for f in report.stale_env_files
                ],
                "stale_other_files": [
                    {
                        "file_path": str(f.file_path),
                        "file_type": f.file_type,
                        "reason": f.reason,
                        "stack_name": f.stack_name,
                        "service_names": f.service_names
                    }
                    for f in report.stale_other_files
                ],
                "running_services": list(report.running_services),
                "git_services": list(report.git_services)
            }
            
            with open(json_path, 'w') as f:
                json.dump(report_dict, f, indent=2)
        
        # Save Markdown
        if format in ["markdown", "both"]:
            markdown_path = output_dir / f"cleanup-report-{timestamp}.md"
            markdown_content = self.generate_cleanup_report_markdown(report)
            
            with open(markdown_path, 'w') as f:
                f.write(markdown_content)
        
        return (json_path, markdown_path)


def main():
    """CLI entry point for cleanup detector"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Detect stale configuration files in infrastructure repositories"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("reports"),
        help="Directory to save reports (default: reports/)"
    )
    parser.add_argument(
        "--format",
        choices=["json", "markdown", "both"],
        default="both",
        help="Output format (default: both)"
    )
    parser.add_argument(
        "--no-deployment-targets",
        action="store_true",
        help="Skip checking stack-targets.yml"
    )
    
    args = parser.parse_args()
    
    # Load config
    config = Config()
    
    # Run detection
    detector = CleanupDetector(config)
    
    print("🔍 Scanning for stale files...")
    report = detector.detect_stale_files(
        check_deployment_targets=not args.no_deployment_targets
    )
    
    # Save reports
    json_path, markdown_path = detector.save_cleanup_report(
        report, args.output_dir, format=args.format
    )
    
    # Print summary
    print("\n" + "=" * 60)
    print("CLEANUP DETECTION SUMMARY")
    print("=" * 60)
    print(f"Total stale files: {report.total_stale_files}")
    print(f"  - Compose files: {len(report.stale_compose_files)}")
    print(f"  - .env files: {len(report.stale_env_files)}")
    print(f"  - Other issues: {len(report.stale_other_files)}")
    print()
    
    if json_path:
        print(f"📄 JSON report: {json_path}")
    if markdown_path:
        print(f"📝 Markdown report: {markdown_path}")
    
    if report.total_stale_files > 0:
        print("\n⚠️  Stale files detected. Review reports before cleanup.")
    else:
        print("\n✅ No stale files detected. Repository is clean!")


if __name__ == "__main__":
    main()
