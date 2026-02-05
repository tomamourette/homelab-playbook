"""Docker container inspection over SSH.

This module provides functionality to connect to remote Docker hosts via SSH
and extract container configuration data for drift analysis.
"""

import json
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime

import paramiko
import docker
from docker.errors import DockerException


# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


@dataclass
class ContainerInfo:
    """Structured container information.
    
    Attributes:
        container_id: Full container ID
        name: Container name
        image: Image name and tag
        status: Container status (running, stopped, etc.)
        labels: Dictionary of container labels
        networks: List of network configurations
        volumes: List of volume mounts
        environment: Dictionary of environment variables
        ports: Port mapping configuration
        created: Container creation timestamp
        started: Container start timestamp
    """
    container_id: str
    name: str
    image: str
    status: str
    labels: Dict[str, str]
    networks: Dict[str, Any]
    volumes: List[Dict[str, str]]
    environment: Dict[str, str]
    ports: Dict[str, Any]
    created: str
    started: Optional[str]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


class SSHConnectionError(Exception):
    """Raised when SSH connection fails."""
    pass


class DockerConnectionError(Exception):
    """Raised when Docker connection fails."""
    pass


class ContainerInspectionError(Exception):
    """Raised when container inspection fails."""
    pass


class DockerInspector:
    """Docker inspector that connects via SSH to remote hosts.
    
    This class manages SSH connections to remote Docker hosts and provides
    methods to inspect running containers and extract their configurations.
    """
    
    def __init__(
        self,
        host: str,
        username: str,
        ssh_key_path: Optional[str] = None,
        ssh_timeout: int = 10,
        docker_timeout: int = 30
    ) -> None:
        """Initialize Docker inspector.
        
        Args:
            host: Target host IP address or hostname
            username: SSH username
            ssh_key_path: Path to SSH private key (None to use SSH agent)
            ssh_timeout: SSH connection timeout in seconds
            docker_timeout: Docker API timeout in seconds
        """
        self.host = host
        self.username = username
        self.ssh_key_path = ssh_key_path
        self.ssh_timeout = ssh_timeout
        self.docker_timeout = docker_timeout
        
        self.ssh_client: Optional[paramiko.SSHClient] = None
        self.docker_client: Optional[docker.DockerClient] = None
        
        logger.info(f"Initialized DockerInspector for {username}@{host}")
    
    def connect(self) -> None:
        """Establish SSH connection to target host.
        
        Raises:
            SSHConnectionError: If SSH connection fails
        """
        try:
            logger.info(f"Connecting to {self.host} via SSH...")
            
            self.ssh_client = paramiko.SSHClient()
            self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            # Prepare connection parameters
            connect_kwargs = {
                'hostname': self.host,
                'username': self.username,
                'timeout': self.ssh_timeout,
            }
            
            if self.ssh_key_path:
                connect_kwargs['key_filename'] = self.ssh_key_path
            
            # Attempt connection
            self.ssh_client.connect(**connect_kwargs)
            
            logger.info(f"Successfully connected to {self.host}")
            
        except paramiko.AuthenticationException as e:
            raise SSHConnectionError(
                f"Authentication failed for {self.username}@{self.host}: {e}"
            )
        except paramiko.SSHException as e:
            raise SSHConnectionError(
                f"SSH connection error to {self.host}: {e}"
            )
        except Exception as e:
            raise SSHConnectionError(
                f"Failed to connect to {self.host}: {e}"
            )
    
    def connect_docker(self) -> None:
        """Connect to Docker daemon over SSH.
        
        Raises:
            DockerConnectionError: If Docker connection fails
        """
        if not self.ssh_client:
            raise DockerConnectionError("SSH connection not established")
        
        try:
            logger.info(f"Connecting to Docker on {self.host}...")
            
            # Create Docker client using SSH connection
            docker_url = f"ssh://{self.username}@{self.host}"
            self.docker_client = docker.DockerClient(
                base_url=docker_url,
                timeout=self.docker_timeout,
                use_ssh_client=True
            )
            
            # Test connection by pinging Docker daemon
            self.docker_client.ping()
            
            logger.info(f"Successfully connected to Docker on {self.host}")
            
        except DockerException as e:
            raise DockerConnectionError(
                f"Failed to connect to Docker on {self.host}: {e}"
            )
        except Exception as e:
            raise DockerConnectionError(
                f"Unexpected error connecting to Docker on {self.host}: {e}"
            )
    
    def list_containers(self, all_containers: bool = False) -> List[str]:
        """List container IDs on the target host.
        
        Args:
            all_containers: If True, include stopped containers
        
        Returns:
            List of container IDs
        
        Raises:
            DockerConnectionError: If not connected to Docker
            ContainerInspectionError: If listing fails
        """
        if not self.docker_client:
            raise DockerConnectionError("Docker client not initialized")
        
        try:
            containers = self.docker_client.containers.list(all=all_containers)
            container_ids = [c.id for c in containers]
            
            logger.info(
                f"Found {len(container_ids)} container(s) on {self.host}"
            )
            
            return container_ids
            
        except DockerException as e:
            raise ContainerInspectionError(
                f"Failed to list containers on {self.host}: {e}"
            )
    
    def inspect_container(self, container_id: str) -> ContainerInfo:
        """Inspect a specific container and extract configuration.
        
        Args:
            container_id: Container ID or name
        
        Returns:
            ContainerInfo object with extracted data
        
        Raises:
            DockerConnectionError: If not connected to Docker
            ContainerInspectionError: If inspection fails
        """
        if not self.docker_client:
            raise DockerConnectionError("Docker client not initialized")
        
        try:
            logger.debug(f"Inspecting container {container_id[:12]}...")
            
            container = self.docker_client.containers.get(container_id)
            attrs = container.attrs
            
            # Extract container name (remove leading slash)
            name = attrs['Name'].lstrip('/')
            
            # Extract image name
            image = attrs['Config']['Image']
            
            # Extract labels
            labels = attrs['Config'].get('Labels', {}) or {}
            
            # Extract networks
            networks = attrs['NetworkSettings'].get('Networks', {})
            
            # Extract volumes
            volumes = []
            if attrs.get('Mounts'):
                for mount in attrs['Mounts']:
                    volumes.append({
                        'type': mount['Type'],
                        'source': mount.get('Source', ''),
                        'destination': mount['Destination'],
                        'mode': mount.get('Mode', ''),
                        'rw': mount.get('RW', True)
                    })
            
            # Extract environment variables (parse into dict)
            env_list = attrs['Config'].get('Env', []) or []
            environment = {}
            for env_var in env_list:
                if '=' in env_var:
                    key, value = env_var.split('=', 1)
                    environment[key] = value
            
            # Extract ports
            ports = attrs['NetworkSettings'].get('Ports', {}) or {}
            
            # Extract timestamps
            created = attrs['Created']
            started = attrs['State'].get('StartedAt', '')
            
            container_info = ContainerInfo(
                container_id=attrs['Id'],
                name=name,
                image=image,
                status=attrs['State']['Status'],
                labels=labels,
                networks=networks,
                volumes=volumes,
                environment=environment,
                ports=ports,
                created=created,
                started=started if started else None
            )
            
            logger.debug(f"Successfully inspected container {name}")
            
            return container_info
            
        except docker.errors.NotFound:
            raise ContainerInspectionError(
                f"Container {container_id} not found on {self.host}"
            )
        except DockerException as e:
            raise ContainerInspectionError(
                f"Failed to inspect container {container_id}: {e}"
            )
        except KeyError as e:
            raise ContainerInspectionError(
                f"Missing expected field in container data: {e}"
            )
    
    def inspect_all_containers(
        self,
        all_containers: bool = False
    ) -> List[ContainerInfo]:
        """Inspect all containers on the target host.
        
        Args:
            all_containers: If True, include stopped containers
        
        Returns:
            List of ContainerInfo objects
        
        Raises:
            DockerConnectionError: If not connected to Docker
            ContainerInspectionError: If inspection fails
        """
        container_ids = self.list_containers(all_containers=all_containers)
        
        results = []
        failed = []
        
        for container_id in container_ids:
            try:
                info = self.inspect_container(container_id)
                results.append(info)
            except ContainerInspectionError as e:
                logger.error(f"Failed to inspect {container_id[:12]}: {e}")
                failed.append(container_id)
        
        if failed:
            logger.warning(
                f"Failed to inspect {len(failed)} container(s): "
                f"{', '.join(c[:12] for c in failed)}"
            )
        
        logger.info(
            f"Successfully inspected {len(results)} container(s) on {self.host}"
        )
        
        return results
    
    def disconnect(self) -> None:
        """Close SSH and Docker connections."""
        if self.docker_client:
            try:
                self.docker_client.close()
                logger.debug(f"Closed Docker connection to {self.host}")
            except Exception as e:
                logger.warning(f"Error closing Docker connection: {e}")
            finally:
                self.docker_client = None
        
        if self.ssh_client:
            try:
                self.ssh_client.close()
                logger.debug(f"Closed SSH connection to {self.host}")
            except Exception as e:
                logger.warning(f"Error closing SSH connection: {e}")
            finally:
                self.ssh_client = None
    
    def __enter__(self):
        """Context manager entry."""
        self.connect()
        self.connect_docker()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()


def inspect_host(
    host: str,
    username: str,
    ssh_key_path: Optional[str] = None,
    ssh_timeout: int = 10,
    docker_timeout: int = 30,
    all_containers: bool = False
) -> Dict[str, Any]:
    """Inspect all containers on a single host.
    
    This is a convenience function that handles connection and inspection
    in a single call.
    
    Args:
        host: Target host IP address
        username: SSH username
        ssh_key_path: Path to SSH private key
        ssh_timeout: SSH connection timeout
        docker_timeout: Docker API timeout
        all_containers: Include stopped containers
    
    Returns:
        Dictionary with host info and container data
    
    Raises:
        SSHConnectionError: If SSH connection fails
        DockerConnectionError: If Docker connection fails
        ContainerInspectionError: If inspection fails
    """
    inspector = DockerInspector(
        host=host,
        username=username,
        ssh_key_path=ssh_key_path,
        ssh_timeout=ssh_timeout,
        docker_timeout=docker_timeout
    )
    
    try:
        inspector.connect()
        inspector.connect_docker()
        
        containers = inspector.inspect_all_containers(
            all_containers=all_containers
        )
        
        return {
            'host': host,
            'timestamp': datetime.utcnow().isoformat(),
            'container_count': len(containers),
            'containers': [c.to_dict() for c in containers]
        }
        
    finally:
        inspector.disconnect()


def inspect_multiple_hosts(
    hosts: List[str],
    username: str,
    ssh_key_path: Optional[str] = None,
    ssh_timeout: int = 10,
    docker_timeout: int = 30,
    all_containers: bool = False
) -> Dict[str, Any]:
    """Inspect containers on multiple hosts.
    
    Args:
        hosts: List of target host IP addresses
        username: SSH username
        ssh_key_path: Path to SSH private key
        ssh_timeout: SSH connection timeout
        docker_timeout: Docker API timeout
        all_containers: Include stopped containers
    
    Returns:
        Dictionary with results for all hosts
    """
    results = {
        'timestamp': datetime.utcnow().isoformat(),
        'hosts': []
    }
    
    for host in hosts:
        try:
            logger.info(f"Processing host: {host}")
            host_data = inspect_host(
                host=host,
                username=username,
                ssh_key_path=ssh_key_path,
                ssh_timeout=ssh_timeout,
                docker_timeout=docker_timeout,
                all_containers=all_containers
            )
            results['hosts'].append(host_data)
            
        except (SSHConnectionError, DockerConnectionError, ContainerInspectionError) as e:
            logger.error(f"Failed to inspect {host}: {e}")
            results['hosts'].append({
                'host': host,
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            })
    
    return results
