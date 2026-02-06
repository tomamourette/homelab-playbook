"""Unit tests for pr_generator.py module."""

import pytest
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
import tempfile

from pr_generator import (
    PRGenerator,
    PRGenerationError,
    GitOperationError,
    generate_pr
)


class TestPRGeneratorInit:
    """Test suite for PRGenerator initialization."""
    
    def test_init_with_parameters(self):
        """Test initialization with explicit parameters."""
        generator = PRGenerator(
            github_token="test_token",
            repo_owner="owner",
            repo_name="repo"
        )
        
        assert generator.github_token == "test_token"
        assert generator.repo_owner == "owner"
        assert generator.repo_name == "repo"
    
    @patch.dict('os.environ', {'GITHUB_TOKEN': 'env_token', 'GITHUB_REPO_OWNER': 'env_owner', 'GITHUB_REPO_NAME': 'env_repo'})
    def test_init_from_environment(self):
        """Test initialization from environment variables."""
        generator = PRGenerator()
        
        assert generator.github_token == "env_token"
        assert generator.repo_owner == "env_owner"
        assert generator.repo_name == "env_repo"


class TestSanitizeValue:
    """Test suite for sanitize_value method."""
    
    def test_sanitize_password_field(self):
        """Test that password fields are redacted."""
        generator = PRGenerator()
        result = generator.sanitize_value("DATABASE_PASSWORD", "secret123")
        assert result == "[REDACTED]"
    
    def test_sanitize_api_key_field(self):
        """Test that API key fields are redacted."""
        generator = PRGenerator()
        result = generator.sanitize_value("environment.API_KEY", "key_12345")
        assert result == "[REDACTED]"
    
    def test_sanitize_token_field(self):
        """Test that token fields are redacted."""
        generator = PRGenerator()
        result = generator.sanitize_value("AUTH_TOKEN", "token_abc")
        assert result == "[REDACTED]"
    
    def test_sanitize_secret_field(self):
        """Test that secret fields are redacted."""
        generator = PRGenerator()
        result = generator.sanitize_value("SECRET_KEY", "my_secret")
        assert result == "[REDACTED]"
    
    def test_non_sensitive_field_not_redacted(self):
        """Test that non-sensitive fields are not redacted."""
        generator = PRGenerator()
        result = generator.sanitize_value("IMAGE", "nginx:latest")
        assert result == "nginx:latest"
    
    def test_case_insensitive_detection(self):
        """Test that sensitive pattern detection is case-insensitive."""
        generator = PRGenerator()
        result = generator.sanitize_value("Database_Password", "value")
        assert result == "[REDACTED]"


class TestCreatePRDescription:
    """Test suite for create_pr_description method."""
    
    def test_pr_description_structure(self):
        """Test PR description contains all required sections."""
        generator = PRGenerator()
        
        drift_items = [{
            'field_path': 'image',
            'baseline_value': 'nginx:1.0',
            'running_value': 'nginx:2.0',
            'severity': 'breaking'
        }]
        
        result = generator.create_pr_description(
            service_name="test-service",
            stack_name="test-stack",
            drift_items=drift_items
        )
        
        assert "# Drift Remediation: test-service" in result
        assert "**Stack**: test-stack" in result
        assert "## Summary" in result
        assert "## Configuration Changes" in result
        assert "## Review Checklist" in result
    
    def test_pr_description_sanitizes_sensitive_values(self):
        """Test that PR description sanitizes sensitive data."""
        generator = PRGenerator()
        
        drift_items = [{
            'field_path': 'environment.API_KEY',
            'baseline_value': 'old_key_123',
            'running_value': 'new_key_456',
            'severity': 'breaking'
        }]
        
        result = generator.create_pr_description(
            service_name="test",
            stack_name="test",
            drift_items=drift_items
        )
        
        assert "[REDACTED]" in result
        assert "old_key_123" not in result
        assert "new_key_456" not in result
    
    def test_pr_description_with_drift_report_link(self):
        """Test PR description includes drift report link."""
        generator = PRGenerator()
        
        result = generator.create_pr_description(
            service_name="test",
            stack_name="test",
            drift_items=[],
            drift_report_path="reports/drift-2026.md"
        )
        
        assert "## Drift Report" in result
        assert "reports/drift-2026.md" in result
    
    def test_pr_description_multiple_drift_items(self):
        """Test PR description with multiple drift items."""
        generator = PRGenerator()
        
        drift_items = [
            {
                'field_path': 'image',
                'baseline_value': 'nginx:1.0',
                'running_value': 'nginx:2.0',
                'severity': 'breaking'
            },
            {
                'field_path': 'labels.version',
                'baseline_value': '1.0',
                'running_value': '2.0',
                'severity': 'cosmetic'
            }
        ]
        
        result = generator.create_pr_description(
            service_name="test",
            stack_name="test",
            drift_items=drift_items
        )
        
        assert "### image" in result
        assert "### labels.version" in result
        assert "2 configuration drift item(s)" in result


class TestGitOperations:
    """Test suite for git operation methods."""
    
    @patch('pr_generator.subprocess.run')
    def test_create_branch_success(self, mock_run):
        """Test successful branch creation."""
        generator = PRGenerator()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)
            
            generator.create_branch(repo_path, "test-branch", "main")
            
            assert mock_run.call_count == 3  # checkout, pull, checkout -b
    
    @patch('pr_generator.subprocess.run')
    def test_create_branch_failure(self, mock_run):
        """Test branch creation failure handling."""
        mock_run.side_effect = subprocess.CalledProcessError(1, 'git', stderr=b'error')
        
        generator = PRGenerator()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)
            
            with pytest.raises(GitOperationError):
                generator.create_branch(repo_path, "test-branch")
    
    @patch('pr_generator.subprocess.run')
    def test_commit_changes_conventional_format(self, mock_run):
        """Test commit uses conventional commit format."""
        generator = PRGenerator()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)
            
            generator.commit_changes(repo_path, "my-service")
            
            # Check commit message format
            commit_call = [call for call in mock_run.call_args_list if 'commit' in str(call)]
            assert len(commit_call) > 0
    
    @patch('pr_generator.subprocess.run')
    def test_push_branch(self, mock_run):
        """Test branch push."""
        generator = PRGenerator()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)
            
            generator.push_branch(repo_path, "test-branch")
            
            # Verify push command called
            assert mock_run.called


class TestUpdateComposeFile:
    """Test suite for update_compose_file method."""
    
    def test_update_compose_file_image(self):
        """Test updating image in compose file."""
        generator = PRGenerator()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            compose_path = Path(tmpdir) / "docker-compose.yml"
            
            # Create test compose file
            compose_data = {
                'services': {
                    'test-service': {
                        'image': 'nginx:1.0'
                    }
                }
            }
            
            import yaml
            with open(compose_path, 'w') as f:
                yaml.dump(compose_data, f)
            
            # Update
            running_config = {'image': 'nginx:2.0'}
            generator.update_compose_file(compose_path, 'test-service', running_config)
            
            # Verify update
            with open(compose_path, 'r') as f:
                updated = yaml.safe_load(f)
            
            assert updated['services']['test-service']['image'] == 'nginx:2.0'
    
    def test_update_compose_file_service_not_found(self):
        """Test error when service not found in compose file."""
        generator = PRGenerator()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            compose_path = Path(tmpdir) / "docker-compose.yml"
            
            compose_data = {'services': {'other-service': {}}}
            
            import yaml
            with open(compose_path, 'w') as f:
                yaml.dump(compose_data, f)
            
            with pytest.raises(PRGenerationError, match="not found"):
                generator.update_compose_file(compose_path, 'test-service', {})


class TestGitHubIntegration:
    """Test suite for GitHub API methods."""
    
    def test_create_github_pr_without_client(self):
        """Test PR creation fails without GitHub client."""
        generator = PRGenerator()
        generator.github_client = None
        
        with pytest.raises(PRGenerationError):
            generator.create_github_pr("branch", "title", "description")


# Import subprocess for mocking
import subprocess
import yaml
