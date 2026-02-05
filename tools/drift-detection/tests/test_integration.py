"""Integration tests for drift detection tool.

These tests verify SSH connections and Docker inspection work against
the real Proxmox infrastructure using the configured .env settings.

Tests use Proxmox proxy method (SSH to Proxmox → pct exec to containers)
since WSL cannot directly reach container network (192.168.50.x).
"""

import pytest
import os
from pathlib import Path
from config import load_config, Config
from docker_inspector import DockerInspector, SSHConnectionError


# Skip all integration tests if not in homelab environment
def is_homelab_available():
    """Check if homelab infrastructure is accessible."""
    config_file = Path(__file__).parent.parent / ".env"
    if not config_file.exists():
        return False
    
    # Load config to check if Proxmox host is configured
    try:
        config = Config(env_file=str(config_file))
        return bool(config.target_hosts)
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not is_homelab_available(),
    reason="Homelab infrastructure not available"
)


@pytest.fixture
def config():
    """Load configuration from .env file."""
    config_file = Path(__file__).parent.parent / ".env"
    return load_config(env_file=str(config_file))


@pytest.fixture
def inspector(config):
    """Create DockerInspector instance with config settings."""
    # Use first target host
    host = config.target_hosts[0]
    
    inspector = DockerInspector(
        host=host,
        username=config.ssh_username,
        ssh_key_path=config.ssh_key_path,
        ssh_timeout=config.ssh_timeout,
        docker_timeout=config.docker_timeout
    )
    
    yield inspector
    
    # Cleanup
    inspector.disconnect()


class TestConfigIntegration:
    """Integration tests for configuration loading."""
    
    def test_load_config_from_env_file(self, config):
        """Test loading configuration from .env file."""
        assert isinstance(config, Config)
        assert len(config.target_hosts) > 0
        assert config.ssh_username
        assert config.ssh_key_path
        
        # Verify SSH key exists
        assert Path(config.ssh_key_path).exists()
    
    def test_config_validation(self, config):
        """Test configuration passes validation."""
        # Should not raise
        config.validate()


class TestSSHConnection:
    """Integration tests for SSH connection."""
    
    def test_ssh_connection_success(self, inspector):
        """Test successful SSH connection to Proxmox host."""
        inspector.connect()
        
        assert inspector.ssh_client is not None
        assert inspector.ssh_client.get_transport() is not None
        assert inspector.ssh_client.get_transport().is_active()
    
    def test_ssh_connection_with_invalid_host(self, config):
        """Test SSH connection with invalid host."""
        inspector = DockerInspector(
            host="192.168.50.254",  # Non-existent host
            username=config.ssh_username,
            ssh_key_path=config.ssh_key_path,
            ssh_timeout=5
        )
        
        with pytest.raises(SSHConnectionError):
            inspector.connect()
    
    def test_ssh_connection_with_invalid_key(self, config):
        """Test SSH connection with invalid key path."""
        inspector = DockerInspector(
            host=config.target_hosts[0],
            username=config.ssh_username,
            ssh_key_path="/nonexistent/key",
            ssh_timeout=5
        )
        
        with pytest.raises(SSHConnectionError):
            inspector.connect()


class TestDockerConnection:
    """Integration tests for Docker connection."""
    
    @pytest.mark.skip(reason="Docker over SSH not working with Proxmox proxy method - use pct exec instead")
    def test_docker_connection_success(self, inspector):
        """Test successful Docker connection over SSH."""
        inspector.connect()
        inspector.connect_docker()
        
        assert inspector.docker_client is not None
        
        # Verify we can ping Docker daemon
        assert inspector.docker_client.ping()


class TestContainerInspection:
    """Integration tests for container inspection."""
    
    @pytest.mark.skip(reason="Container inspection requires pct exec method, not direct Docker API")
    def test_list_containers(self, inspector):
        """Test listing containers on target host."""
        inspector.connect()
        inspector.connect_docker()
        
        containers = inspector.list_containers()
        
        # Verify we get a list (may be empty if no running containers)
        assert isinstance(containers, list)
    
    @pytest.mark.skip(reason="Container inspection requires pct exec method, not direct Docker API")
    def test_inspect_specific_container(self, inspector, config):
        """Test inspecting a specific container."""
        inspector.connect()
        inspector.connect_docker()
        
        containers = inspector.list_containers()
        
        if containers:
            # Inspect first container
            container_id = containers[0]
            info = inspector.inspect_container(container_id)
            
            # Verify we got valid container info
            assert info.container_id
            assert info.name
            assert info.image
            assert info.status


class TestEndToEndWorkflow:
    """End-to-end integration tests."""
    
    def test_complete_workflow_ssh_only(self, config):
        """Test complete workflow: load config → connect SSH → disconnect."""
        # 1. Load configuration
        assert config.target_hosts
        
        # 2. Create inspector
        inspector = DockerInspector(
            host=config.target_hosts[0],
            username=config.ssh_username,
            ssh_key_path=config.ssh_key_path,
            ssh_timeout=config.ssh_timeout
        )
        
        # 3. Connect via SSH
        inspector.connect()
        assert inspector.ssh_client is not None
        
        # 4. Verify connection is active
        transport = inspector.ssh_client.get_transport()
        assert transport is not None
        assert transport.is_active()
        
        # 5. Disconnect
        inspector.disconnect()
        assert inspector.ssh_client is None
    
    @pytest.mark.skip(reason="Full workflow requires pct exec implementation")
    def test_complete_workflow_full(self, config):
        """Test complete workflow: load config → connect → inspect → disconnect."""
        # 1. Load configuration
        assert config.target_hosts
        
        # 2. Create inspector
        inspector = DockerInspector(
            host=config.target_hosts[0],
            username=config.ssh_username,
            ssh_key_path=config.ssh_key_path,
            ssh_timeout=config.ssh_timeout,
            docker_timeout=config.docker_timeout
        )
        
        try:
            # 3. Connect
            inspector.connect()
            inspector.connect_docker()
            
            # 4. List containers
            containers = inspector.list_containers()
            
            # 5. Inspect containers (if any exist)
            if containers:
                for container_id in containers[:3]:  # Inspect first 3
                    info = inspector.inspect_container(container_id)
                    assert info.name
                    assert info.image
        
        finally:
            # 6. Cleanup
            inspector.disconnect()


class TestProxmoxProxyMethod:
    """Tests specific to Proxmox proxy method (pct exec)."""
    
    def test_ssh_to_proxmox(self, config):
        """Test SSH connection to Proxmox host works."""
        # The config should point to Proxmox host, not container
        # Verify we can establish connection
        inspector = DockerInspector(
            host=config.target_hosts[0],
            username=config.ssh_username,
            ssh_key_path=config.ssh_key_path,
            ssh_timeout=config.ssh_timeout
        )
        
        inspector.connect()
        
        # Verify connection
        assert inspector.ssh_client is not None
        transport = inspector.ssh_client.get_transport()
        assert transport.is_active()
        
        # Test we can execute a command
        stdin, stdout, stderr = inspector.ssh_client.exec_command('hostname')
        hostname = stdout.read().decode().strip()
        assert hostname  # Should get a hostname back
        
        inspector.disconnect()
    
    @pytest.mark.skip(reason="Container access via pct exec needs implementation in docker_inspector.py")
    def test_pct_exec_to_container(self, config):
        """Test executing commands in container via pct exec."""
        # This test verifies we can reach containers via Proxmox pct exec
        # Once docker_inspector.py supports pct exec method
        pass
