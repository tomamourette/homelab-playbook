"""Example usage of git_config_loader module.

This script demonstrates how to load baseline configurations from
git repositories and compare them with running container states.
"""

import json
import logging
from pathlib import Path
from git_config_loader import GitConfigLoader, load_git_baselines
from config import load_config


# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


def example_basic_loading():
    """Example: Load all baselines from homelab-apps."""
    print("\n" + "="*60)
    print("Example 1: Basic Baseline Loading")
    print("="*60 + "\n")
    
    loader = GitConfigLoader(
        homelab_apps_path="../../../homelab-apps",
        homelab_infra_path=None,
        endpoint=None
    )
    
    baselines = loader.load_all_baselines()
    
    print(f"Loaded {len(baselines)} baseline configuration(s)\n")
    
    for baseline in baselines[:3]:  # Show first 3
        print(f"Stack: {baseline.stack_name}")
        print(f"  Service: {baseline.name}")
        print(f"  Image: {baseline.image}")
        print(f"  Labels: {len(baseline.labels)} label(s)")
        print(f"  Networks: {baseline.networks}")
        print()


def example_with_endpoint():
    """Example: Load baselines with endpoint-specific overrides."""
    print("\n" + "="*60)
    print("Example 2: Loading with Endpoint Overrides")
    print("="*60 + "\n")
    
    loader = GitConfigLoader(
        homelab_apps_path="../../../homelab-apps",
        homelab_infra_path="../../../homelab-infra",
        endpoint="ct-docker-01"
    )
    
    baselines = loader.load_all_baselines()
    
    print(f"Loaded {len(baselines)} baseline(s) for endpoint: ct-docker-01\n")
    
    # Find a specific service
    pihole = loader.get_baseline_by_name("pihole", baselines)
    if pihole:
        print(f"Found baseline for: {pihole.name}")
        print(f"  Image: {pihole.image}")
        print(f"  Stack: {pihole.stack_name}")
        print(f"  Ports: {pihole.ports}")
        print()


def example_convenience_function():
    """Example: Using convenience function."""
    print("\n" + "="*60)
    print("Example 3: Using Convenience Function")
    print("="*60 + "\n")
    
    result = load_git_baselines(
        homelab_apps_path="../../../homelab-apps",
        homelab_infra_path="../../../homelab-infra",
        endpoint="ct-docker-01"
    )
    
    print(f"Total baselines: {result['count']}")
    print(f"Endpoint: {result['endpoint']}")
    print()
    
    # Show first baseline
    if result['baselines']:
        first = result['baselines'][0]
        print(f"First baseline: {first['stack_name']}/{first['name']}")
        print(f"Image: {first['image']}")


def example_stack_discovery():
    """Example: Discover available stacks."""
    print("\n" + "="*60)
    print("Example 4: Stack Discovery")
    print("="*60 + "\n")
    
    loader = GitConfigLoader(
        homelab_apps_path="../../../homelab-apps",
        homelab_infra_path="../../../homelab-infra"
    )
    
    stacks = loader.discover_stacks()
    
    print(f"Discovered {len(stacks)} stack(s):\n")
    for stack in stacks:
        print(f"  - {stack.name}")
        compose_file = stack / "docker-compose.yml"
        if compose_file.exists():
            print(f"    └─ {compose_file.name}")


def example_env_substitution():
    """Example: Show environment variable substitution."""
    print("\n" + "="*60)
    print("Example 5: Environment Variable Substitution")
    print("="*60 + "\n")
    
    loader = GitConfigLoader(
        homelab_apps_path="../../../homelab-apps"
    )
    
    # Load a specific stack
    stack_path = Path("../../../homelab-apps/stacks/dns-pihole")
    if stack_path.exists():
        env_vars = loader.load_env_file(stack_path)
        print(f"Loaded {len(env_vars)} environment variable(s):\n")
        
        for key, value in list(env_vars.items())[:5]:  # Show first 5
            print(f"  {key}={value}")
        
        print("\nLoading stack with substitution...")
        config = loader.load_stack_config(stack_path)
        
        services = config.get('services', {})
        if 'pihole' in services:
            pihole_service = services['pihole']
            print(f"\nPihole service image: {pihole_service.get('image')}")
            print(f"Environment vars: {len(pihole_service.get('environment', []))}")


def example_with_config():
    """Example: Load baselines using config from .env file."""
    print("\n" + "="*60)
    print("Example 6: Loading with Configuration File")
    print("="*60 + "\n")
    
    try:
        config = load_config()
        
        loader = GitConfigLoader(
            homelab_apps_path=config.homelab_apps_path,
            homelab_infra_path=config.homelab_infra_path,
            endpoint=config.endpoint
        )
        
        baselines = loader.load_all_baselines()
        
        print(f"Loaded {len(baselines)} baseline(s) from config\n")
        print(f"Config:")
        print(f"  Apps path: {config.homelab_apps_path}")
        print(f"  Infra path: {config.homelab_infra_path}")
        print(f"  Endpoint: {config.endpoint}")
        
    except ValueError as e:
        print(f"Config validation failed: {e}")
        print("Ensure .env file is configured correctly")


def example_json_export():
    """Example: Export baselines to JSON."""
    print("\n" + "="*60)
    print("Example 7: Export to JSON")
    print("="*60 + "\n")
    
    result = load_git_baselines(
        homelab_apps_path="../../../homelab-apps",
        endpoint=None
    )
    
    output_file = "git_baselines.json"
    with open(output_file, 'w') as f:
        json.dump(result, f, indent=2)
    
    print(f"Exported {result['count']} baseline(s) to {output_file}")


if __name__ == "__main__":
    print("\n" + "="*60)
    print("Git Config Loader - Example Usage")
    print("="*60)
    
    # Run examples (uncomment the ones you want to try)
    
    example_basic_loading()
    example_with_endpoint()
    example_convenience_function()
    example_stack_discovery()
    example_env_substitution()
    # example_with_config()  # Requires .env configuration
    example_json_export()
    
    print("\n" + "="*60)
    print("Examples complete!")
    print("="*60 + "\n")
