"""Configuration management for drift detection tool.

This module loads and validates configuration from environment variables
and .env files using python-dotenv.
"""

import os
from pathlib import Path
from typing import List, Optional
from dotenv import load_dotenv


class Config:
    """Configuration settings for the drift detection tool.
    
    Attributes:
        ssh_key_path: Path to SSH private key file
        target_hosts: List of target host IP addresses
        ssh_username: Username for SSH connections
        ssh_timeout: SSH connection timeout in seconds
        docker_timeout: Docker API timeout in seconds
        output_format: Format for output data (json, yaml)
        output_dir: Directory for output files
        log_level: Logging level
    """
    
    def __init__(self, env_file: Optional[str] = None) -> None:
        """Initialize configuration by loading from environment.
        
        Args:
            env_file: Optional path to .env file. If not provided, searches for
                     .env in current directory and parent directories.
        """
        # Load environment variables from .env file
        if env_file:
            load_dotenv(dotenv_path=env_file)
        else:
            load_dotenv()
        
        # SSH Configuration
        self.ssh_key_path: Optional[str] = os.getenv('SSH_KEY_PATH')
        if self.ssh_key_path:
            self.ssh_key_path = os.path.expanduser(self.ssh_key_path)
        
        # Target hosts
        hosts_str = os.getenv('TARGET_HOSTS', '')
        self.target_hosts: List[str] = [
            host.strip() for host in hosts_str.split(',') if host.strip()
        ]
        
        # SSH settings
        self.ssh_username: str = os.getenv('SSH_USERNAME', 'root')
        self.ssh_timeout: int = int(os.getenv('SSH_TIMEOUT', '10'))
        
        # Docker settings
        self.docker_timeout: int = int(os.getenv('DOCKER_TIMEOUT', '30'))
        
        # Output settings
        self.output_format: str = os.getenv('OUTPUT_FORMAT', 'json')
        self.output_dir: str = os.getenv('OUTPUT_DIR', './output')
        
        # Logging
        self.log_level: str = os.getenv('LOG_LEVEL', 'INFO')
    
    def validate(self) -> None:
        """Validate configuration settings.
        
        Raises:
            ValueError: If required configuration is missing or invalid
        """
        if not self.target_hosts:
            raise ValueError("TARGET_HOSTS must be specified")
        
        if self.ssh_key_path and not Path(self.ssh_key_path).exists():
            raise ValueError(f"SSH key not found: {self.ssh_key_path}")
        
        if self.ssh_timeout <= 0:
            raise ValueError("SSH_TIMEOUT must be positive")
        
        if self.docker_timeout <= 0:
            raise ValueError("DOCKER_TIMEOUT must be positive")
        
        if self.output_format not in ['json', 'yaml']:
            raise ValueError("OUTPUT_FORMAT must be 'json' or 'yaml'")
    
    def __repr__(self) -> str:
        """Return string representation of configuration."""
        return (
            f"Config(target_hosts={self.target_hosts}, "
            f"ssh_username={self.ssh_username}, "
            f"ssh_timeout={self.ssh_timeout}s, "
            f"docker_timeout={self.docker_timeout}s)"
        )


def load_config(env_file: Optional[str] = None) -> Config:
    """Load and validate configuration.
    
    Args:
        env_file: Optional path to .env file
    
    Returns:
        Validated Config object
    
    Raises:
        ValueError: If configuration is invalid
    """
    config = Config(env_file=env_file)
    config.validate()
    return config
