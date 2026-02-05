"""Unit tests for config.py module."""

import os
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from config import Config, load_config


class TestConfig:
    """Test suite for Config class."""
    
    def test_init_with_defaults(self, monkeypatch):
        """Test Config initialization with default values."""
        monkeypatch.setenv('TARGET_HOSTS', '192.168.50.19,192.168.50.161')
        
        config = Config()
        
        assert config.target_hosts == ['192.168.50.19', '192.168.50.161']
        assert config.ssh_username == 'root'
        assert config.ssh_timeout == 10
        assert config.docker_timeout == 30
        assert config.output_format == 'json'
        assert config.output_dir == './output'
        assert config.log_level == 'INFO'
    
    def test_init_with_custom_values(self, monkeypatch):
        """Test Config initialization with custom environment values."""
        monkeypatch.setenv('TARGET_HOSTS', '10.0.0.1')
        monkeypatch.setenv('SSH_USERNAME', 'admin')
        monkeypatch.setenv('SSH_TIMEOUT', '20')
        monkeypatch.setenv('DOCKER_TIMEOUT', '60')
        monkeypatch.setenv('OUTPUT_FORMAT', 'yaml')
        monkeypatch.setenv('LOG_LEVEL', 'DEBUG')
        
        config = Config()
        
        assert config.target_hosts == ['10.0.0.1']
        assert config.ssh_username == 'admin'
        assert config.ssh_timeout == 20
        assert config.docker_timeout == 60
        assert config.output_format == 'yaml'
        assert config.log_level == 'DEBUG'
    
    def test_target_hosts_parsing(self, monkeypatch):
        """Test parsing of comma-separated target hosts."""
        monkeypatch.setenv('TARGET_HOSTS', '  host1, host2 ,  host3  ')
        
        config = Config()
        
        assert config.target_hosts == ['host1', 'host2', 'host3']
    
    def test_target_hosts_empty_string(self, monkeypatch):
        """Test handling of empty TARGET_HOSTS."""
        monkeypatch.setenv('TARGET_HOSTS', '')
        
        config = Config()
        
        assert config.target_hosts == []
    
    def test_ssh_key_path_expansion(self, monkeypatch, tmp_path):
        """Test SSH key path expansion."""
        key_path = str(tmp_path / "test_key")
        Path(key_path).touch()
        monkeypatch.setenv('SSH_KEY_PATH', key_path)
        monkeypatch.setenv('TARGET_HOSTS', '192.168.1.1')
        
        config = Config()
        
        assert config.ssh_key_path == key_path
    
    def test_homelab_apps_path_expansion(self, monkeypatch):
        """Test homelab_apps_path expansion."""
        monkeypatch.setenv('HOMELAB_APPS_PATH', '~/projects/homelab-apps')
        monkeypatch.setenv('TARGET_HOSTS', '192.168.1.1')
        
        config = Config()
        
        assert config.homelab_apps_path == os.path.expanduser('~/projects/homelab-apps')
    
    def test_endpoint_optional(self, monkeypatch):
        """Test that endpoint is optional."""
        monkeypatch.setenv('TARGET_HOSTS', '192.168.1.1')
        
        config = Config()
        
        assert config.endpoint is None
    
    def test_endpoint_set(self, monkeypatch):
        """Test endpoint when set."""
        monkeypatch.setenv('TARGET_HOSTS', '192.168.1.1')
        monkeypatch.setenv('ENDPOINT', 'ct-docker-01')
        
        config = Config()
        
        assert config.endpoint == 'ct-docker-01'


class TestConfigValidation:
    """Test suite for Config validation."""
    
    def test_validate_success(self, monkeypatch, tmp_path):
        """Test successful validation with valid configuration."""
        key_path = str(tmp_path / "test_key")
        Path(key_path).touch()
        
        monkeypatch.setenv('TARGET_HOSTS', '192.168.1.1')
        monkeypatch.setenv('SSH_KEY_PATH', key_path)
        
        config = Config()
        config.validate()  # Should not raise
    
    def test_validate_missing_target_hosts(self, monkeypatch):
        """Test validation fails when TARGET_HOSTS is missing."""
        monkeypatch.setenv('TARGET_HOSTS', '')
        
        config = Config()
        
        with pytest.raises(ValueError, match="TARGET_HOSTS must be specified"):
            config.validate()
    
    def test_validate_ssh_key_not_found(self, monkeypatch):
        """Test validation fails when SSH key file doesn't exist."""
        monkeypatch.setenv('TARGET_HOSTS', '192.168.1.1')
        monkeypatch.setenv('SSH_KEY_PATH', '/nonexistent/key')
        
        config = Config()
        
        with pytest.raises(ValueError, match="SSH key not found"):
            config.validate()
    
    def test_validate_negative_ssh_timeout(self, monkeypatch):
        """Test validation fails with negative SSH timeout."""
        monkeypatch.setenv('TARGET_HOSTS', '192.168.1.1')
        monkeypatch.setenv('SSH_TIMEOUT', '-1')
        
        config = Config()
        
        with pytest.raises(ValueError, match="SSH_TIMEOUT must be positive"):
            config.validate()
    
    def test_validate_zero_docker_timeout(self, monkeypatch):
        """Test validation fails with zero Docker timeout."""
        monkeypatch.setenv('TARGET_HOSTS', '192.168.1.1')
        monkeypatch.setenv('DOCKER_TIMEOUT', '0')
        
        config = Config()
        
        with pytest.raises(ValueError, match="DOCKER_TIMEOUT must be positive"):
            config.validate()
    
    def test_validate_invalid_output_format(self, monkeypatch):
        """Test validation fails with invalid output format."""
        monkeypatch.setenv('TARGET_HOSTS', '192.168.1.1')
        monkeypatch.setenv('OUTPUT_FORMAT', 'xml')
        
        config = Config()
        
        with pytest.raises(ValueError, match="OUTPUT_FORMAT must be 'json' or 'yaml'"):
            config.validate()


class TestLoadConfig:
    """Test suite for load_config function."""
    
    def test_load_config_success(self, monkeypatch, tmp_path):
        """Test successful config loading and validation."""
        key_path = str(tmp_path / "test_key")
        Path(key_path).touch()
        
        monkeypatch.setenv('TARGET_HOSTS', '192.168.1.1,192.168.1.2')
        monkeypatch.setenv('SSH_KEY_PATH', key_path)
        
        config = load_config()
        
        assert isinstance(config, Config)
        assert len(config.target_hosts) == 2
    
    def test_load_config_validation_error(self, monkeypatch):
        """Test load_config raises error on invalid configuration."""
        monkeypatch.setenv('TARGET_HOSTS', '')
        
        with pytest.raises(ValueError, match="TARGET_HOSTS must be specified"):
            load_config()


class TestConfigRepr:
    """Test suite for Config string representation."""
    
    def test_repr(self, monkeypatch):
        """Test Config __repr__ method."""
        monkeypatch.setenv('TARGET_HOSTS', '192.168.1.1,192.168.1.2')
        monkeypatch.setenv('SSH_USERNAME', 'admin')
        monkeypatch.setenv('SSH_TIMEOUT', '15')
        monkeypatch.setenv('DOCKER_TIMEOUT', '45')
        
        config = Config()
        repr_str = repr(config)
        
        assert "Config(" in repr_str
        assert "target_hosts=['192.168.1.1', '192.168.1.2']" in repr_str
        assert "ssh_username=admin" in repr_str
        assert "ssh_timeout=15s" in repr_str
        assert "docker_timeout=45s" in repr_str
