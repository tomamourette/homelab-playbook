#!/usr/bin/env python3
"""
Unit tests for PR Generator

Tests cover:
- Branch creation and cleanup
- Compose file updates
- Commit message generation
- PR metadata generation
- GitHub API integration (mocked)
"""

import pytest
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, call
import tempfile
import shutil
import yaml

from pr_generator import (
    PRGenerator,
    DriftItem,
    PRMetadata,
    GitOperationError,
    PRGenerationError,
    generate_prs_from_drift_report
)


@pytest.fixture
def temp_git_repo():
    """Create a temporary git repository for testing"""
    temp_dir = tempfile.mkdtemp()
    repo_path = Path(temp_dir)
    
    # Initialize git repo
    import subprocess
    subprocess.run(["git", "init"], cwd=repo_path, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo_path, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo_path, capture_output=True)
    
    # Create initial commit
    (repo_path / "README.md").write_text("# Test Repo\n")
    subprocess.run(["git", "add", "README.md"], cwd=repo_path, capture_output=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=repo_path, capture_output=True)
    
    yield repo_path
    
    # Cleanup
    shutil.rmtree(temp_dir)


@pytest.fixture
def sample_compose_file(temp_git_repo):
    """Create a sample Docker Compose file"""
    compose_path = temp_git_repo / "docker-compose.yml"
    compose_data = {
        "services": {
            "pihole": {
                "image": "pihole/pihole:2024.01.0",
                "labels": {
                    "traefik.enable": "true",
                    "traefik.http.routers.pihole.rule": "Host(`pihole.local`)"
                },
                "environment": {
                    "TZ": "UTC"
                }
            }
        }
    }
    
    with open(compose_path, 'w') as f:
        yaml.dump(compose_data, f)
    
    return Path("docker-compose.yml")


@pytest.fixture
def sample_drift_items():
    """Create sample drift items for testing"""
    return [
        DriftItem(
            service_name="pihole",
            stack_name="dns-pihole",
            field_path="labels.traefik.http.routers.pihole.rule",
            running_value="Host(`pihole.home.lan`)",
            git_value="Host(`pihole.local`)",
            severity="FUNCTIONAL"
        ),
        DriftItem(
            service_name="pihole",
            stack_name="dns-pihole",
            field_path="environment.TZ",
            running_value="Europe/Brussels",
            git_value="UTC",
            severity="COSMETIC"
        )
    ]


class TestPRGenerator:
    """Tests for PRGenerator class"""
    
    def test_init_valid_repo(self, temp_git_repo):
        """Test initialization with valid git repository"""
        generator = PRGenerator(repo_path=temp_git_repo, dry_run=True)
        
        assert generator.repo_path == temp_git_repo
        assert generator.dry_run is True
    
    def test_init_invalid_path(self):
        """Test initialization with non-existent path"""
        with pytest.raises(ValueError, match="does not exist"):
            PRGenerator(repo_path="/nonexistent/path")
    
    def test_init_not_git_repo(self, tmp_path):
        """Test initialization with non-git directory"""
        with pytest.raises(ValueError, match="Not a git repository"):
            PRGenerator(repo_path=tmp_path)
    
    def test_validate_branch_name_valid(self, temp_git_repo):
        """Test valid branch names pass validation"""
        generator = PRGenerator(repo_path=temp_git_repo, dry_run=True)
        
        valid_names = [
            "fix/drift-pihole-20260206",
            "feature/test-branch",
            "hotfix/urgent_fix",
            "fix/drift-dns-pihole-20260206-123456"
        ]
        
        for name in valid_names:
            generator._validate_branch_name(name)  # Should not raise
    
    def test_validate_branch_name_invalid(self, temp_git_repo):
        """Test invalid branch names fail validation"""
        generator = PRGenerator(repo_path=temp_git_repo, dry_run=True)
        
        invalid_names = [
            "branch with spaces",
            "branch..double-dot",
            "branch~tilde",
            "branch:colon",
            "branch?question",
            "branch*asterisk",
            "branch[bracket"
        ]
        
        for name in invalid_names:
            with pytest.raises(ValueError, match="Invalid branch name"):
                generator._validate_branch_name(name)
    
    def test_create_branch_success(self, temp_git_repo):
        """Test successful branch creation"""
        generator = PRGenerator(repo_path=temp_git_repo, dry_run=True)
        
        branch_name = "test-branch"
        generator._create_branch(branch_name)
        
        # Verify branch was created
        import subprocess
        result = subprocess.run(
            ["git", "branch", "--list", branch_name],
            cwd=temp_git_repo,
            capture_output=True,
            text=True
        )
        assert branch_name in result.stdout
    
    def test_cleanup_branch(self, temp_git_repo):
        """Test branch cleanup after failure"""
        generator = PRGenerator(repo_path=temp_git_repo, dry_run=True)
        
        # Create a branch
        branch_name = "test-cleanup"
        generator._create_branch(branch_name)
        
        # Clean it up
        generator._cleanup_branch(branch_name)
        
        # Verify branch was deleted
        import subprocess
        result = subprocess.run(
            ["git", "branch", "--list", branch_name],
            cwd=temp_git_repo,
            capture_output=True,
            text=True
        )
        assert branch_name not in result.stdout
    
    def test_update_compose_file_yaml_error(self, temp_git_repo):
        """Test handling of malformed YAML files"""
        generator = PRGenerator(repo_path=temp_git_repo, dry_run=True)
        
        # Create malformed YAML file
        bad_yaml = temp_git_repo / "bad.yml"
        bad_yaml.write_text("services:\n  test: {\n    invalid yaml")
        
        drift_items = [
            DriftItem(
                service_name="test",
                stack_name="test-stack",
                field_path="image",
                running_value="nginx:latest",
                git_value="nginx:1.0",
                severity="BREAKING"
            )
        ]
        
        with pytest.raises(ValueError, match="Failed to parse"):
            generator._update_compose_file(Path("bad.yml"), "test", drift_items)
    
    def test_update_compose_file_missing(self, temp_git_repo):
        """Test handling of missing compose file"""
        generator = PRGenerator(repo_path=temp_git_repo, dry_run=True)
        
        drift_items = []
        
        with pytest.raises(ValueError, match="not found"):
            generator._update_compose_file(Path("nonexistent.yml"), "test", drift_items)
    
    def test_apply_drift_fix_simple(self, temp_git_repo, sample_compose_file, sample_drift_items):
        """Test applying drift fix to compose file"""
        generator = PRGenerator(repo_path=temp_git_repo, dry_run=True)
        
        # Load compose data
        with open(temp_git_repo / sample_compose_file, 'r') as f:
            compose_data = yaml.safe_load(f)
        
        service_config = compose_data['services']['pihole']
        
        # Apply one drift fix
        drift = sample_drift_items[1]  # TZ change
        generator._apply_drift_fix(service_config, drift)
        
        # Verify fix was applied
        assert service_config['environment']['TZ'] == "Europe/Brussels"
    
    def test_apply_drift_fix_nested(self, temp_git_repo):
        """Test applying drift fix to nested fields"""
        generator = PRGenerator(repo_path=temp_git_repo, dry_run=True)
        
        service_config = {
            "labels": {
                "traefik.http.routers.test.rule": "Host(`old.local`)"
            }
        }
        
        drift = DriftItem(
            service_name="test",
            stack_name="test-stack",
            field_path="labels.traefik.http.routers.test.rule",
            running_value="Host(`new.local`)",
            git_value="Host(`old.local`)",
            severity="FUNCTIONAL"
        )
        
        generator._apply_drift_fix(service_config, drift)
        
        assert service_config['labels']['traefik.http.routers.test.rule'] == "Host(`new.local`)"
    
    def test_generate_commit_message_breaking(self, sample_drift_items):
        """Test commit message generation with breaking changes"""
        generator = PRGenerator(repo_path="/tmp", dry_run=True)  # Path not used in this test
        
        breaking_drift = DriftItem(
            service_name="pihole",
            stack_name="dns-pihole",
            field_path="image",
            running_value="pihole/pihole:2024.02.0",
            git_value="pihole/pihole:2024.01.0",
            severity="BREAKING"
        )
        
        msg = generator._generate_commit_message(
            "pihole",
            "dns-pihole",
            [breaking_drift]
        )
        
        assert msg.startswith("fix(dns-pihole):")
        assert "sync pihole config with running state" in msg
        assert "BREAKING" in msg
        assert "image" in msg
    
    def test_generate_commit_message_cosmetic(self, sample_drift_items):
        """Test commit message generation with cosmetic changes only"""
        generator = PRGenerator(repo_path="/tmp", dry_run=True)
        
        cosmetic_drift = [sample_drift_items[1]]  # TZ change (COSMETIC)
        
        msg = generator._generate_commit_message(
            "pihole",
            "dns-pihole",
            cosmetic_drift
        )
        
        assert msg.startswith("chore(dns-pihole):")
        assert "COSMETIC" in msg
    
    def test_generate_pr_metadata(self, sample_drift_items):
        """Test PR metadata generation"""
        generator = PRGenerator(repo_path="/tmp", dry_run=True)
        
        metadata = generator._generate_pr_metadata(
            branch_name="fix/drift-pihole-123",
            service_name="pihole",
            stack_name="dns-pihole",
            drift_items=sample_drift_items,
            compose_file_path=Path("stacks/dns-pihole/docker-compose.yml")
        )
        
        assert metadata.branch_name == "fix/drift-pihole-123"
        assert "pihole" in metadata.title
        assert "dns-pihole" in metadata.title
        assert "FUNCTIONAL" in metadata.body
        assert "COSMETIC" in metadata.body
        assert "drift-remediation" in metadata.labels
        assert "automated" in metadata.labels
    
    def test_generate_pr_metadata_severity_grouping(self, sample_drift_items):
        """Test PR metadata groups drift by severity"""
        generator = PRGenerator(repo_path="/tmp", dry_run=True)
        
        # Add multiple severities
        all_severities = sample_drift_items + [
            DriftItem(
                service_name="pihole",
                stack_name="dns-pihole",
                field_path="image",
                running_value="new:1.0",
                git_value="old:1.0",
                severity="BREAKING"
            ),
            DriftItem(
                service_name="pihole",
                stack_name="dns-pihole",
                field_path="healthcheck",
                running_value="test",
                git_value="",
                severity="INFORMATIONAL"
            )
        ]
        
        metadata = generator._generate_pr_metadata(
            branch_name="fix/test",
            service_name="pihole",
            stack_name="dns-pihole",
            drift_items=all_severities,
            compose_file_path=Path("test.yml")
        )
        
        # Check all severity sections present
        assert "🔴 BREAKING" in metadata.body
        assert "🟡 FUNCTIONAL" in metadata.body
        assert "🔵 COSMETIC" in metadata.body
        assert "⚪ INFORMATIONAL" in metadata.body
    
    @patch('pr_generator.requests.post')
    def test_create_github_pr_success(self, mock_post, temp_git_repo):
        """Test successful GitHub PR creation"""
        generator = PRGenerator(
            repo_path=temp_git_repo,
            github_token="test-token",
            github_repo="user/repo",
            dry_run=False
        )
        
        # Mock successful PR creation
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "html_url": "https://github.com/user/repo/pull/123",
            "number": 123
        }
        mock_post.return_value = mock_response
        
        metadata = PRMetadata(
            branch_name="test-branch",
            title="Test PR",
            body="Test body",
            labels=["test"]
        )
        
        pr_url = generator._create_github_pr(metadata)
        
        assert pr_url == "https://github.com/user/repo/pull/123"
        assert mock_post.called
    
    @patch('pr_generator.requests.post')
    def test_create_github_pr_failure(self, mock_post, temp_git_repo):
        """Test GitHub PR creation failure"""
        generator = PRGenerator(
            repo_path=temp_git_repo,
            github_token="test-token",
            github_repo="user/repo",
            dry_run=False
        )
        
        # Mock failed PR creation
        mock_response = Mock()
        mock_response.status_code = 422
        mock_response.text = "Validation failed"
        mock_post.return_value = mock_response
        
        metadata = PRMetadata(
            branch_name="test-branch",
            title="Test PR",
            body="Test body",
            labels=[]
        )
        
        with pytest.raises(PRGenerationError, match="422"):
            generator._create_github_pr(metadata)
    
    def test_create_github_pr_missing_token(self, temp_git_repo):
        """Test GitHub PR creation without token"""
        generator = PRGenerator(repo_path=temp_git_repo, dry_run=False)
        
        metadata = PRMetadata(
            branch_name="test-branch",
            title="Test PR",
            body="Test body",
            labels=[]
        )
        
        with pytest.raises(PRGenerationError, match="token and repo required"):
            generator._create_github_pr(metadata)
    
    @patch('pr_generator.requests.post')
    def test_add_labels_to_pr(self, mock_post, temp_git_repo):
        """Test adding labels to PR"""
        generator = PRGenerator(
            repo_path=temp_git_repo,
            github_token="test-token",
            github_repo="user/repo",
            dry_run=False
        )
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        generator._add_labels_to_pr(123, ["label1", "label2"])
        
        assert mock_post.called
        call_args = mock_post.call_args
        assert "labels" in call_args[1]["json"]
        assert call_args[1]["json"]["labels"] == ["label1", "label2"]


class TestGeneratePRsFromReport:
    """Tests for generate_prs_from_drift_report function"""
    
    def test_generate_from_empty_report(self, temp_git_repo, tmp_path):
        """Test PR generation from empty drift report"""
        report_path = tmp_path / "drift-report.json"
        report_data = {
            "services": []
        }
        
        with open(report_path, 'w') as f:
            json.dump(report_data, f)
        
        results = generate_prs_from_drift_report(
            report_path,
            temp_git_repo,
            dry_run=True
        )
        
        assert len(results) == 0
    
    def test_generate_from_report_dry_run(self, temp_git_repo, tmp_path, sample_compose_file):
        """Test PR generation in dry-run mode"""
        # Create compose file
        (temp_git_repo / sample_compose_file).parent.mkdir(parents=True, exist_ok=True)
        
        report_path = tmp_path / "drift-report.json"
        report_data = {
            "services": [
                {
                    "service_name": "pihole",
                    "stack_name": "dns-pihole",
                    "compose_file": str(sample_compose_file),
                    "drift_items": [
                        {
                            "field_path": "environment.TZ",
                            "running_value": "Europe/Brussels",
                            "git_value": "UTC",
                            "severity": "COSMETIC"
                        }
                    ]
                }
            ]
        }
        
        with open(report_path, 'w') as f:
            json.dump(report_data, f)
        
        results = generate_prs_from_drift_report(
            report_path,
            temp_git_repo,
            dry_run=True
        )
        
        assert "pihole" in results
        assert results["pihole"] is None  # Dry-run returns None


def test_dataclass_drift_item():
    """Test DriftItem dataclass"""
    item = DriftItem(
        service_name="test",
        stack_name="test-stack",
        field_path="image",
        running_value="nginx:latest",
        git_value="nginx:1.0",
        severity="BREAKING"
    )
    
    assert item.service_name == "test"
    assert item.severity == "BREAKING"


def test_dataclass_pr_metadata():
    """Test PRMetadata dataclass"""
    metadata = PRMetadata(
        branch_name="test-branch",
        title="Test PR",
        body="Body text",
        labels=["test"],
        base_branch="main"
    )
    
    assert metadata.branch_name == "test-branch"
    assert metadata.base_branch == "main"
    assert "test" in metadata.labels
