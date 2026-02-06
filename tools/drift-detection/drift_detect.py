#!/usr/bin/env python3
"""Complete drift detection workflow.

This script orchestrates the full drift detection process:
1. Load configuration from .env
2. Connect to target hosts and inspect running containers
3. Load git baseline configurations
4. Compare and identify drift
5. Generate report (JSON and optionally Markdown)
"""

import sys
import json
import logging
import argparse
from pathlib import Path
from typing import Dict, Any

from config import load_config
from docker_inspector import DockerInspector
from git_config_loader import GitConfigLoader
from drift_comparator import DriftComparator
from drift_report_generator import DriftReportGenerator


# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


def inspect_running_containers(config) -> list:
    """Inspect running containers on all target hosts.
    
    Args:
        config: Configuration object
    
    Returns:
        List of ContainerInfo objects
    """
    all_containers = []
    
    for host in config.target_hosts:
        logger.info(f"Inspecting containers on {host}...")
        
        inspector = DockerInspector(
            host=host,
            username=config.ssh_username,
            ssh_key_path=config.ssh_key_path,
            ssh_timeout=config.ssh_timeout,
            docker_timeout=config.docker_timeout
        )
        
        try:
            # Connect
            inspector.connect()
            inspector.connect_docker()
            
            # List and inspect all containers
            containers = inspector.inspect_all_containers()
            all_containers.extend(containers)
            
            logger.info(f"Found {len(containers)} container(s) on {host}")
            
        except Exception as e:
            logger.error(f"Failed to inspect {host}: {e}")
        finally:
            inspector.disconnect()
    
    return all_containers


def load_baselines(config) -> list:
    """Load git baseline configurations.
    
    Args:
        config: Configuration object
    
    Returns:
        List of GitBaselineConfig objects
    """
    logger.info("Loading git baselines...")
    
    loader = GitConfigLoader(
        homelab_apps_path=config.homelab_apps_path,
        homelab_infra_path=config.homelab_infra_path,
        endpoint=config.endpoint
    )
    
    baselines = loader.load_all_baselines()
    logger.info(f"Loaded {len(baselines)} baseline configuration(s)")
    
    return baselines


def perform_drift_analysis(running_containers: list, git_baselines: list) -> Dict[str, Any]:
    """Perform drift comparison analysis.
    
    Args:
        running_containers: List of ContainerInfo objects
        git_baselines: List of GitBaselineConfig objects
    
    Returns:
        Drift report dictionary
    """
    logger.info("Performing drift analysis...")
    
    comparator = DriftComparator()
    report = comparator.compare_configurations(running_containers, git_baselines)
    
    return report.to_dict()


def save_report(report: Dict[str, Any], output_dir: Path, format: str = 'json'):
    """Save drift report to file.
    
    Args:
        report: Drift report dictionary
        output_dir: Output directory path
        format: Output format ('json', 'markdown', or 'both')
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = report['timestamp'].replace(':', '-').split('.')[0]
    
    if format == 'json' or format == 'both':
        json_file = output_dir / f"drift-report-{timestamp}.json"
        with open(json_file, 'w') as f:
            json.dump(report, f, indent=2)
        logger.info(f"Saved JSON report to {json_file}")
    
    if format == 'markdown' or format == 'both':
        markdown_file = output_dir / f"drift-{timestamp}.md"
        generator = DriftReportGenerator()
        generator.save_markdown_report(report, output_dir, markdown_file.name)
        logger.info(f"Saved Markdown report to {markdown_file}")


def main():
    """Main drift detection workflow."""
    parser = argparse.ArgumentParser(
        description='Detect configuration drift between running containers and git baselines'
    )
    parser.add_argument(
        '--config',
        help='Path to .env config file',
        default=None
    )
    parser.add_argument(
        '--output-dir',
        help='Output directory for reports',
        default='./output'
    )
    parser.add_argument(
        '--format',
        choices=['json', 'markdown', 'both'],
        default='json',
        help='Report output format'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        # Load configuration
        logger.info("Loading configuration...")
        config = load_config(env_file=args.config)
        logger.info(f"Loaded config: {config}")
        
        # Inspect running containers
        logger.info("=== Step 1: Inspect Running Containers ===")
        running_containers = inspect_running_containers(config)
        
        if not running_containers:
            logger.error("No running containers found!")
            sys.exit(1)
        
        logger.info(f"Total running containers: {len(running_containers)}")
        
        # Load git baselines
        logger.info("=== Step 2: Load Git Baselines ===")
        git_baselines = load_baselines(config)
        
        if not git_baselines:
            logger.error("No git baselines found!")
            sys.exit(1)
        
        # Perform drift analysis
        logger.info("=== Step 3: Perform Drift Analysis ===")
        drift_report = perform_drift_analysis(running_containers, git_baselines)
        
        # Display summary
        logger.info("=== Drift Analysis Summary ===")
        logger.info(f"Services analyzed: {drift_report['services_analyzed']}")
        logger.info(f"Services with drift: {drift_report['services_with_drift']}")
        logger.info(f"Total drift items: {drift_report['total_drift_items']}")
        
        severity_summary = drift_report['severity_summary']
        logger.info(f"Breaking: {severity_summary['breaking']}")
        logger.info(f"Functional: {severity_summary['functional']}")
        logger.info(f"Cosmetic: {severity_summary['cosmetic']}")
        logger.info(f"Informational: {severity_summary['informational']}")
        
        if drift_report['breaking_services'] > 0:
            logger.warning(
                f"⚠️  {drift_report['breaking_services']} service(s) have BREAKING drift!"
            )
        
        # Save report
        logger.info("=== Step 4: Save Report ===")
        output_dir = Path(args.output_dir)
        save_report(drift_report, output_dir, format=args.format)
        
        logger.info("✅ Drift detection complete!")
        
        # Exit with non-zero if drift detected
        if drift_report['services_with_drift'] > 0:
            sys.exit(1)
        
    except Exception as e:
        logger.error(f"Drift detection failed: {e}", exc_info=True)
        sys.exit(2)


if __name__ == '__main__':
    main()
