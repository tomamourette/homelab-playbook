"""Git repository baseline configuration loader.

This module loads baseline configurations from git repositories (homelab-apps
and homelab-infra) to compare against running container states. It parses
Docker Compose files and handles endpoint-specific overrides.
"""

import os
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass
import yaml
import re
from dotenv import dotenv_values


# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


@dataclass
class GitBaselineConfig:
    """Baseline configuration from git repository.
    
    This structure mirrors ContainerInfo from docker_inspector.py for easy
    comparison.
    
    Attributes:
        name: Container/service name
        image: Image name and tag
        labels: Dictionary of container labels
        networks: List or dict of network configurations
        volumes: List of volume mounts
        environment: Dictionary of environment variables
        ports: Port mapping configuration
        stack_name: Name of the compose stack
        compose_file: Path to the source compose file
    """
    name: str
    image: str
    labels: Dict[str, str]
    networks: Any  # Can be list or dict depending on compose format
    volumes: List[Any]
    environment: Dict[str, str]
    ports: List[Any]
    stack_name: str
    compose_file: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'name': self.name,
            'image': self.image,
            'labels': self.labels,
            'networks': self.networks,
            'volumes': self.volumes,
            'environment': self.environment,
            'ports': self.ports,
            'stack_name': self.stack_name,
            'compose_file': self.compose_file
        }


class GitConfigError(Exception):
    """Base exception for git configuration loading errors."""
    pass


class ComposeFileNotFoundError(GitConfigError):
    """Raised when compose file is not found."""
    pass


class ComposeParseError(GitConfigError):
    """Raised when compose file parsing fails."""
    pass


class GitConfigLoader:
    """Load baseline configurations from git repositories.
    
    This class discovers and parses Docker Compose files from homelab-apps
    and homelab-infra repositories, handling endpoint-specific overrides
    and environment variable substitution.
    """
    
    def __init__(
        self,
        homelab_apps_path: str,
        homelab_infra_path: Optional[str] = None,
        endpoint: Optional[str] = None
    ) -> None:
        """Initialize git config loader.
        
        Args:
            homelab_apps_path: Path to homelab-apps repository
            homelab_infra_path: Path to homelab-infra repository (optional)
            endpoint: Endpoint name for loading endpoint-specific overrides
                     (e.g., 'ct-docker-01', 'ct-media-01')
        """
        self.homelab_apps_path = Path(homelab_apps_path)
        self.homelab_infra_path = Path(homelab_infra_path) if homelab_infra_path else None
        self.endpoint = endpoint
        
        logger.info(
            f"Initialized GitConfigLoader: apps={homelab_apps_path}, "
            f"infra={homelab_infra_path}, endpoint={endpoint}"
        )
    
    def discover_stacks(self) -> List[Path]:
        """Discover all stack directories in homelab-apps and homelab-infra.
        
        Returns:
            List of paths to stack directories
        
        Raises:
            GitConfigError: If repository paths are invalid
        """
        stacks = []
        
        # Check homelab-apps/stacks/*
        if not self.homelab_apps_path.exists():
            raise GitConfigError(
                f"homelab-apps path does not exist: {self.homelab_apps_path}"
            )
        
        apps_stacks_path = self.homelab_apps_path / "stacks"
        if apps_stacks_path.exists():
            for stack_dir in apps_stacks_path.iterdir():
                if stack_dir.is_dir():
                    # Check if docker-compose.yml exists
                    compose_file = stack_dir / "docker-compose.yml"
                    if compose_file.exists():
                        stacks.append(stack_dir)
                        logger.debug(f"Discovered stack: {stack_dir.name}")
        
        # Check homelab-infra (if provided)
        if self.homelab_infra_path and self.homelab_infra_path.exists():
            # homelab-infra might have stacks in root or subdirectories
            for item in self.homelab_infra_path.iterdir():
                if item.is_dir():
                    compose_file = item / "docker-compose.yml"
                    if compose_file.exists():
                        stacks.append(item)
                        logger.debug(f"Discovered infra stack: {item.name}")
        
        logger.info(f"Discovered {len(stacks)} stack(s)")
        return stacks
    
    def load_env_file(self, stack_path: Path) -> Dict[str, str]:
        """Load environment variables from .env file in stack directory.
        
        Args:
            stack_path: Path to stack directory
        
        Returns:
            Dictionary of environment variables
        """
        env_file = stack_path / ".env"
        env_vars = {}
        
        if env_file.exists():
            try:
                env_vars = dotenv_values(str(env_file))
                logger.debug(
                    f"Loaded {len(env_vars)} env var(s) from {env_file.name}"
                )
            except Exception as e:
                logger.warning(f"Failed to parse .env file {env_file}: {e}")
        
        # Also check for .env.sample as fallback
        env_sample = stack_path / ".env.sample"
        if not env_vars and env_sample.exists():
            try:
                env_vars = dotenv_values(str(env_sample))
                logger.debug(
                    f"Loaded {len(env_vars)} env var(s) from {env_sample.name}"
                )
            except Exception as e:
                logger.warning(f"Failed to parse .env.sample file {env_sample}: {e}")
        
        return {k: v for k, v in env_vars.items() if v is not None}
    
    def substitute_env_vars(
        self,
        data: Any,
        env_vars: Dict[str, str]
    ) -> Any:
        """Recursively substitute environment variables in data structure.
        
        Handles ${VAR} and ${VAR:-default} syntax.
        
        Args:
            data: Data structure (dict, list, or string)
            env_vars: Environment variables for substitution
        
        Returns:
            Data with substituted variables
        """
        if isinstance(data, dict):
            return {
                k: self.substitute_env_vars(v, env_vars)
                for k, v in data.items()
            }
        elif isinstance(data, list):
            return [self.substitute_env_vars(item, env_vars) for item in data]
        elif isinstance(data, str):
            # Handle ${VAR} and ${VAR:-default}
            def replacer(match):
                var_expr = match.group(1)
                if ':-' in var_expr:
                    var_name, default = var_expr.split(':-', 1)
                    return env_vars.get(var_name, default)
                else:
                    return env_vars.get(var_expr, match.group(0))
            
            return re.sub(r'\$\{([^}]+)\}', replacer, data)
        else:
            return data
    
    def load_compose_file(self, compose_path: Path) -> Dict[str, Any]:
        """Load and parse a Docker Compose file.
        
        Args:
            compose_path: Path to docker-compose.yml file
        
        Returns:
            Parsed compose file as dictionary
        
        Raises:
            ComposeFileNotFoundError: If file doesn't exist
            ComposeParseError: If YAML parsing fails
        """
        if not compose_path.exists():
            raise ComposeFileNotFoundError(
                f"Compose file not found: {compose_path}"
            )
        
        try:
            with open(compose_path, 'r') as f:
                data = yaml.safe_load(f)
            
            if not data:
                raise ComposeParseError(f"Empty compose file: {compose_path}")
            
            logger.debug(f"Loaded compose file: {compose_path.name}")
            return data
            
        except yaml.YAMLError as e:
            raise ComposeParseError(
                f"Failed to parse {compose_path}: {e}"
            )
        except Exception as e:
            raise ComposeParseError(
                f"Error reading {compose_path}: {e}"
            )
    
    def merge_compose_configs(
        self,
        base_config: Dict[str, Any],
        override_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Merge base and override compose configurations.
        
        Performs deep merge of compose files, with override taking precedence.
        
        Args:
            base_config: Base docker-compose.yml config
            override_config: Override config (e.g., docker-compose.ct-docker-01.yml)
        
        Returns:
            Merged configuration
        """
        def deep_merge(base: Any, override: Any) -> Any:
            """Recursively merge two data structures."""
            if isinstance(base, dict) and isinstance(override, dict):
                result = base.copy()
                for key, value in override.items():
                    if key in result:
                        result[key] = deep_merge(result[key], value)
                    else:
                        result[key] = value
                return result
            elif isinstance(base, list) and isinstance(override, list):
                # For lists, override replaces base
                return override
            else:
                # For primitives, override replaces base
                return override
        
        return deep_merge(base_config, override_config)
    
    def load_stack_config(self, stack_path: Path) -> Dict[str, Any]:
        """Load complete stack configuration with overrides and env substitution.
        
        Args:
            stack_path: Path to stack directory
        
        Returns:
            Complete merged and substituted compose configuration
        
        Raises:
            ComposeFileNotFoundError: If base compose file missing
            ComposeParseError: If parsing fails
        """
        # Load base docker-compose.yml
        base_compose = stack_path / "docker-compose.yml"
        config = self.load_compose_file(base_compose)
        
        # Load endpoint-specific override if it exists and endpoint is specified
        if self.endpoint:
            override_compose = stack_path / f"docker-compose.{self.endpoint}.yml"
            if override_compose.exists():
                logger.debug(
                    f"Loading endpoint override: {override_compose.name}"
                )
                override_config = self.load_compose_file(override_compose)
                config = self.merge_compose_configs(config, override_config)
        
        # Load environment variables
        env_vars = self.load_env_file(stack_path)
        
        # Substitute environment variables
        config = self.substitute_env_vars(config, env_vars)
        
        return config
    
    def parse_service_config(
        self,
        service_name: str,
        service_config: Dict[str, Any],
        stack_name: str,
        compose_file: str
    ) -> GitBaselineConfig:
        """Parse a single service configuration into GitBaselineConfig.
        
        Args:
            service_name: Name of the service
            service_config: Service configuration from compose file
            stack_name: Name of the stack
            compose_file: Path to compose file
        
        Returns:
            GitBaselineConfig object
        """
        # Extract image
        image = service_config.get('image', '')
        
        # Extract labels
        labels = service_config.get('labels', {})
        if isinstance(labels, list):
            # Convert list format to dict
            labels_dict = {}
            for label in labels:
                if '=' in label:
                    key, value = label.split('=', 1)
                    labels_dict[key] = value
            labels = labels_dict
        
        # Extract networks
        networks = service_config.get('networks', [])
        if isinstance(networks, dict):
            # Keep dict format (has additional config)
            pass
        elif isinstance(networks, list):
            # Keep list format
            pass
        
        # Extract volumes
        volumes = service_config.get('volumes', [])
        
        # Extract environment
        environment = {}
        env_config = service_config.get('environment', {})
        if isinstance(env_config, dict):
            environment = env_config
        elif isinstance(env_config, list):
            # Convert list format to dict
            for env_var in env_config:
                if '=' in env_var:
                    key, value = env_var.split('=', 1)
                    environment[key] = value
                else:
                    # Environment variable without value (will be set at runtime)
                    environment[env_var] = ''
        
        # Extract ports
        ports = service_config.get('ports', [])
        
        return GitBaselineConfig(
            name=service_name,
            image=image,
            labels=labels,
            networks=networks,
            volumes=volumes,
            environment=environment,
            ports=ports,
            stack_name=stack_name,
            compose_file=compose_file
        )
    
    def load_all_baselines(self) -> List[GitBaselineConfig]:
        """Load all baseline configurations from discovered stacks.
        
        Returns:
            List of GitBaselineConfig objects for all services
        
        Raises:
            GitConfigError: If loading fails
        """
        stacks = self.discover_stacks()
        baselines = []
        
        for stack_path in stacks:
            stack_name = stack_path.name
            
            try:
                logger.info(f"Loading stack: {stack_name}")
                config = self.load_stack_config(stack_path)
                
                # Extract services
                services = config.get('services', {})
                if not services:
                    logger.warning(f"No services found in stack: {stack_name}")
                    continue
                
                for service_name, service_config in services.items():
                    baseline = self.parse_service_config(
                        service_name=service_name,
                        service_config=service_config,
                        stack_name=stack_name,
                        compose_file=str(stack_path / "docker-compose.yml")
                    )
                    baselines.append(baseline)
                    logger.debug(
                        f"Parsed service: {stack_name}/{service_name}"
                    )
                
            except (ComposeFileNotFoundError, ComposeParseError) as e:
                logger.error(f"Failed to load stack {stack_name}: {e}")
                continue
            except Exception as e:
                logger.error(
                    f"Unexpected error loading stack {stack_name}: {e}",
                    exc_info=True
                )
                continue
        
        logger.info(
            f"Loaded {len(baselines)} baseline configuration(s) "
            f"from {len(stacks)} stack(s)"
        )
        
        return baselines
    
    def get_baseline_by_name(
        self,
        service_name: str,
        baselines: Optional[List[GitBaselineConfig]] = None
    ) -> Optional[GitBaselineConfig]:
        """Get baseline configuration for a specific service name.
        
        Args:
            service_name: Name of the service to find
            baselines: List of baselines to search (loads all if not provided)
        
        Returns:
            GitBaselineConfig if found, None otherwise
        """
        if baselines is None:
            baselines = self.load_all_baselines()
        
        for baseline in baselines:
            if baseline.name == service_name:
                return baseline
        
        return None


def load_git_baselines(
    homelab_apps_path: str,
    homelab_infra_path: Optional[str] = None,
    endpoint: Optional[str] = None
) -> Dict[str, Any]:
    """Convenience function to load all git baselines.
    
    Args:
        homelab_apps_path: Path to homelab-apps repository
        homelab_infra_path: Path to homelab-infra repository
        endpoint: Endpoint name for overrides
    
    Returns:
        Dictionary with baseline configurations
    """
    loader = GitConfigLoader(
        homelab_apps_path=homelab_apps_path,
        homelab_infra_path=homelab_infra_path,
        endpoint=endpoint
    )
    
    baselines = loader.load_all_baselines()
    
    return {
        'baselines': [b.to_dict() for b in baselines],
        'count': len(baselines),
        'endpoint': endpoint
    }
