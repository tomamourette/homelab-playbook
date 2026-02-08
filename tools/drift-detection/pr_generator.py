#!/usr/bin/env python3
"""
PR Generator for Drift Remediation

Automatically generates Pull Requests to backport running configurations
to git repositories when drift is detected.

Handles:
- Branch creation
- Compose file updates
- Conventional commits
- PR creation via GitHub API
"""

import os
import json
import subprocess
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime
import requests
from dataclasses import dataclass


@dataclass
class DriftItem:
    """Represents a single configuration drift item"""
    service_name: str
    stack_name: str
    field_path: str
    running_value: any
    git_value: any
    severity: str
    
    
@dataclass
class PRMetadata:
    """Metadata for a Pull Request"""
    branch_name: str
    title: str
    body: str
    labels: List[str]
    base_branch: str = "main"


class GitOperationError(Exception):
    """Raised when git operations fail"""
    pass


class PRGenerationError(Exception):
    """Raised when PR creation fails"""
    pass


class PRGenerator:
    """Generates Pull Requests for drift remediation"""
    
    def __init__(
        self,
        repo_path: Path,
        github_token: Optional[str] = None,
        github_repo: Optional[str] = None,
        dry_run: bool = False
    ):
        """
        Initialize PR Generator
        
        Args:
            repo_path: Path to local git repository
            github_token: GitHub API token (optional, from env if not provided)
            github_repo: GitHub repository (e.g., "user/repo")
            dry_run: If True, don't actually create PRs or push branches
        """
        self.repo_path = Path(repo_path)
        self.dry_run = dry_run
        
        # GitHub configuration
        self.github_token = github_token or os.getenv("GITHUB_TOKEN")
        self.github_repo = github_repo or os.getenv("GITHUB_REPO")
        
        if not self.repo_path.exists():
            raise ValueError(f"Repository path does not exist: {repo_path}")
            
        # Validate we're in a git repo
        if not (self.repo_path / ".git").exists():
            raise ValueError(f"Not a git repository: {repo_path}")
    
    def generate_pr_for_service(
        self,
        service_name: str,
        stack_name: str,
        drift_items: List[DriftItem],
        compose_file_path: Path
    ) -> Optional[str]:
        """
        Generate a PR to remediate drift for a single service
        
        Args:
            service_name: Name of the service (e.g., "pihole")
            stack_name: Name of the stack (e.g., "dns-pihole")
            drift_items: List of drift items for this service
            compose_file_path: Path to the compose file to update (relative to repo root)
            
        Returns:
            PR URL if created, None if dry-run or error
        """
        if not drift_items:
            print(f"No drift items for {service_name}, skipping PR generation")
            return None
        
        # Generate branch name
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        branch_name = f"fix/drift-{stack_name}-{timestamp}"
        
        # Create branch
        try:
            self._create_branch(branch_name)
        except GitOperationError as e:
            print(f"Failed to create branch: {e}")
            return None
        
        # Update compose file
        try:
            self._update_compose_file(compose_file_path, service_name, drift_items)
        except Exception as e:
            print(f"Failed to update compose file: {e}")
            self._cleanup_branch(branch_name)
            return None
        
        # Commit changes
        commit_msg = self._generate_commit_message(service_name, stack_name, drift_items)
        try:
            self._commit_changes(compose_file_path, commit_msg)
        except GitOperationError as e:
            print(f"Failed to commit changes: {e}")
            self._cleanup_branch(branch_name)
            return None
        
        # Push branch
        if not self.dry_run:
            try:
                self._push_branch(branch_name)
            except GitOperationError as e:
                print(f"Failed to push branch: {e}")
                self._cleanup_branch(branch_name)
                return None
        
        # Create PR
        pr_metadata = self._generate_pr_metadata(
            branch_name, service_name, stack_name, drift_items, compose_file_path
        )
        
        if not self.dry_run:
            try:
                pr_url = self._create_github_pr(pr_metadata)
                print(f"✅ Created PR for {service_name}: {pr_url}")
                return pr_url
            except PRGenerationError as e:
                print(f"Failed to create PR: {e}")
                return None
        else:
            print(f"[DRY RUN] Would create PR: {pr_metadata.title}")
            print(f"[DRY RUN] Branch: {branch_name}")
            print(f"[DRY RUN] Commit: {commit_msg}")
            return None
    
    def _validate_branch_name(self, branch_name: str) -> None:
        """Validate branch name to prevent injection attacks"""
        # Git branch names must not contain: .., ~, ^, :, ?, *, [, \, space at start/end
        # Keep it simple: allow alphanumeric, -, /, _
        if not re.match(r'^[a-zA-Z0-9/_-]+$', branch_name):
            raise ValueError(
                f"Invalid branch name: {branch_name}. "
                "Branch names must contain only alphanumeric characters, -, /, and _"
            )
    
    def _create_branch(self, branch_name: str) -> None:
        """Create a new git branch"""
        # Validate branch name to prevent injection
        self._validate_branch_name(branch_name)
        
        result = subprocess.run(
            ["git", "checkout", "-b", branch_name],
            cwd=self.repo_path,
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            raise GitOperationError(f"Failed to create branch: {result.stderr}")
    
    def _cleanup_branch(self, branch_name: str) -> None:
        """Clean up a branch after failed PR generation"""
        # Switch back to main
        subprocess.run(
            ["git", "checkout", "main"],
            cwd=self.repo_path,
            capture_output=True
        )
        
        # Delete the branch
        subprocess.run(
            ["git", "branch", "-D", branch_name],
            cwd=self.repo_path,
            capture_output=True
        )
    
    def _update_compose_file(
        self,
        compose_file_path: Path,
        service_name: str,
        drift_items: List[DriftItem]
    ) -> None:
        """
        Update Docker Compose file with running configuration values
        
        This is a simplified implementation that updates specific fields.
        A full implementation would parse YAML, update values, and write back.
        """
        import yaml
        
        full_path = self.repo_path / compose_file_path
        
        # Read current compose file
        try:
            with open(full_path, 'r') as f:
                compose_data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ValueError(f"Failed to parse {compose_file_path}: {e}")
        except FileNotFoundError:
            raise ValueError(f"Compose file not found: {compose_file_path}")
        
        if 'services' not in compose_data or service_name not in compose_data['services']:
            raise ValueError(f"Service {service_name} not found in {compose_file_path}")
        
        service_config = compose_data['services'][service_name]
        
        # Apply drift fixes
        for drift in drift_items:
            self._apply_drift_fix(service_config, drift)
        
        # Write back to file
        with open(full_path, 'w') as f:
            yaml.dump(compose_data, f, default_flow_style=False, sort_keys=False)
    
    def _apply_drift_fix(self, service_config: Dict[str, Any], drift: DriftItem) -> None:
        """Apply a single drift fix to service configuration"""
        path_parts = drift.field_path.split('.')
        current = service_config
        
        # If the drift is at the root level of the service (e.g. 'image', 'volumes', 'networks')
        if len(path_parts) == 1:
            service_config[path_parts[0]] = drift.running_value
            return

        # Navigate to parent
        for part in path_parts[:-1]:
            if not isinstance(current, dict) or part not in current:
                # If path doesn't exist or is blocked by non-dict, abort fix for this item
                return
            current = current[part]
        
        # Set final key if parent is a dict
        final_key = path_parts[-1]
        if isinstance(current, dict):
            current[final_key] = drift.running_value
    
    def _generate_commit_message(
        self,
        service_name: str,
        stack_name: str,
        drift_items: List[DriftItem]
    ) -> str:
        """Generate conventional commit message"""
        # Count drift by severity
        severity_counts = {}
        for item in drift_items:
            severity_counts[item.severity] = severity_counts.get(item.severity, 0) + 1
        
        # Determine commit type based on most severe drift
        if "BREAKING" in severity_counts:
            commit_type = "fix"  # Breaking config drift is a fix
        elif "FUNCTIONAL" in severity_counts:
            commit_type = "fix"
        else:
            commit_type = "chore"  # Cosmetic/informational
        
        # Generate summary
        drift_count = len(drift_items)
        scope = stack_name
        
        subject = f"sync {service_name} config with running state"
        
        # Body with details
        body_lines = [
            "",
            f"Detected {drift_count} configuration drift(s) in {service_name}:",
            ""
        ]
        
        for item in drift_items:
            body_lines.append(f"- {item.field_path}: {item.severity}")
            body_lines.append(f"  Git: {item.git_value}")
            body_lines.append(f"  Running: {item.running_value}")
        
        body_lines.extend([
            "",
            "This PR backports the running configuration to git to eliminate drift.",
            ""
        ])
        
        commit_msg = f"{commit_type}({scope}): {subject}\n" + "\n".join(body_lines)
        return commit_msg
    
    def _commit_changes(self, compose_file_path: Path, commit_msg: str) -> None:
        """Commit changes to git"""
        # Add file
        result = subprocess.run(
            ["git", "add", str(compose_file_path)],
            cwd=self.repo_path,
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            raise GitOperationError(f"Failed to add file: {result.stderr}")
        
        # Commit
        result = subprocess.run(
            ["git", "commit", "-m", commit_msg],
            cwd=self.repo_path,
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            raise GitOperationError(f"Failed to commit: {result.stderr}")
    
    def _push_branch(self, branch_name: str) -> None:
        """Push branch to remote"""
        result = subprocess.run(
            ["git", "push", "-u", "origin", branch_name],
            cwd=self.repo_path,
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            raise GitOperationError(f"Failed to push branch: {result.stderr}")
    
    def _generate_pr_metadata(
        self,
        branch_name: str,
        service_name: str,
        stack_name: str,
        drift_items: List[DriftItem],
        compose_file_path: Path
    ) -> PRMetadata:
        """Generate PR metadata (title, body, labels)"""
        title = f"fix({stack_name}): Sync {service_name} config with running state"
        
        # Build PR body
        body_lines = [
            "## Drift Remediation",
            "",
            f"This PR backports the running configuration of `{service_name}` to git.",
            "",
            f"**Stack:** `{stack_name}`",
            f"**File:** `{compose_file_path}`",
            f"**Drift Items:** {len(drift_items)}",
            "",
            "### Changes",
            ""
        ]
        
        # Group by severity
        by_severity = {}
        for item in drift_items:
            by_severity.setdefault(item.severity, []).append(item)
        
        for severity in ["BREAKING", "FUNCTIONAL", "COSMETIC", "INFORMATIONAL"]:
            if severity in by_severity:
                items = by_severity[severity]
                emoji = {
                    "BREAKING": "🔴",
                    "FUNCTIONAL": "🟡",
                    "COSMETIC": "🔵",
                    "INFORMATIONAL": "⚪"
                }.get(severity, "")
                
                body_lines.append(f"#### {emoji} {severity} ({len(items)} items)")
                body_lines.append("")
                
                for item in items:
                    body_lines.append(f"**{item.field_path}**")
                    body_lines.append(f"- Git: `{item.git_value}`")
                    body_lines.append(f"- Running: `{item.running_value}`")
                    body_lines.append("")
        
        body_lines.extend([
            "### Review Notes",
            "",
            "- This PR was automatically generated by drift detection tool",
            "- Changes reflect the **current running state** of the service",
            "- Review carefully to ensure running config is correct",
            "- Once approved, git will match deployed infrastructure",
            ""
        ])
        
        body = "\n".join(body_lines)
        
        return PRMetadata(
            branch_name=branch_name,
            title=title,
            body=body,
            labels=["drift-remediation", "automated"],
            base_branch="main"
        )
    
    def _create_github_pr(self, metadata: PRMetadata) -> str:
        """Create PR via GitHub API"""
        if not self.github_token or not self.github_repo:
            raise PRGenerationError(
                "GitHub token and repo required. Set GITHUB_TOKEN and GITHUB_REPO environment variables."
            )
        
        api_url = f"https://api.github.com/repos/{self.github_repo}/pulls"
        
        headers = {
            "Authorization": f"token {self.github_token}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        data = {
            "title": metadata.title,
            "body": metadata.body,
            "head": metadata.branch_name,
            "base": metadata.base_branch
        }
        
        response = requests.post(api_url, headers=headers, json=data)
        
        if response.status_code != 201:
            raise PRGenerationError(
                f"GitHub API returned {response.status_code}: {response.text}"
            )
        
        pr_data = response.json()
        pr_url = pr_data["html_url"]
        pr_number = pr_data["number"]
        
        # Add labels
        if metadata.labels:
            self._add_labels_to_pr(pr_number, metadata.labels)
        
        return pr_url
    
    def _add_labels_to_pr(self, pr_number: int, labels: List[str]) -> None:
        """Add labels to a PR"""
        if not self.github_token or not self.github_repo:
            return
        
        api_url = f"https://api.github.com/repos/{self.github_repo}/issues/{pr_number}/labels"
        
        headers = {
            "Authorization": f"token {self.github_token}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        data = {"labels": labels}
        
        response = requests.post(api_url, headers=headers, json=data)
        
        if response.status_code != 200:
            print(f"Warning: Failed to add labels: {response.text}")


def generate_prs_from_drift_report(
    drift_report_path: Path,
    repo_path: Path,
    dry_run: bool = False
) -> Dict[str, Optional[str]]:
    """
    Generate PRs for all drifted services in a drift report
    """
    with open(drift_report_path, 'r') as f:
        drift_data = json.load(f)
    
    generator = PRGenerator(repo_path=repo_path, dry_run=dry_run)
    pr_results = {}
    
    for service_drift in drift_data.get("service_drifts", []):
        if not service_drift.get("has_drift") or service_drift.get("baseline_missing"):
            continue
            
        service_name = service_drift["service_name"]
        stack_name = service_drift.get("stack_name", "unknown")
        
        # Determine compose path relative to repo root
        full_path = service_drift.get("compose_file")
        if not full_path:
            # Dynamic lookup for missing paths
            potential_path = repo_path / "stacks" / stack_name / "docker-compose.yml"
            if potential_path.exists():
                full_path = str(potential_path)
            else:
                continue
        
        try:
            compose_file = Path(full_path).relative_to(repo_path)
        except ValueError:
            # Fallback if path is already relative or elsewhere
            compose_file = Path(full_path)
        
        # Convert drift items to DriftItem objects
        drift_items = [
            DriftItem(
                service_name=service_name,
                stack_name=stack_name,
                field_path=item["field_path"],
                running_value=item["running_value"],
                git_value=item["baseline_value"],
                severity=item["severity"]
            )
            for item in service_drift.get("drift_items", [])
        ]
        
        if not drift_items: continue

        pr_url = generator.generate_pr_for_service(
            service_name=service_name,
            stack_name=stack_name,
            drift_items=drift_items,
            compose_file_path=compose_file
        )
        
        pr_results[service_name] = pr_url
    
    return pr_results


if __name__ == "__main__":
    # Example usage
    import sys
    
    if len(sys.argv) < 3:
        print("Usage: pr_generator.py <drift_report.json> <repo_path> [--dry-run]")
        sys.exit(1)
    
    drift_report = Path(sys.argv[1])
    repo_path = Path(sys.argv[2])
    dry_run = "--dry-run" in sys.argv
    
    results = generate_prs_from_drift_report(drift_report, repo_path, dry_run=dry_run)
    
    print("\n=== PR Generation Results ===")
    for service, pr_url in results.items():
        if pr_url:
            print(f"✅ {service}: {pr_url}")
        else:
            print(f"❌ {service}: Failed or skipped")
