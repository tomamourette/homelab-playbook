#!/usr/bin/env python3
"""Example usage of the drift detection docker inspector.

This script demonstrates how to use the docker_inspector module to
connect to remote hosts and extract container configurations.
"""

import json
import logging
from pathlib import Path

from config import load_config
from docker_inspector import (
    inspect_host,
    inspect_multiple_hosts,
    DockerInspector,
    SSHConnectionError,
    DockerConnectionError,
    ContainerInspectionError
)


def example_single_host():
    """Example: Inspect containers on a single host."""
    print("\n=== Example 1: Single Host Inspection ===\n")
    
    host = "192.168.50.19"
    username = "root"
    ssh_key_path = "~/.ssh/id_rsa"
    
    try:
        result = inspect_host(
            host=host,
            username=username,
            ssh_key_path=ssh_key_path,
            all_containers=False  # Only running containers
        )
        
        print(f"Host: {result['host']}")
        print(f"Containers found: {result['container_count']}")
        print(f"Timestamp: {result['timestamp']}\n")
        
        for container in result['containers']:
            print(f"  - {container['name']} ({container['image']})")
            print(f"    Status: {container['status']}")
            print(f"    ID: {container['container_id'][:12]}")
            if container['labels']:
                print(f"    Labels: {len(container['labels'])} label(s)")
            print()
        
    except (SSHConnectionError, DockerConnectionError, ContainerInspectionError) as e:
        print(f"Error: {e}")


def example_multiple_hosts():
    """Example: Inspect containers on multiple hosts."""
    print("\n=== Example 2: Multiple Hosts Inspection ===\n")
    
    hosts = ["192.168.50.19", "192.168.50.161"]
    username = "root"
    ssh_key_path = "~/.ssh/id_rsa"
    
    results = inspect_multiple_hosts(
        hosts=hosts,
        username=username,
        ssh_key_path=ssh_key_path
    )
    
    print(f"Inspection timestamp: {results['timestamp']}\n")
    
    for host_data in results['hosts']:
        if 'error' in host_data:
            print(f"Host: {host_data['host']} - FAILED")
            print(f"  Error: {host_data['error']}\n")
        else:
            print(f"Host: {host_data['host']} - SUCCESS")
            print(f"  Containers: {host_data['container_count']}\n")


def example_context_manager():
    """Example: Using DockerInspector with context manager."""
    print("\n=== Example 3: Context Manager Usage ===\n")
    
    host = "192.168.50.19"
    username = "root"
    ssh_key_path = "~/.ssh/id_rsa"
    
    try:
        with DockerInspector(
            host=host,
            username=username,
            ssh_key_path=ssh_key_path
        ) as inspector:
            # List containers
            container_ids = inspector.list_containers()
            print(f"Found {len(container_ids)} container(s)\n")
            
            # Inspect each container
            for cid in container_ids:
                info = inspector.inspect_container(cid)
                print(f"Container: {info.name}")
                print(f"  Image: {info.image}")
                print(f"  Status: {info.status}")
                print(f"  Networks: {', '.join(info.networks.keys())}")
                print(f"  Volumes: {len(info.volumes)} volume(s)")
                print(f"  Environment vars: {len(info.environment)}")
                print()
        
    except (SSHConnectionError, DockerConnectionError, ContainerInspectionError) as e:
        print(f"Error: {e}")


def example_with_config():
    """Example: Load configuration from .env file."""
    print("\n=== Example 4: Using Configuration File ===\n")
    
    try:
        # Load configuration
        config = load_config()
        print(f"Configuration loaded: {config}\n")
        
        # Inspect all configured hosts
        results = inspect_multiple_hosts(
            hosts=config.target_hosts,
            username=config.ssh_username,
            ssh_key_path=config.ssh_key_path,
            ssh_timeout=config.ssh_timeout,
            docker_timeout=config.docker_timeout
        )
        
        # Save results to file
        output_dir = Path(config.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        output_file = output_dir / "container_inspection.json"
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"Results saved to: {output_file}")
        print(f"Total hosts inspected: {len(results['hosts'])}")
        
        # Count total containers across all hosts
        total_containers = sum(
            host_data.get('container_count', 0)
            for host_data in results['hosts']
            if 'container_count' in host_data
        )
        print(f"Total containers found: {total_containers}")
        
    except ValueError as e:
        print(f"Configuration error: {e}")
    except Exception as e:
        print(f"Error: {e}")


def main():
    """Run all examples."""
    # Set logging level
    logging.basicConfig(level=logging.INFO)
    
    print("=" * 60)
    print("Docker Inspector - Example Usage")
    print("=" * 60)
    
    # Note: These examples will fail if hosts are not reachable
    # Uncomment the examples you want to run:
    
    # example_single_host()
    # example_multiple_hosts()
    # example_context_manager()
    
    # This one requires a .env file:
    # example_with_config()
    
    print("\nNote: Uncomment examples in main() to run them.")
    print("Make sure you have:")
    print("  1. SSH access configured to target hosts")
    print("  2. Created a .env file (copy from .env.sample)")
    print("  3. Installed requirements: pip install -r requirements.txt")


if __name__ == '__main__':
    main()
