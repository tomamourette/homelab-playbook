"""Pull Request generation for drift remediation.

This module automates the creation of Pull Requests to sync git repositories
with running container configurations, enabling review-based drift remediation.
"""

import logging
import os
import subprocess
from typing import Dict, Any, Optional, List
from pathlib import Path
from datetime import datetime
import yaml

try:
    from github import Github, GithubException
    GITHUB_AVAILABLE = True
except ImportError:
    GITHUB_AVAILABLE = False
    logging.warning("PyGithub not installed - GitHub PR creation disabled")


# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


class PRGenerationError(Exception):
    """Raised when PR generation fails."""
    pass


class GitOperationError(Exception):
    """Raised when git operations fail."""
    pass


class PRGenerator:
    """Generate Pull Requests for drift remediation.
    
    This class handles the complete PR workflow:
    1. Create git branch for drift fix
    2. Update compose file with running configuration
    3. Commit changes with conventional commit message
    4. Push branch to remote
    5. Create Pull Request via GitHub API
    """
    
    # Patterns for sensitive data detection
    SENSITIVE_PATTERNS = [
        'password', 'passwd', 'pwd',
        'secret', 'token', 'key',
        'api_key', 'apikey',
        'auth', 'credential',
        'private', 'certificate'
    ]
    
    def __init__(
        self,
        github_token: Optional[str] = None,
        repo_owner: Optional[str] = None,
        repo_name: Optional[str] = None
    ):
        """Initialize PR generator.
        
        Args:
            github_token: GitHub personal access token
            repo_owner: GitHub repository owner/organization
            repo_name: GitHub repository name
        """
        self.github_token = github_token or os.getenv('GITHUB_TOKEN')
        self.repo_owner = repo_owner or os.getenv('GITHUB_REPO_OWNER')
        self.repo_name = repo_name or os.getenv('GITHUB_REPO_NAME')
        
        self.github_client = None
        if GITHUB_AVAILABLE and self.github_token:
            try:
                self.github_client = Github(self.github_token)
                logger.info(f"Initialized GitHub client for {self.repo_owner}/{self.repo_name}")
            except Exception as e:
                logger.warning(f"Failed to initialize GitHub client: {e}")
        
        logger.info("Initialized PRGenerator")
    
    def sanitize_value(self, key: str, value: Any) -> str:
        """Sanitize potentially sensitive values.
        
        Args:
            key: Field name/key
            value: Value to sanitize
        
        Returns:
            Original value or [REDACTED] if sensitive
        """
        key_lower = str(key).lower()
        if any(pattern in key_lower for pattern in self.SENSITIVE_PATTERNS):
            return "[REDACTED]"
        return str(value)
    
    def create_branch(
        self,
        repo_path: Path,
        branch_name: str,
        base_branch: str = "main"
    ) -> None:
        """Create a new git branch.
        
        Args:
            repo_path: Path to git repository
            branch_name: Name for the new branch
            base_branch: Base branch to branch from
        
        Raises:
            GitOperationError: If branch creation fails
        """
        try:
            # Ensure we're on base branch
            subprocess.run(
                ["git", "checkout", base_branch],
                cwd=repo_path,
                check=True,
                capture_output=True
            )
            
            # Pull latest changes
            subprocess.run(
                ["git", "pull"],
                cwd=repo_path,
                check=True,
                capture_output=True
            )
            
            # Create new branch
            subprocess.run(
                ["git", "checkout", "-b", branch_name],
                cwd=repo_path,
                check=True,
                capture_output=True
            )
            
            logger.info(f"Created branch: {branch_name}")
            
        except subprocess.CalledProcessError as e:
            raise GitOperationError(f"Failed to create branch {branch_name}: {e.stderr.decode()}")
    
    def update_compose_file(
        self,
        compose_path: Path,
        service_name: str,
        running_config: Dict[str, Any]
    ) -> None:
        """Update Docker Compose file with running configuration.
        
        Args:
            compose_path: Path to docker-compose.yml file
            service_name: Name of the service to update
            running_config: Running configuration from container
        
        Raises:
            PRGenerationError: If compose file update fails
        """
        try:
            # Load compose file
            with open(compose_path, 'r') as f:
                compose_data = yaml.safe_load(f)
            
            if 'services' not in compose_data:
                raise PRGenerationError(f"No services section in {compose_path}")
            
            if service_name not in compose_data['services']:
                raise PRGenerationError(f"Service {service_name} not found in compose file")
            
            # Update service configuration
            service_config = compose_data['services'][service_name]
            
            # Update key fields from running config
            if 'image' in running_config:
                service_config['image'] = running_config['image']
            
            if 'environment' in running_config and running_config['environment']:
                service_config['environment'] = running_config['environment']
            
            if 'ports' in running_config and running_config['ports']:
                service_config['ports'] = running_config['ports']
            
            if 'volumes' in running_config and running_config['volumes']:
                service_config['volumes'] = running_config['volumes']
            
            if 'networks' in running_config and running_config['networks']:
                service_config['networks'] = running_config['networks']
            
            if 'labels' in running_config and running_config['labels']:
                service_config['labels'] = running_config['labels']
            
            # Write updated compose file
            with open(compose_path, 'w') as f:
                yaml.dump(compose_data, f, default_flow_style=False, sort_keys=False)
            
            logger.info(f"Updated {compose_path} for service {service_name}")
            
        except Exception as e:
            raise PRGenerationError(f"Failed to update compose file: {e}")
    
    def commit_changes(
        self,
        repo_path: Path,
        service_name: str,
        message_suffix: str = "sync config with running state"
    ) -> None:
        """Commit changes with conventional commit message.
        
        Args:
            repo_path: Path to git repository
            service_name: Name of the service
            message_suffix: Commit message suffix
        
        Raises:
            GitOperationError: If commit fails
        """
        try:
            # Stage changes
            subprocess.run(
                ["git", "add", "-A"],
                cwd=repo_path,
                check=True,
                capture_output=True
            )
            
            # Create conventional commit message
            commit_message = f"fix({service_name}): {message_suffix}"
            
            # Commit
            subprocess.run(
                ["git", "commit", "-m", commit_message],
                cwd=repo_path,
                check=True,
                capture_output=True
            )
            
            logger.info(f"Committed changes: {commit_message}")
            
        except subprocess.CalledProcessError as e:
            raise GitOperationError(f"Failed to commit changes: {e.stderr.decode()}")
    
    def push_branch(
        self,
        repo_path: Path,
        branch_name: str
    ) -> None:
        """Push branch to remote.
        
        Args:
            repo_path: Path to git repository
            branch_name: Name of the branch to push
        
        Raises:
            GitOperationError: If push fails
        """
        try:
            subprocess.run(
                ["git", "push", "-u", "origin", branch_name],
                cwd=repo_path,
                check=True,
                capture_output=True
            )
            
            logger.info(f"Pushed branch: {branch_name}")
            
        except subprocess.CalledProcessError as e:
            raise GitOperationError(f"Failed to push branch: {e.stderr.decode()}")
    
    def create_pr_description(
        self,
        service_name: str,
        stack_name: str,
        drift_items: List[Dict[str, Any]],
        drift_report_path: Optional[str] = None
    ) -> str:
        """Create Pull Request description.
        
        Args:
            service_name: Name of the service
            stack_name: Name of the stack
            drift_items: List of drift items
            drift_report_path: Path to drift report file
        
        Returns:
            Formatted PR description
        """
        description_parts = []
        
        # Header
        description_parts.append(f"# Drift Remediation: {service_name}\n")
        description_parts.append(f"**Stack**: {stack_name}\n")
        description_parts.append(f"**Auto-generated**: {datetime.utcnow().isoformat()}\n\n")
        
        # Summary
        description_parts.append("## Summary\n\n")
        description_parts.append(
            f"This PR updates the git baseline configuration for `{service_name}` "
            f"to match the current running state, remediating {len(drift_items)} "
            f"configuration drift item(s).\n\n"
        )
        
        # Drift items
        description_parts.append("## Configuration Changes\n\n")
        
        for item in drift_items:
            field_path = item.get('field_path', 'unknown')
            baseline_value = item.get('baseline_value', 'N/A')
            running_value = item.get('running_value', 'N/A')
            severity = item.get('severity', 'unknown')
            
            # Sanitize potentially sensitive values
            baseline_sanitized = self.sanitize_value(field_path, baseline_value)
            running_sanitized = self.sanitize_value(field_path, running_value)
            
            description_parts.append(f"### {field_path}\n\n")
            description_parts.append(f"- **Severity**: {severity}\n")
            description_parts.append(f"- **Baseline**: `{baseline_sanitized}`\n")
            description_parts.append(f"- **Running**: `{running_sanitized}`\n\n")
        
        # Drift report link
        if drift_report_path:
            description_parts.append("## Drift Report\n\n")
            description_parts.append(f"See full drift analysis: `{drift_report_path}`\n\n")
        
        # Review checklist
        description_parts.append("## Review Checklist\n\n")
        description_parts.append("- [ ] Running configuration is correct and intentional\n")
        description_parts.append("- [ ] Changes align with deployment standards\n")
        description_parts.append("- [ ] No sensitive data exposed in configuration\n")
        description_parts.append("- [ ] Documentation updated if needed\n\n")
        
        # Labels
        description_parts.append("---\n")
        description_parts.append("*Auto-generated by drift detection tool*\n")
        description_parts.append("**Labels**: `drift-remediation`, `automated`\n")
        
        return ''.join(description_parts)
    
    def create_github_pr(
        self,
        branch_name: str,
        pr_title: str,
        pr_description: str,
        base_branch: str = "main"
    ) -> Optional[str]:
        """Create Pull Request via GitHub API.
        
        Args:
            branch_name: Source branch name
            pr_title: PR title
            pr_description: PR description/body
            base_branch: Target base branch
        
        Returns:
            PR URL if successful, None otherwise
        
        Raises:
            PRGenerationError: If PR creation fails
        """
        if not GITHUB_AVAILABLE:
            raise PRGenerationError("PyGithub not installed - cannot create PR")
        
        if not self.github_client:
            raise PRGenerationError("GitHub client not initialized - check token")
        
        try:
            # Get repository
            repo = self.github_client.get_repo(f"{self.repo_owner}/{self.repo_name}")
            
            # Create PR
            pr = repo.create_pull(
                title=pr_title,
                body=pr_description,
                head=branch_name,
                base=base_branch
            )
            
            # Add labels
            try:
                pr.add_to_labels("drift-remediation")
                pr.add_to_labels("automated")
            except GithubException as e:
                logger.warning(f"Failed to add labels to PR: {e}")
            
            logger.info(f"Created PR: {pr.html_url}")
            return pr.html_url
            
        except GithubException as e:
            raise PRGenerationError(f"Failed to create PR: {e}")
    
    def generate_pr_for_service(
        self,
        repo_path: Path,
        service_name: str,
        stack_name: str,
        running_config: Dict[str, Any],
        drift_items: List[Dict[str, Any]],
        drift_report_path: Optional[str] = None,
        base_branch: str = "main"
    ) -> Optional[str]:
        """Complete PR generation workflow for a service.
        
        Args:
            repo_path: Path to target repository
            service_name: Name of the service
            stack_name: Name of the stack
            running_config: Running configuration
            drift_items: List of drift items
            drift_report_path: Path to drift report
            base_branch: Base branch to target
        
        Returns:
            PR URL if successful, None otherwise
        """
        timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
        branch_name = f"fix/drift-{service_name}-{timestamp}"
        
        try:
            # Step 1: Create branch
            logger.info(f"Creating branch {branch_name}...")
            self.create_branch(repo_path, branch_name, base_branch)
            
            # Step 2: Update compose file
            compose_path = repo_path / "stacks" / stack_name / "docker-compose.yml"
            if not compose_path.exists():
                # Try alternate path
                compose_path = repo_path / stack_name / "docker-compose.yml"
            
            if not compose_path.exists():
                raise PRGenerationError(f"Compose file not found for {stack_name}")
            
            logger.info(f"Updating compose file {compose_path}...")
            self.update_compose_file(compose_path, service_name, running_config)
            
            # Step 3: Commit changes
            logger.info("Committing changes...")
            self.commit_changes(repo_path, service_name)
            
            # Step 4: Push branch
            logger.info("Pushing branch...")
            self.push_branch(repo_path, branch_name)
            
            # Step 5: Create PR
            logger.info("Creating Pull Request...")
            pr_title = f"fix({service_name}): sync config with running state"
            pr_description = self.create_pr_description(
                service_name,
                stack_name,
                drift_items,
                drift_report_path
            )
            
            pr_url = self.create_github_pr(branch_name, pr_title, pr_description, base_branch)
            
            logger.info(f"✅ PR generated successfully: {pr_url}")
            return pr_url
            
        except Exception as e:
            logger.error(f"Failed to generate PR for {service_name}: {e}")
            raise PRGenerationError(f"PR generation failed: {e}")


def generate_pr(
    service_drift: Dict[str, Any],
    repo_path: Path,
    github_token: Optional[str] = None,
    repo_owner: Optional[str] = None,
    repo_name: Optional[str] = None
) -> Optional[str]:
    """Convenience function to generate PR for a service drift.
    
    Args:
        service_drift: ServiceDrift dictionary
        repo_path: Path to target repository
        github_token: GitHub API token
        repo_owner: Repository owner
        repo_name: Repository name
    
    Returns:
        PR URL if successful, None otherwise
    """
    generator = PRGenerator(github_token, repo_owner, repo_name)
    
    service_name = service_drift['service_name']
    stack_name = service_drift['stack_name']
    drift_items = service_drift['drift_items']
    
    # Convert drift items to running config
    running_config = {}
    for item in drift_items:
        # Simplified - in production would reconstruct full config
        running_config[item['field_path']] = item['running_value']
    
    return generator.generate_pr_for_service(
        repo_path=repo_path,
        service_name=service_name,
        stack_name=stack_name,
        running_config=running_config,
        drift_items=drift_items
    )
