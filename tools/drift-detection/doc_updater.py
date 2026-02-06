#!/usr/bin/env python3
"""
Documentation Update Automation

Automatically updates README files and deployment documentation when
configurations change. Keeps documentation synchronized with infrastructure state.

Features:
- Update service lists in repository READMEs
- Refresh deployment target mappings
- Update "Last Audit" timestamps
- Generate service inventory tables
- Commit documentation updates to PRs
"""

import yaml
from pathlib import Path
from typing import Dict, List, Optional, Set
from dataclasses import dataclass
from datetime import datetime
import re


@dataclass
class ServiceInfo:
    """Information about a service"""
    name: str
    stack: str
    image: str
    description: Optional[str]
    endpoints: List[str]  # Traefik endpoints if configured


class DocUpdater:
    """Updates documentation files based on current infrastructure state"""
    
    def __init__(self, repo_path: Path):
        """
        Initialize Documentation Updater
        
        Args:
            repo_path: Path to repository
        """
        self.repo_path = Path(repo_path)
    
    def update_all(self) -> List[Path]:
        """
        Update all documentation files
        
        Returns:
            List of files that were updated
        """
        updated_files = []
        
        # Update main README
        readme_path = self.repo_path / "README.md"
        if readme_path.exists():
            if self._update_main_readme(readme_path):
                updated_files.append(readme_path)
        
        # Update stack-targets.yml
        targets_path = self.repo_path / "stack-targets.yml"
        if targets_path.exists():
            if self._update_stack_targets(targets_path):
                updated_files.append(targets_path)
        
        return updated_files
    
    def get_all_services(self) -> List[ServiceInfo]:
        """
        Extract all services from compose files
        
        Returns:
            List of ServiceInfo for all services
        """
        services = []
        
        stacks_dir = self.repo_path / "stacks"
        if not stacks_dir.exists():
            return services
        
        for stack_dir in stacks_dir.iterdir():
            if not stack_dir.is_dir():
                continue
            
            stack_name = stack_dir.name
            
            # Load main compose file
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
            
            # Extract service info
            for service_name, service_config in compose_data['services'].items():
                image = service_config.get('image', '')
                
                # Extract endpoints from Traefik labels
                endpoints = self._extract_endpoints(service_config.get('labels', {}))
                
                # Try to get description from comments or labels
                description = service_config.get('labels', {}).get('description', None)
                
                services.append(ServiceInfo(
                    name=service_name,
                    stack=stack_name,
                    image=image,
                    description=description,
                    endpoints=endpoints
                ))
        
        return services
    
    def _extract_endpoints(self, labels: dict) -> List[str]:
        """Extract Traefik endpoints from labels"""
        endpoints = []
        
        if not isinstance(labels, dict):
            return endpoints
        
        # Look for Traefik router rules
        for key, value in labels.items():
            if 'traefik.http.routers' in key and key.endswith('.rule'):
                # Extract hostname from rule
                # Rule format: Host(`example.com`) or Host(`example.com`,`www.example.com`)
                hosts = re.findall(r'Host\(`([^`]+)`\)', str(value))
                endpoints.extend(hosts)
        
        return endpoints
    
    def _update_main_readme(self, readme_path: Path) -> bool:
        """
        Update main README.md with current service list
        
        Args:
            readme_path: Path to README.md
            
        Returns:
            True if file was modified
        """
        content = readme_path.read_text()
        original_content = content
        
        # Get current services
        services = self.get_all_services()
        
        # Generate service table
        service_table = self._generate_service_table(services)
        
        # Find and replace service list section
        # Look for markers: <!-- BEGIN SERVICE LIST --> and <!-- END SERVICE LIST -->
        begin_marker = "<!-- BEGIN SERVICE LIST -->"
        end_marker = "<!-- END SERVICE LIST -->"
        
        if begin_marker in content and end_marker in content:
            # Replace content between markers
            before = content.split(begin_marker)[0]
            after = content.split(end_marker)[1]
            
            new_content = (
                before +
                begin_marker + "\n" +
                service_table + "\n" +
                end_marker +
                after
            )
            
            content = new_content
        else:
            # Markers not found, append at end
            content += "\n\n" + begin_marker + "\n" + service_table + "\n" + end_marker + "\n"
        
        # Update "Last Audit" timestamp
        content = self._update_timestamp(content, "Last Audit")
        
        # Write back if changed
        if content != original_content:
            readme_path.write_text(content)
            return True
        
        return False
    
    def _generate_service_table(self, services: List[ServiceInfo]) -> str:
        """Generate Markdown table of services"""
        lines = [
            "## Deployed Services",
            "",
            "| Stack | Service | Image | Endpoints |",
            "|-------|---------|-------|-----------|"
        ]
        
        # Group by stack
        by_stack = {}
        for svc in services:
            by_stack.setdefault(svc.stack, []).append(svc)
        
        # Sort stacks alphabetically
        for stack in sorted(by_stack.keys()):
            for svc in by_stack[stack]:
                endpoints = ", ".join(svc.endpoints) if svc.endpoints else "-"
                lines.append(f"| {svc.stack} | {svc.name} | `{svc.image}` | {endpoints} |")
        
        lines.append("")
        lines.append(f"**Total Services:** {len(services)}")
        lines.append(f"**Last Updated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        return "\n".join(lines)
    
    def _update_stack_targets(self, targets_path: Path) -> bool:
        """
        Update stack-targets.yml with current deployments
        
        Args:
            targets_path: Path to stack-targets.yml
            
        Returns:
            True if file was modified
        """
        try:
            with open(targets_path, 'r') as f:
                targets_data = yaml.safe_load(f) or {}
        except Exception:
            return False
        
        original_data = targets_data.copy()
        
        # Get all stacks
        stacks_dir = self.repo_path / "stacks"
        if not stacks_dir.exists():
            return False
        
        current_stacks = {d.name for d in stacks_dir.iterdir() if d.is_dir()}
        
        # Remove stacks that no longer exist
        stacks_to_remove = [s for s in targets_data.keys() if s not in current_stacks]
        for stack in stacks_to_remove:
            del targets_data[stack]
        
        # Add new stacks (with default values)
        for stack in current_stacks:
            if stack not in targets_data:
                targets_data[stack] = {
                    "target": "ct-docker-01",  # Default target
                    "enabled": True
                }
        
        # Write back if changed
        if targets_data != original_data:
            with open(targets_path, 'w') as f:
                yaml.dump(
                    targets_data,
                    f,
                    default_flow_style=False,
                    sort_keys=True
                )
            return True
        
        return False
    
    def _update_timestamp(self, content: str, label: str) -> str:
        """
        Update timestamp in document
        
        Args:
            content: Document content
            label: Timestamp label (e.g., "Last Audit")
            
        Returns:
            Updated content
        """
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Pattern: **Last Audit:** 2024-01-01 12:00:00
        pattern = rf'\*\*{label}:\*\* \d{{4}}-\d{{2}}-\d{{2}} \d{{2}}:\d{{2}}:\d{{2}}'
        replacement = f"**{label}:** {timestamp}"
        
        # Try to replace existing
        new_content, count = re.subn(pattern, replacement, content)
        
        if count > 0:
            return new_content
        
        # Not found, try without formatting
        pattern = rf'{label}: \d{{4}}-\d{{2}}-\d{{2}} \d{{2}}:\d{{2}}:\d{{2}}'
        replacement = f"{label}: {timestamp}"
        
        new_content, count = re.subn(pattern, replacement, content)
        
        return new_content
    
    def generate_service_catalog(self, output_path: Path) -> None:
        """
        Generate comprehensive service catalog document
        
        Args:
            output_path: Path to write catalog
        """
        services = self.get_all_services()
        
        lines = [
            "# Service Catalog",
            "",
            f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"**Total Services:** {len(services)}",
            "",
            "## Services by Stack",
            ""
        ]
        
        # Group by stack
        by_stack = {}
        for svc in services:
            by_stack.setdefault(svc.stack, []).append(svc)
        
        # Generate sections for each stack
        for stack in sorted(by_stack.keys()):
            lines.append(f"### {stack}")
            lines.append("")
            
            for svc in by_stack[stack]:
                lines.append(f"#### {svc.name}")
                lines.append(f"- **Image:** `{svc.image}`")
                
                if svc.endpoints:
                    lines.append(f"- **Endpoints:**")
                    for endpoint in svc.endpoints:
                        lines.append(f"  - `{endpoint}`")
                
                if svc.description:
                    lines.append(f"- **Description:** {svc.description}")
                
                lines.append("")
        
        output_path.write_text("\n".join(lines))


def main():
    """CLI entry point"""
    import argparse
    import subprocess
    
    parser = argparse.ArgumentParser(
        description="Update documentation with current infrastructure state"
    )
    parser.add_argument(
        "repo_path",
        type=Path,
        help="Path to repository"
    )
    parser.add_argument(
        "--commit",
        action="store_true",
        help="Commit changes to git"
    )
    parser.add_argument(
        "--catalog",
        type=Path,
        help="Generate service catalog to specified path"
    )
    
    args = parser.parse_args()
    
    # Run updates
    updater = DocUpdater(args.repo_path)
    
    print("📝 Updating documentation...")
    updated_files = updater.update_all()
    
    if updated_files:
        print(f"\n✅ Updated {len(updated_files)} file(s):")
        for file_path in updated_files:
            print(f"  - {file_path.relative_to(args.repo_path)}")
    else:
        print("\n✅ Documentation is up to date (no changes needed)")
    
    # Generate catalog if requested
    if args.catalog:
        updater.generate_service_catalog(args.catalog)
        print(f"\n📚 Generated service catalog: {args.catalog}")
    
    # Commit if requested
    if args.commit and updated_files:
        print("\n📦 Committing changes...")
        
        # Add files
        for file_path in updated_files:
            subprocess.run(
                ["git", "add", str(file_path)],
                cwd=args.repo_path,
                check=True
            )
        
        # Commit
        commit_msg = "docs: update service list and deployment mappings\n\nAutomatically updated by doc_updater.py"
        subprocess.run(
            ["git", "commit", "-m", commit_msg],
            cwd=args.repo_path,
            check=True
        )
        
        print("✅ Changes committed")


if __name__ == "__main__":
    main()
