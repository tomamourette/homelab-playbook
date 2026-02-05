"""Unit tests for docker_inspector.py module."""

import pytest
from unittest.mock import Mock, MagicMock, patch, call
from datetime import datetime

from docker_inspector import (
    DockerInspector,
    ContainerInfo,
    SSHConnectionError,
    DockerConnectionError,
    ContainerInspectionError
)


class TestContainerInfo:
    """Test suite for ContainerInfo dataclass."""
    
    def test_container_info_creation(self):
        """Test ContainerInfo initialization."""
        info = ContainerInfo(
            container_id="abc123def456",
            name="test-container",
            image="nginx:latest",
            status="running",
            labels={"app": "web"},
            networks={"bridge": {}},
            volumes=[{"source": "/data", "target": "/app/data"}],
            environment={"ENV": "prod"},
            ports={"80/tcp": [{"HostPort": "8080"}]},
            created="2024-01-01T00:00:00Z",
            started="2024-01-01T00:01:00Z"
        )
        
        assert info.container_id == "abc123def456"
        assert info.name == "test-container"
        assert info.image == "nginx:latest"
        assert info.status == "running"
    
    def test_container_info_to_dict(self):
        """Test ContainerInfo to_dict conversion."""
        info = ContainerInfo(
            container_id="abc123",
            name="test",
            image="nginx:latest",
            status="running",
            labels={},
            networks={},
            volumes=[],
            environment={},
            ports={},
            created="2024-01-01T00:00:00Z",
            started=None
        )
        
        result = info.to_dict()
        
        assert isinstance(result, dict)
        assert result['container_id'] == "abc123"
        assert result['name'] == "test"
        assert result['started'] is None


class TestDockerInspectorInit:
    """Test suite for DockerInspector initialization."""
    
    def test_init_with_defaults(self):
        """Test DockerInspector initialization with default values."""
        inspector = DockerInspector(
            host="192.168.1.100",
            username="root"
        )
        
        assert inspector.host == "192.168.1.100"
        assert inspector.username == "root"
        assert inspector.ssh_key_path is None
        assert inspector.ssh_timeout == 10
        assert inspector.docker_timeout == 30
        assert inspector.ssh_client is None
        assert inspector.docker_client is None
    
    def test_init_with_custom_values(self):
        """Test DockerInspector initialization with custom values."""
        inspector = DockerInspector(
            host="10.0.0.1",
            username="admin",
            ssh_key_path="/path/to/key",
            ssh_timeout=20,
            docker_timeout=60
        )
        
        assert inspector.host == "10.0.0.1"
        assert inspector.username == "admin"
        assert inspector.ssh_key_path == "/path/to/key"
        assert inspector.ssh_timeout == 20
        assert inspector.docker_timeout == 60


class TestDockerInspectorConnect:
    """Test suite for SSH connection methods."""
    
    @patch('docker_inspector.paramiko.SSHClient')
    def test_connect_success_with_key(self, mock_ssh_client_class):
        """Test successful SSH connection with key file."""
        mock_client = Mock()
        mock_ssh_client_class.return_value = mock_client
        
        inspector = DockerInspector(
            host="192.168.1.100",
            username="root",
            ssh_key_path="/path/to/key"
        )
        
        inspector.connect()
        
        mock_client.set_missing_host_key_policy.assert_called_once()
        mock_client.connect.assert_called_once_with(
            hostname="192.168.1.100",
            username="root",
            timeout=10,
            key_filename="/path/to/key"
        )
        assert inspector.ssh_client == mock_client
    
    @patch('docker_inspector.paramiko.SSHClient')
    def test_connect_success_without_key(self, mock_ssh_client_class):
        """Test successful SSH connection without key file (agent auth)."""
        mock_client = Mock()
        mock_ssh_client_class.return_value = mock_client
        
        inspector = DockerInspector(
            host="192.168.1.100",
            username="root"
        )
        
        inspector.connect()
        
        mock_client.connect.assert_called_once()
        call_kwargs = mock_client.connect.call_args[1]
        assert 'key_filename' not in call_kwargs
    
    @patch('docker_inspector.paramiko.SSHClient')
    def test_connect_authentication_failure(self, mock_ssh_client_class):
        """Test SSH connection with authentication failure."""
        mock_client = Mock()
        mock_client.connect.side_effect = paramiko.AuthenticationException("Auth failed")
        mock_ssh_client_class.return_value = mock_client
        
        inspector = DockerInspector(
            host="192.168.1.100",
            username="root"
        )
        
        with pytest.raises(SSHConnectionError, match="Authentication failed"):
            inspector.connect()
    
    @patch('docker_inspector.paramiko.SSHClient')
    def test_connect_ssh_exception(self, mock_ssh_client_class):
        """Test SSH connection with SSH exception."""
        mock_client = Mock()
        mock_client.connect.side_effect = paramiko.SSHException("Connection error")
        mock_ssh_client_class.return_value = mock_client
        
        inspector = DockerInspector(
            host="192.168.1.100",
            username="root"
        )
        
        with pytest.raises(SSHConnectionError, match="SSH connection error"):
            inspector.connect()
    
    @patch('docker_inspector.paramiko.SSHClient')
    def test_connect_generic_exception(self, mock_ssh_client_class):
        """Test SSH connection with generic exception."""
        mock_client = Mock()
        mock_client.connect.side_effect = Exception("Network error")
        mock_ssh_client_class.return_value = mock_client
        
        inspector = DockerInspector(
            host="192.168.1.100",
            username="root"
        )
        
        with pytest.raises(SSHConnectionError, match="Failed to connect"):
            inspector.connect()


class TestDockerInspectorDockerConnect:
    """Test suite for Docker connection methods."""
    
    @patch('docker_inspector.docker.DockerClient')
    def test_connect_docker_success(self, mock_docker_client_class):
        """Test successful Docker connection."""
        mock_docker = Mock()
        mock_docker.ping.return_value = True
        mock_docker_client_class.return_value = mock_docker
        
        inspector = DockerInspector(
            host="192.168.1.100",
            username="root"
        )
        inspector.ssh_client = Mock()  # Simulate SSH connection
        
        inspector.connect_docker()
        
        mock_docker_client_class.assert_called_once_with(
            base_url="ssh://root@192.168.1.100",
            timeout=30,
            use_ssh_client=True
        )
        mock_docker.ping.assert_called_once()
        assert inspector.docker_client == mock_docker
    
    def test_connect_docker_no_ssh(self):
        """Test Docker connection without SSH connection."""
        inspector = DockerInspector(
            host="192.168.1.100",
            username="root"
        )
        
        with pytest.raises(DockerConnectionError, match="SSH connection not established"):
            inspector.connect_docker()
    
    @patch('docker_inspector.docker.DockerClient')
    def test_connect_docker_exception(self, mock_docker_client_class):
        """Test Docker connection with exception."""
        from docker.errors import DockerException
        mock_docker_client_class.side_effect = DockerException("Docker error")
        
        inspector = DockerInspector(
            host="192.168.1.100",
            username="root"
        )
        inspector.ssh_client = Mock()
        
        with pytest.raises(DockerConnectionError, match="Failed to connect to Docker"):
            inspector.connect_docker()


class TestDockerInspectorListContainers:
    """Test suite for list_containers method."""
    
    def test_list_containers_success(self):
        """Test successful container listing."""
        mock_container1 = Mock()
        mock_container1.id = "abc123"
        mock_container2 = Mock()
        mock_container2.id = "def456"
        
        inspector = DockerInspector(
            host="192.168.1.100",
            username="root"
        )
        inspector.docker_client = Mock()
        inspector.docker_client.containers.list.return_value = [
            mock_container1,
            mock_container2
        ]
        
        result = inspector.list_containers()
        
        assert result == ["abc123", "def456"]
        inspector.docker_client.containers.list.assert_called_once_with(all=False)
    
    def test_list_containers_including_stopped(self):
        """Test container listing including stopped containers."""
        inspector = DockerInspector(
            host="192.168.1.100",
            username="root"
        )
        inspector.docker_client = Mock()
        inspector.docker_client.containers.list.return_value = []
        
        inspector.list_containers(all_containers=True)
        
        inspector.docker_client.containers.list.assert_called_once_with(all=True)
    
    def test_list_containers_no_docker_client(self):
        """Test list_containers without Docker connection."""
        inspector = DockerInspector(
            host="192.168.1.100",
            username="root"
        )
        
        with pytest.raises(DockerConnectionError, match="Docker client not initialized"):
            inspector.list_containers()
    
    def test_list_containers_docker_exception(self):
        """Test list_containers with Docker exception."""
        from docker.errors import DockerException
        
        inspector = DockerInspector(
            host="192.168.1.100",
            username="root"
        )
        inspector.docker_client = Mock()
        inspector.docker_client.containers.list.side_effect = DockerException("Error")
        
        with pytest.raises(ContainerInspectionError, match="Failed to list containers"):
            inspector.list_containers()


class TestDockerInspectorInspectContainer:
    """Test suite for inspect_container method."""
    
    def test_inspect_container_success(self):
        """Test successful container inspection."""
        mock_container = Mock()
        mock_container.attrs = {
            'Name': '/test-container',
            'Config': {
                'Image': 'nginx:latest',
                'Labels': {'app': 'web'},
                'Env': ['ENV=prod', 'DEBUG=false']
            },
            'State': {
                'Status': 'running',
                'StartedAt': '2024-01-01T00:01:00Z'
            },
            'NetworkSettings': {
                'Networks': {'bridge': {}}
            },
            'Mounts': [{
                'Type': 'bind',
                'Source': '/data',
                'Destination': '/app/data'
            }],
            'HostConfig': {
                'PortBindings': {
                    '80/tcp': [{'HostPort': '8080'}]
                }
            },
            'Created': '2024-01-01T00:00:00Z',
            'Id': 'abc123def456'
        }
        
        inspector = DockerInspector(
            host="192.168.1.100",
            username="root"
        )
        inspector.docker_client = Mock()
        inspector.docker_client.containers.get.return_value = mock_container
        
        result = inspector.inspect_container("abc123")
        
        assert isinstance(result, ContainerInfo)
        assert result.name == "test-container"
        assert result.image == "nginx:latest"
        assert result.status == "running"
        assert result.labels == {'app': 'web'}
    
    def test_inspect_container_no_docker_client(self):
        """Test inspect_container without Docker connection."""
        inspector = DockerInspector(
            host="192.168.1.100",
            username="root"
        )
        
        with pytest.raises(DockerConnectionError, match="Docker client not initialized"):
            inspector.inspect_container("abc123")
    
    def test_inspect_container_not_found(self):
        """Test inspect_container with non-existent container."""
        from docker.errors import NotFound
        
        inspector = DockerInspector(
            host="192.168.1.100",
            username="root"
        )
        inspector.docker_client = Mock()
        inspector.docker_client.containers.get.side_effect = NotFound("Not found")
        
        with pytest.raises(ContainerInspectionError, match="Container .* not found"):
            inspector.inspect_container("nonexistent")


class TestDockerInspectorDisconnect:
    """Test suite for disconnect method."""
    
    def test_disconnect_both_clients(self):
        """Test disconnecting both SSH and Docker clients."""
        inspector = DockerInspector(
            host="192.168.1.100",
            username="root"
        )
        mock_ssh = Mock()
        mock_docker = Mock()
        inspector.ssh_client = mock_ssh
        inspector.docker_client = mock_docker
        
        inspector.disconnect()
        
        # Verify close was called before setting to None
        mock_docker.close.assert_called_once()
        mock_ssh.close.assert_called_once()
        # Verify clients are None after disconnect
        assert inspector.docker_client is None
        assert inspector.ssh_client is None
    
    def test_disconnect_only_ssh(self):
        """Test disconnecting only SSH client."""
        inspector = DockerInspector(
            host="192.168.1.100",
            username="root"
        )
        mock_ssh = Mock()
        inspector.ssh_client = mock_ssh
        
        inspector.disconnect()
        
        mock_ssh.close.assert_called_once()
        assert inspector.ssh_client is None
    
    def test_disconnect_no_clients(self):
        """Test disconnecting when no clients are connected."""
        inspector = DockerInspector(
            host="192.168.1.100",
            username="root"
        )
        
        inspector.disconnect()  # Should not raise


# Import paramiko for exception testing
import paramiko
