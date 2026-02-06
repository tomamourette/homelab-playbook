#!/usr/bin/env python3
"""
Drift Remediation CLI

End-to-end workflow for detecting drift and generating remediation PRs.

Usage:
    python drift_remediate.py detect --output drift-report.json
    python drift_remediate.py remediate --report drift-report.json --repo /path/to/homelab-apps
    python drift_remediate.py full --repo /path/to/homelab-apps --dry-run
"""

import argparse
import sys
import json
from pathlib import Path
from typing import Optional

from config import Config
from docker_inspector import DockerInspector
from git_config_loader import GitConfigLoader
from drift_comparator import DriftComparator
from drift_report_generator import DriftReportGenerator
from pr_generator import PRGenerator, DriftItem


def detect_drift(output_path: Optional[Path] = None) -> dict:
    """
    Detect configuration drift
    
    Args:
        output_path: Optional path to save drift report JSON
        
    Returns:
        Drift report data as dict
    """
    print("🔍 Starting drift detection...")
    
    # Load config
    config = Config()
    
    # Connect to hosts and inspect containers
    print("\n📡 Connecting to hosts...")
    inspector = DockerInspector(config)
    
    running_configs = {}
    for endpoint_name, endpoint_config in config.endpoints.items():
        print(f"  Inspecting {endpoint_name} ({endpoint_config.hostname})...")
        try:
            containers = inspector.inspect_endpoint(endpoint_name)
            running_configs[endpoint_name] = containers
            print(f"    ✅ Found {len(containers)} containers")
        except Exception as e:
            print(f"    ❌ Failed: {e}")
    
    # Load git baselines
    print("\n📚 Loading git baselines...")
    git_loader = GitConfigLoader(config.apps_repo_path)
    baselines = git_loader.load_all_baselines()
    print(f"  ✅ Loaded {len(baselines)} baseline configurations")
    
    # Compare and detect drift
    print("\n🔬 Comparing configurations...")
    comparator = DriftComparator()
    
    all_drifts = []
    for endpoint_name, containers in running_configs.items():
        for container_name, running_config in containers.items():
            # Find matching baseline
            baseline = None
            for b in baselines:
                if b.service_name == container_name or container_name.startswith(b.service_name):
                    baseline = b
                    break
            
            if not baseline:
                print(f"  ⚠️  No baseline found for {container_name}")
                continue
            
            # Compare
            drifts = comparator.compare(running_config, baseline.config)
            if drifts:
                all_drifts.append({
                    "service_name": container_name,
                    "stack_name": baseline.stack_name,
                    "compose_file": str(baseline.compose_file),
                    "drift_items": [
                        {
                            "field_path": d.field_path,
                            "running_value": d.running_value,
                            "git_value": d.git_value,
                            "severity": d.severity.name
                        }
                        for d in drifts
                    ]
                })
                print(f"  🔴 Drift detected in {container_name}: {len(drifts)} items")
    
    # Generate report
    print("\n📊 Generating drift report...")
    report_data = {
        "timestamp": config.timestamp,
        "total_services_inspected": sum(len(c) for c in running_configs.values()),
        "services_with_drift": len(all_drifts),
        "total_drift_items": sum(len(s["drift_items"]) for s in all_drifts),
        "services": all_drifts
    }
    
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(report_data, f, indent=2)
        print(f"  ✅ Saved to {output_path}")
    
    # Summary
    print("\n" + "=" * 60)
    print("DRIFT DETECTION SUMMARY")
    print("=" * 60)
    print(f"Total services inspected: {report_data['total_services_inspected']}")
    print(f"Services with drift: {report_data['services_with_drift']}")
    print(f"Total drift items: {report_data['total_drift_items']}")
    
    if report_data['services_with_drift'] > 0:
        print("\n⚠️  Configuration drift detected!")
        print("Run remediation to generate PRs:")
        print(f"  python drift_remediate.py remediate --report {output_path} --repo /path/to/homelab-apps")
    else:
        print("\n✅ No drift detected - infrastructure matches git!")
    
    return report_data


def remediate_drift(report_path: Path, repo_path: Path, dry_run: bool = False) -> None:
    """
    Generate remediation PRs from drift report
    
    Args:
        report_path: Path to drift report JSON
        repo_path: Path to target git repository
        dry_run: If True, don't actually create PRs
    """
    print("🔧 Starting drift remediation...")
    
    if not report_path.exists():
        print(f"❌ Drift report not found: {report_path}")
        sys.exit(1)
    
    with open(report_path, 'r') as f:
        drift_data = json.load(f)
    
    services_with_drift = drift_data.get("services", [])
    
    if not services_with_drift:
        print("✅ No drift to remediate!")
        return
    
    print(f"\n📋 Found {len(services_with_drift)} services with drift")
    
    # Initialize PR generator
    generator = PRGenerator(repo_path=repo_path, dry_run=dry_run)
    
    # Generate PRs
    pr_results = {}
    for service_drift in services_with_drift:
        service_name = service_drift["service_name"]
        stack_name = service_drift["stack_name"]
        compose_file = Path(service_drift["compose_file"])
        
        print(f"\n🔨 Processing {service_name} ({stack_name})...")
        
        # Convert drift items
        drift_items = [
            DriftItem(
                service_name=service_name,
                stack_name=stack_name,
                field_path=item["field_path"],
                running_value=item["running_value"],
                git_value=item["git_value"],
                severity=item["severity"]
            )
            for item in service_drift.get("drift_items", [])
        ]
        
        try:
            pr_url = generator.generate_pr_for_service(
                service_name=service_name,
                stack_name=stack_name,
                drift_items=drift_items,
                compose_file_path=compose_file
            )
            pr_results[service_name] = pr_url
        except Exception as e:
            print(f"  ❌ Failed: {e}")
            pr_results[service_name] = None
    
    # Summary
    print("\n" + "=" * 60)
    print("REMEDIATION SUMMARY")
    print("=" * 60)
    
    successful = sum(1 for url in pr_results.values() if url)
    failed = len(pr_results) - successful
    
    print(f"PRs created: {successful}")
    print(f"Failed: {failed}")
    
    if successful > 0:
        print("\n✅ Successfully created PRs:")
        for service, url in pr_results.items():
            if url:
                print(f"  - {service}: {url}")
    
    if failed > 0:
        print("\n❌ Failed to create PRs for:")
        for service, url in pr_results.items():
            if not url:
                print(f"  - {service}")


def full_workflow(repo_path: Path, dry_run: bool = False) -> None:
    """
    Run full drift detection + remediation workflow
    
    Args:
        repo_path: Path to target git repository
        dry_run: If True, don't actually create PRs
    """
    # Detect drift
    temp_report = Path("/tmp/drift-report.json")
    drift_data = detect_drift(output_path=temp_report)
    
    # If drift found, remediate
    if drift_data["services_with_drift"] > 0:
        print("\n" + "=" * 60)
        remediate_drift(temp_report, repo_path, dry_run=dry_run)
    
    # Cleanup temp file
    if temp_report.exists():
        temp_report.unlink()


def main():
    parser = argparse.ArgumentParser(
        description="Drift detection and remediation tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Detect drift only
  python drift_remediate.py detect --output drift-report.json
  
  # Generate remediation PRs from existing report
  python drift_remediate.py remediate --report drift-report.json --repo /path/to/homelab-apps
  
  # Full workflow (detect + remediate)
  python drift_remediate.py full --repo /path/to/homelab-apps --dry-run
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Detect command
    detect_parser = subparsers.add_parser("detect", help="Detect configuration drift")
    detect_parser.add_argument(
        "--output", "-o",
        type=Path,
        default=Path("drift-report.json"),
        help="Output path for drift report (default: drift-report.json)"
    )
    
    # Remediate command
    remediate_parser = subparsers.add_parser("remediate", help="Generate remediation PRs")
    remediate_parser.add_argument(
        "--report", "-r",
        type=Path,
        required=True,
        help="Path to drift report JSON"
    )
    remediate_parser.add_argument(
        "--repo",
        type=Path,
        required=True,
        help="Path to target git repository"
    )
    remediate_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Don't actually create PRs, just show what would be done"
    )
    
    # Full command
    full_parser = subparsers.add_parser("full", help="Run full workflow (detect + remediate)")
    full_parser.add_argument(
        "--repo",
        type=Path,
        required=True,
        help="Path to target git repository"
    )
    full_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Don't actually create PRs, just show what would be done"
    )
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    if args.command == "detect":
        detect_drift(output_path=args.output)
    elif args.command == "remediate":
        remediate_drift(args.report, args.repo, dry_run=args.dry_run)
    elif args.command == "full":
        full_workflow(args.repo, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
