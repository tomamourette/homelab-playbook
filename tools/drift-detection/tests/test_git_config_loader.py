"""Unit tests for git_config_loader.py module."""

import pytest
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch, mock_open
import yaml

from git_config_loader import (
    GitConfigLoader,
    GitBaselineConfig,
    GitConfigError,
    ComposeFileNotFoundError,
    ComposeParseError,
    load_git_baselines
)


class TestGitBaselineConfig:
    """Test suite for GitBaselineConfig dataclass."""
    
    def test_baseline_config_creation(self):
        """Test GitBaselineConfig initialization."""
        config = GitBaselineConfig(
            name="test-service",
            image="nginx:latest",
            labels={"app": "web"},
            networks=["proxy"],
            volumes=["/data:/app/data"],
            environment={"ENV": "prod"},
            ports=["80:8080"],
            stack_name="web-stack",
            compose_file="/path/to/docker-compose.yml"
        )
        
        assert config.name == "test-service"
        assert config.image == "nginx:latest"
        assert config.stack_name == "web-stack"
    
    def test_baseline_config_to_dict(self):
        """Test GitBaselineConfig to_dict conversion."""
        config = GitBaselineConfig(
            name="test",
            image="nginx:latest",
            labels={},
            networks=[],
            volumes=[],
            environment={},
            ports=[],
            stack_name="test-stack",
            compose_file="/test/compose.yml"
        )
        
        result = config.to_dict()
        
        assert isinstance(result, dict)
        assert result['name'] == "test"
        assert result['stack_name'] == "test-stack"
        assert 'compose_file' in result


class TestGitConfigLoaderInit:
    """Test suite for GitConfigLoader initialization."""
    
    def test_init_with_apps_path_only(self):
        """Test initialization with only homelab-apps path."""
        loader = GitConfigLoader(
            homelab_apps_path="/path/to/homelab-apps"
        )
        
        assert loader.homelab_apps_path == Path("/path/to/homelab-apps")
        assert loader.homelab_infra_path is None
        assert loader.endpoint is None
    
    def test_init_with_all_parameters(self):
        """Test initialization with all parameters."""
        loader = GitConfigLoader(
            homelab_apps_path="/path/to/homelab-apps",
            homelab_infra_path="/path/to/homelab-infra",
            endpoint="ct-docker-01"
        )
        
        assert loader.homelab_apps_path == Path("/path/to/homelab-apps")
        assert loader.homelab_infra_path == Path("/path/to/homelab-infra")
        assert loader.endpoint == "ct-docker-01"


class TestDiscoverStacks:
    """Test suite for discover_stacks method."""
    
    def test_discover_stacks_apps_path_not_exists(self):
        """Test discover_stacks when homelab-apps path doesn't exist."""
        loader = GitConfigLoader(
            homelab_apps_path="/nonexistent/path"
        )
        
        with pytest.raises(GitConfigError, match="homelab-apps path does not exist"):
            loader.discover_stacks()
    
    @patch('git_config_loader.Path')
    def test_discover_stacks_finds_compose_files(self, mock_path):
        """Test discovering stacks with docker-compose.yml files."""
        # Mock the directory structure
        mock_apps_path = MagicMock()
        mock_apps_path.exists.return_value = True
        
        mock_stacks_dir = MagicMock()
        mock_apps_path.__truediv__.return_value = mock_stacks_dir
        mock_stacks_dir.exists.return_value = True
        
        # Create mock stack directories
        mock_stack1 = MagicMock()
        mock_stack1.is_dir.return_value = True
        mock_stack1.name = "web-stack"
        mock_compose1 = MagicMock()
        mock_compose1.exists.return_value = True
        mock_stack1.__truediv__.return_value = mock_compose1
        
        mock_stack2 = MagicMock()
        mock_stack2.is_dir.return_value = True
        mock_stack2.name = "db-stack"
        mock_compose2 = MagicMock()
        mock_compose2.exists.return_value = True
        mock_stack2.__truediv__.return_value = mock_compose2
        
        mock_stacks_dir.iterdir.return_value = [mock_stack1, mock_stack2]
        
        mock_path.return_value = mock_apps_path
        
        loader = GitConfigLoader(homelab_apps_path="/test/apps")
        loader.homelab_apps_path = mock_apps_path
        
        stacks = loader.discover_stacks()
        
        assert len(stacks) == 2


class TestLoadEnvFile:
    """Test suite for load_env_file method."""
    
    @patch('git_config_loader.dotenv_values')
    def test_load_env_file_exists(self, mock_dotenv):
        """Test loading .env file when it exists."""
        mock_dotenv.return_value = {
            'VAR1': 'value1',
            'VAR2': 'value2'
        }
        
        loader = GitConfigLoader(homelab_apps_path="/test")
        
        with patch.object(Path, 'exists', return_value=True):
            env_vars = loader.load_env_file(Path("/test/stack"))
        
        assert env_vars == {'VAR1': 'value1', 'VAR2': 'value2'}
    
    @patch('git_config_loader.dotenv_values')
    def test_load_env_file_filters_none_values(self, mock_dotenv):
        """Test that None values are filtered out."""
        mock_dotenv.return_value = {
            'VAR1': 'value1',
            'VAR2': None,
            'VAR3': 'value3'
        }
        
        loader = GitConfigLoader(homelab_apps_path="/test")
        
        with patch.object(Path, 'exists', return_value=True):
            env_vars = loader.load_env_file(Path("/test/stack"))
        
        assert 'VAR2' not in env_vars
        assert env_vars == {'VAR1': 'value1', 'VAR3': 'value3'}
    
    @patch('git_config_loader.dotenv_values')
    def test_load_env_file_falls_back_to_sample(self, mock_dotenv):
        """Test fallback to .env.sample when .env is empty."""
        # When .env exists but returns empty dict, fallback to .env.sample
        mock_dotenv.side_effect = [
            {},  # .env returns empty
            {'SAMPLE_VAR': 'sample_value'}  # .env.sample has values
        ]
        
        loader = GitConfigLoader(homelab_apps_path="/test")
        
        # Mock both files exist
        with patch.object(Path, 'exists', return_value=True):
            env_vars = loader.load_env_file(Path("/test/stack"))
        
        assert env_vars == {'SAMPLE_VAR': 'sample_value'}


class TestSubstituteEnvVars:
    """Test suite for substitute_env_vars method."""
    
    def test_substitute_simple_var(self):
        """Test substituting simple ${VAR} syntax."""
        loader = GitConfigLoader(homelab_apps_path="/test")
        env_vars = {'VAR1': 'value1', 'VAR2': 'value2'}
        
        data = "prefix_${VAR1}_${VAR2}_suffix"
        result = loader.substitute_env_vars(data, env_vars)
        
        assert result == "prefix_value1_value2_suffix"
    
    def test_substitute_var_with_default(self):
        """Test substituting ${VAR:-default} syntax."""
        loader = GitConfigLoader(homelab_apps_path="/test")
        env_vars = {'VAR1': 'value1'}
        
        data = "${VAR1}_${VAR2:-default_value}"
        result = loader.substitute_env_vars(data, env_vars)
        
        assert result == "value1_default_value"
    
    def test_substitute_missing_var_without_default(self):
        """Test that missing vars without defaults remain unchanged."""
        loader = GitConfigLoader(homelab_apps_path="/test")
        env_vars = {'VAR1': 'value1'}
        
        data = "${VAR1}_${MISSING_VAR}"
        result = loader.substitute_env_vars(data, env_vars)
        
        assert result == "value1_${MISSING_VAR}"
    
    def test_substitute_in_dict(self):
        """Test substitution in dictionary structure."""
        loader = GitConfigLoader(homelab_apps_path="/test")
        env_vars = {'HOST': 'localhost', 'PORT': '8080'}
        
        data = {
            'url': 'http://${HOST}:${PORT}',
            'nested': {
                'value': '${HOST}'
            }
        }
        result = loader.substitute_env_vars(data, env_vars)
        
        assert result['url'] == 'http://localhost:8080'
        assert result['nested']['value'] == 'localhost'
    
    def test_substitute_in_list(self):
        """Test substitution in list structure."""
        loader = GitConfigLoader(homelab_apps_path="/test")
        env_vars = {'VAR': 'value'}
        
        data = ['${VAR}', 'static', '${VAR}_suffix']
        result = loader.substitute_env_vars(data, env_vars)
        
        assert result == ['value', 'static', 'value_suffix']
    
    def test_substitute_non_string_unchanged(self):
        """Test that non-string values remain unchanged."""
        loader = GitConfigLoader(homelab_apps_path="/test")
        env_vars = {}
        
        assert loader.substitute_env_vars(123, env_vars) == 123
        assert loader.substitute_env_vars(True, env_vars) is True
        assert loader.substitute_env_vars(None, env_vars) is None


class TestLoadComposeFile:
    """Test suite for load_compose_file method."""
    
    def test_load_compose_file_not_found(self):
        """Test loading non-existent compose file."""
        loader = GitConfigLoader(homelab_apps_path="/test")
        
        with pytest.raises(ComposeFileNotFoundError, match="Compose file not found"):
            loader.load_compose_file(Path("/nonexistent/docker-compose.yml"))
    
    @patch('builtins.open', new_callable=mock_open, read_data="version: '3'\nservices:\n  web:\n    image: nginx")
    @patch.object(Path, 'exists', return_value=True)
    def test_load_compose_file_success(self, mock_exists, mock_file):
        """Test successful compose file loading."""
        loader = GitConfigLoader(homelab_apps_path="/test")
        
        result = loader.load_compose_file(Path("/test/docker-compose.yml"))
        
        assert 'services' in result
        assert 'web' in result['services']
    
    @patch('builtins.open', new_callable=mock_open, read_data="invalid: yaml: content: [[[")
    @patch.object(Path, 'exists', return_value=True)
    def test_load_compose_file_invalid_yaml(self, mock_exists, mock_file):
        """Test loading compose file with invalid YAML."""
        loader = GitConfigLoader(homelab_apps_path="/test")
        
        with pytest.raises(ComposeParseError, match="Failed to parse"):
            loader.load_compose_file(Path("/test/docker-compose.yml"))
    
    @patch('builtins.open', new_callable=mock_open, read_data="")
    @patch.object(Path, 'exists', return_value=True)
    def test_load_compose_file_empty(self, mock_exists, mock_file):
        """Test loading empty compose file."""
        loader = GitConfigLoader(homelab_apps_path="/test")
        
        with pytest.raises(ComposeParseError, match="Empty compose file"):
            loader.load_compose_file(Path("/test/docker-compose.yml"))


class TestMergeComposeConfigs:
    """Test suite for merge_compose_configs method."""
    
    def test_merge_simple_override(self):
        """Test merging with simple override."""
        loader = GitConfigLoader(homelab_apps_path="/test")
        
        base = {
            'services': {
                'web': {
                    'image': 'nginx:1.0',
                    'ports': ['80:80']
                }
            }
        }
        
        override = {
            'services': {
                'web': {
                    'image': 'nginx:2.0'
                }
            }
        }
        
        result = loader.merge_compose_configs(base, override)
        
        assert result['services']['web']['image'] == 'nginx:2.0'
        assert result['services']['web']['ports'] == ['80:80']  # Preserved
    
    def test_merge_list_replacement(self):
        """Test that lists are replaced, not merged."""
        loader = GitConfigLoader(homelab_apps_path="/test")
        
        base = {
            'services': {
                'web': {
                    'volumes': ['/data1:/app/data1', '/data2:/app/data2']
                }
            }
        }
        
        override = {
            'services': {
                'web': {
                    'volumes': ['/data3:/app/data3']
                }
            }
        }
        
        result = loader.merge_compose_configs(base, override)
        
        # Lists should be replaced, not merged
        assert result['services']['web']['volumes'] == ['/data3:/app/data3']
        assert len(result['services']['web']['volumes']) == 1
    
    def test_merge_deep_nested(self):
        """Test deep nested merge."""
        loader = GitConfigLoader(homelab_apps_path="/test")
        
        base = {
            'services': {
                'web': {
                    'labels': {
                        'app': 'web',
                        'version': '1.0'
                    }
                }
            }
        }
        
        override = {
            'services': {
                'web': {
                    'labels': {
                        'version': '2.0',
                        'env': 'prod'
                    }
                }
            }
        }
        
        result = loader.merge_compose_configs(base, override)
        
        assert result['services']['web']['labels']['app'] == 'web'  # Preserved
        assert result['services']['web']['labels']['version'] == '2.0'  # Overridden
        assert result['services']['web']['labels']['env'] == 'prod'  # Added


class TestParseServiceConfig:
    """Test suite for parse_service_config method."""
    
    def test_parse_service_basic(self):
        """Test parsing basic service configuration."""
        loader = GitConfigLoader(homelab_apps_path="/test")
        
        service_config = {
            'image': 'nginx:latest',
            'labels': {'app': 'web'},
            'networks': ['proxy'],
            'volumes': ['/data:/app/data'],
            'environment': {'ENV': 'prod'},
            'ports': ['80:8080']
        }
        
        result = loader.parse_service_config(
            service_name="web",
            service_config=service_config,
            stack_name="web-stack",
            compose_file="/test/compose.yml"
        )
        
        assert isinstance(result, GitBaselineConfig)
        assert result.name == "web"
        assert result.image == "nginx:latest"
        assert result.stack_name == "web-stack"
    
    def test_parse_service_labels_as_list(self):
        """Test parsing labels in list format."""
        loader = GitConfigLoader(homelab_apps_path="/test")
        
        service_config = {
            'image': 'nginx:latest',
            'labels': [
                'app=web',
                'version=1.0'
            ]
        }
        
        result = loader.parse_service_config(
            service_name="web",
            service_config=service_config,
            stack_name="test",
            compose_file="/test"
        )
        
        assert result.labels == {'app': 'web', 'version': '1.0'}
    
    def test_parse_service_environment_as_list(self):
        """Test parsing environment in list format."""
        loader = GitConfigLoader(homelab_apps_path="/test")
        
        service_config = {
            'image': 'nginx:latest',
            'environment': [
                'VAR1=value1',
                'VAR2=value2',
                'VAR_NO_VALUE'
            ]
        }
        
        result = loader.parse_service_config(
            service_name="web",
            service_config=service_config,
            stack_name="test",
            compose_file="/test"
        )
        
        assert result.environment['VAR1'] == 'value1'
        assert result.environment['VAR2'] == 'value2'
        assert result.environment['VAR_NO_VALUE'] == ''


class TestLoadGitBaselines:
    """Test suite for load_git_baselines convenience function."""
    
    @patch.object(GitConfigLoader, 'load_all_baselines')
    def test_load_git_baselines(self, mock_load_all):
        """Test convenience function for loading baselines."""
        mock_baseline = GitBaselineConfig(
            name="test",
            image="nginx:latest",
            labels={},
            networks=[],
            volumes=[],
            environment={},
            ports=[],
            stack_name="test-stack",
            compose_file="/test"
        )
        mock_load_all.return_value = [mock_baseline]
        
        result = load_git_baselines(
            homelab_apps_path="/test/apps",
            endpoint="ct-docker-01"
        )
        
        assert 'baselines' in result
        assert 'count' in result
        assert 'endpoint' in result
        assert result['count'] == 1
        assert result['endpoint'] == "ct-docker-01"
