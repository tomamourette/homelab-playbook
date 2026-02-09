#!/usr/bin/env python3
"""Configuration Audit Trail Viewer.

CLI tool that parses git logs from homelab-infra and homelab-apps repositories
to display a chronological history of configuration changes. Supports filtering
by date range, author, repository, and file type.

Usage:
    python3 audit_viewer.py
    python3 audit_viewer.py --since "2 weeks ago" --repo homelab-apps
    python3 audit_viewer.py --format json --output audit-report.json
    python3 audit_viewer.py --author "Larry" --config-only
"""

import argparse
import json
import logging
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime
from fnmatch import fnmatch
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
import os

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# File patterns considered as configuration files
DEFAULT_CONFIG_PATTERNS: List[str] = [
    "*.yml",
    "*.yaml",
    "*.env",
    "*.env.*",
    "*.conf",
    "*.cfg",
    "*.toml",
    "*.ini",
    "*.json",
    "*.tf",
    "*.tfvars",
    "docker-compose*",
    "Dockerfile*",
    "*.hcl",
]


class Config:
    """Configuration settings for the audit trail viewer.

    Attributes:
        homelab_apps_path: Path to homelab-apps repository.
        homelab_infra_path: Path to homelab-infra repository.
        max_entries: Maximum log entries to display.
        log_level: Logging verbosity level.
        config_patterns: Glob patterns for config file matching.
    """

    def __init__(self, env_file: Optional[str] = None) -> None:
        """Initialize configuration from environment.

        Args:
            env_file: Optional path to .env file.
        """
        if env_file:
            load_dotenv(dotenv_path=env_file)
        else:
            load_dotenv()

        self.homelab_apps_path: str = os.path.expanduser(
            os.getenv("HOMELAB_APPS_PATH", "/root/.openclaw/workspace/homelab-apps")
        )
        self.homelab_infra_path: str = os.path.expanduser(
            os.getenv("HOMELAB_INFRA_PATH", "/root/.openclaw/workspace/homelab-infra")
        )
        self.max_entries: int = int(os.getenv("AUDIT_MAX_ENTRIES", "100"))
        self.log_level: str = os.getenv("LOG_LEVEL", "INFO")

        patterns_str = os.getenv("AUDIT_CONFIG_PATTERNS", "")
        if patterns_str.strip():
            self.config_patterns: List[str] = [
                p.strip() for p in patterns_str.split(",") if p.strip()
            ]
        else:
            self.config_patterns = DEFAULT_CONFIG_PATTERNS

    @property
    def repo_paths(self) -> List[str]:
        """Return list of configured repository paths."""
        paths = []
        if self.homelab_apps_path:
            paths.append(self.homelab_apps_path)
        if self.homelab_infra_path:
            paths.append(self.homelab_infra_path)
        return paths

    def validate(self) -> List[str]:
        """Validate config and return warnings for missing repos.

        Returns:
            List of warning messages.

        Raises:
            ValueError: If no valid repositories are configured.
        """
        warnings: List[str] = []
        valid_repos = []
        for path in self.repo_paths:
            repo = Path(path)
            if not repo.exists():
                warnings.append(f"Repository not found: {path}")
            elif not (repo / ".git").exists():
                warnings.append(f"Not a git repository: {path}")
            else:
                valid_repos.append(path)

        if not valid_repos:
            raise ValueError(
                "No valid git repositories configured. "
                "Set HOMELAB_APPS_PATH and/or HOMELAB_INFRA_PATH."
            )
        if self.max_entries <= 0:
            raise ValueError("AUDIT_MAX_ENTRIES must be positive")
        return warnings

    def __repr__(self) -> str:
        return f"Config(repos={self.repo_paths}, max_entries={self.max_entries})"


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------


class GitLogError(Exception):
    """Raised when git log parsing fails."""

    pass


@dataclass
class FileChange:
    """A single file changed in a commit.

    Attributes:
        status: Git status code (A/M/D/R).
        path: File path relative to repository root.
        old_path: Previous path for renamed files.
    """

    status: str
    path: str
    old_path: Optional[str] = None

    @property
    def status_label(self) -> str:
        """Human-readable status label."""
        labels = {"A": "added", "M": "modified", "D": "deleted", "R": "renamed", "C": "copied"}
        return labels.get(self.status[0], self.status)

    def to_dict(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "status": self.status,
            "status_label": self.status_label,
            "path": self.path,
        }
        if self.old_path:
            result["old_path"] = self.old_path
        return result


@dataclass
class AuditEntry:
    """A single configuration change event from git history.

    Attributes:
        commit_hash: Full git commit SHA.
        short_hash: Abbreviated commit SHA.
        author: Commit author name.
        email: Author email address.
        timestamp: Commit datetime.
        subject: Commit subject line.
        body: Full commit message body.
        repo_name: Name of the source repository.
        repo_path: Filesystem path to the repository.
        files_changed: Config files changed in this commit.
    """

    commit_hash: str
    short_hash: str
    author: str
    email: str
    timestamp: datetime
    subject: str
    body: str
    repo_name: str
    repo_path: str
    files_changed: List[FileChange] = field(default_factory=list)

    @property
    def is_config_change(self) -> bool:
        return len(self.files_changed) > 0

    @property
    def change_type(self) -> str:
        """Infer type from conventional commit prefix."""
        s = self.subject.lower()
        for prefix in ("feat", "fix", "refactor", "docs", "chore", "ci", "test"):
            if s.startswith(prefix):
                return prefix if prefix != "feat" else "feature"
        return "other"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "commit_hash": self.commit_hash,
            "short_hash": self.short_hash,
            "author": self.author,
            "email": self.email,
            "timestamp": self.timestamp.isoformat(),
            "subject": self.subject,
            "body": self.body,
            "repo_name": self.repo_name,
            "change_type": self.change_type,
            "files_changed": [f.to_dict() for f in self.files_changed],
        }


# ---------------------------------------------------------------------------
# Git Log Parser
# ---------------------------------------------------------------------------


class GitLogParser:
    """Parse git log output into structured audit trail entries."""

    FIELD_SEP = "---FIELD---"
    RECORD_SEP = "---RECORD---"

    def __init__(self, config_patterns: Optional[List[str]] = None) -> None:
        self.config_patterns = config_patterns

    def _is_config_file(self, filepath: str) -> bool:
        if not self.config_patterns:
            return True
        filename = Path(filepath).name
        for pattern in self.config_patterns:
            if fnmatch(filename, pattern) or fnmatch(filepath, pattern):
                return True
        return False

    def _parse_file_changes(self, name_status_output: str) -> List[FileChange]:
        changes: List[FileChange] = []
        for line in name_status_output.strip().split("\n"):
            line = line.strip()
            if not line:
                continue
            parts = line.split("\t")
            if len(parts) < 2:
                continue
            status = parts[0]
            filepath = parts[-1]
            old_path = parts[1] if len(parts) == 3 else None
            if self._is_config_file(filepath):
                changes.append(FileChange(status=status, path=filepath, old_path=old_path))
        return changes

    def parse_repo(
        self,
        repo_path: str,
        max_entries: int = 100,
        since: Optional[str] = None,
        until: Optional[str] = None,
        author: Optional[str] = None,
        path_filter: Optional[str] = None,
    ) -> List[AuditEntry]:
        """Parse git log from a repository into audit entries.

        Args:
            repo_path: Filesystem path to the git repository.
            max_entries: Maximum commits to retrieve.
            since: Git --since date filter.
            until: Git --until date filter.
            author: Filter by author name or email.
            path_filter: Only show commits affecting this path.

        Returns:
            List of AuditEntry objects, newest first.

        Raises:
            GitLogError: If git command fails.
        """
        repo_path_obj = Path(repo_path)
        if not repo_path_obj.exists():
            raise GitLogError(f"Repository path does not exist: {repo_path}")
        repo_name = repo_path_obj.name

        log_format = self.FIELD_SEP.join(["%H", "%h", "%an", "%ae", "%aI", "%s", "%b"])
        log_format = f"{self.RECORD_SEP}{log_format}"

        cmd = [
            "git", "-C", str(repo_path),
            "log",
            f"--max-count={max_entries}",
            f"--format={log_format}",
            "--name-status",
        ]
        if since:
            cmd.append(f"--since={since}")
        if until:
            cmd.append(f"--until={until}")
        if author:
            cmd.append(f"--author={author}")
        if path_filter:
            cmd.extend(["--", path_filter])

        logger.info(f"Parsing git log for {repo_name}")

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        except subprocess.TimeoutExpired:
            raise GitLogError(f"Git log timed out for {repo_name}")
        except FileNotFoundError:
            raise GitLogError("git executable not found in PATH")

        if result.returncode != 0:
            raise GitLogError(f"git log failed for {repo_name}: {result.stderr.strip()}")

        return self._parse_log_output(result.stdout, repo_name, str(repo_path))

    def _parse_log_output(
        self, raw_output: str, repo_name: str, repo_path: str
    ) -> List[AuditEntry]:
        entries: List[AuditEntry] = []
        records = raw_output.split(self.RECORD_SEP)

        for record in records:
            record = record.strip()
            if not record:
                continue

            lines = record.split("\n", 1)
            formatted_line = lines[0]
            name_status_block = lines[1] if len(lines) > 1 else ""

            fields = formatted_line.split(self.FIELD_SEP)
            if len(fields) < 7:
                continue

            try:
                timestamp = datetime.fromisoformat(fields[4])
            except ValueError:
                continue

            file_changes = self._parse_file_changes(name_status_block)

            entries.append(
                AuditEntry(
                    commit_hash=fields[0],
                    short_hash=fields[1],
                    author=fields[2],
                    email=fields[3],
                    timestamp=timestamp,
                    subject=fields[5],
                    body=fields[6].strip(),
                    repo_name=repo_name,
                    repo_path=repo_path,
                    files_changed=file_changes,
                )
            )

        logger.info(f"Parsed {len(entries)} entries from {repo_name}")
        return entries

    def parse_multiple_repos(
        self,
        repo_paths: List[str],
        max_entries: int = 100,
        since: Optional[str] = None,
        until: Optional[str] = None,
        author: Optional[str] = None,
        config_only: bool = True,
    ) -> List[AuditEntry]:
        """Parse and merge git logs from multiple repositories.

        Returns entries sorted by timestamp, newest first.
        """
        all_entries: List[AuditEntry] = []
        for repo_path in repo_paths:
            try:
                entries = self.parse_repo(
                    repo_path, max_entries=max_entries,
                    since=since, until=until, author=author,
                )
                if config_only:
                    entries = [e for e in entries if e.is_config_change]
                all_entries.extend(entries)
            except GitLogError as e:
                logger.error(f"Failed to parse {repo_path}: {e}")

        all_entries.sort(key=lambda e: e.timestamp, reverse=True)
        return all_entries


# ---------------------------------------------------------------------------
# Report Formatter
# ---------------------------------------------------------------------------


class AuditFormatter:
    """Format audit trail entries for terminal or file output."""

    # ANSI color codes
    COLORS = {
        "reset": "\033[0m",
        "bold": "\033[1m",
        "dim": "\033[2m",
        "red": "\033[31m",
        "green": "\033[32m",
        "yellow": "\033[33m",
        "blue": "\033[34m",
        "magenta": "\033[35m",
        "cyan": "\033[36m",
    }

    REPO_COLORS = {
        "homelab-apps": "cyan",
        "homelab-infra": "magenta",
    }

    STATUS_COLORS = {
        "A": "green",
        "M": "yellow",
        "D": "red",
        "R": "blue",
    }

    CHANGE_TYPE_LABELS = {
        "feature": "FEAT",
        "fix": "FIX",
        "refactor": "REFAC",
        "docs": "DOCS",
        "chore": "CHORE",
        "ci": "CI",
        "test": "TEST",
        "other": "OTHER",
    }

    def __init__(self, color: bool = True) -> None:
        self.color = color

    def _c(self, text: str, color_name: str) -> str:
        if not self.color:
            return text
        c = self.COLORS.get(color_name, "")
        r = self.COLORS["reset"]
        return f"{c}{text}{r}"

    def format_table(self, entries: List[AuditEntry], max_entries: int = 100) -> str:
        """Format entries as a compact table for terminal display.

        Args:
            entries: Audit trail entries to format.
            max_entries: Maximum entries to display.

        Returns:
            Formatted string for terminal output.
        """
        if not entries:
            return "No configuration changes found.\n"

        display = entries[:max_entries]
        lines: List[str] = []

        # Header
        header = (
            f"{'Date':<12} {'Hash':<9} {'Repo':<15} {'Type':<7} "
            f"{'Author':<20} {'Subject':<50} {'Files':>5}"
        )
        lines.append(self._c(header, "bold"))
        lines.append("-" * 118)

        for entry in display:
            date_str = entry.timestamp.strftime("%Y-%m-%d")
            repo_color = self.REPO_COLORS.get(entry.repo_name, "dim")
            type_label = self.CHANGE_TYPE_LABELS.get(entry.change_type, "OTHER")

            subject = entry.subject[:50]
            author = entry.author[:20]
            file_count = len(entry.files_changed)

            line = (
                f"{date_str:<12} "
                f"{self._c(entry.short_hash, 'yellow'):<{9 + (8 if self.color else 0)}} "
                f"{self._c(entry.repo_name, repo_color):<{15 + (8 if self.color else 0)}} "
                f"{type_label:<7} "
                f"{author:<20} "
                f"{subject:<50} "
                f"{file_count:>5}"
            )
            lines.append(line)

        # Footer
        total = len(entries)
        shown = len(display)
        lines.append("-" * 118)
        footer = f"Showing {shown} of {total} configuration change(s)"
        if total > shown:
            footer += f" (use --max-entries to show more)"
        lines.append(self._c(footer, "dim"))

        return "\n".join(lines) + "\n"

    def format_detail(self, entries: List[AuditEntry], max_entries: int = 100) -> str:
        """Format entries with full file change details.

        Args:
            entries: Audit trail entries.
            max_entries: Maximum entries to display.

        Returns:
            Formatted string with per-file details.
        """
        if not entries:
            return "No configuration changes found.\n"

        display = entries[:max_entries]
        lines: List[str] = []

        for entry in display:
            repo_color = self.REPO_COLORS.get(entry.repo_name, "dim")
            date_str = entry.timestamp.strftime("%Y-%m-%d %H:%M:%S %z")

            lines.append(
                f"{self._c(entry.short_hash, 'yellow')} "
                f"{self._c(entry.repo_name, repo_color)} "
                f"{self._c(date_str, 'dim')}"
            )
            lines.append(
                f"  {self._c(entry.subject, 'bold')} "
                f"({entry.author})"
            )

            for fc in entry.files_changed:
                sc = self.STATUS_COLORS.get(fc.status[0], "dim")
                status_char = fc.status[0]
                lines.append(f"    {self._c(status_char, sc)} {fc.path}")

            lines.append("")

        total = len(entries)
        shown = len(display)
        footer = f"Showing {shown} of {total} configuration change(s)"
        if total > shown:
            footer += f" (use --max-entries to show more)"
        lines.append(self._c(footer, "dim"))

        return "\n".join(lines) + "\n"

    def format_markdown(self, entries: List[AuditEntry], max_entries: int = 100) -> str:
        """Format entries as a Markdown report.

        Args:
            entries: Audit trail entries.
            max_entries: Maximum entries to include.

        Returns:
            Markdown formatted report string.
        """
        if not entries:
            return "# Configuration Audit Trail\n\nNo configuration changes found.\n"

        display = entries[:max_entries]
        lines: List[str] = []
        lines.append("# Configuration Audit Trail\n")
        lines.append(f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  ")
        lines.append(f"**Entries**: {len(display)} of {len(entries)}  \n")

        # Summary by repo
        repo_counts: Dict[str, int] = {}
        for e in display:
            repo_counts[e.repo_name] = repo_counts.get(e.repo_name, 0) + 1

        lines.append("## Summary\n")
        lines.append("| Repository | Changes |")
        lines.append("|------------|---------|")
        for repo, count in sorted(repo_counts.items()):
            lines.append(f"| {repo} | {count} |")
        lines.append("")

        # Entries grouped by date
        current_date = ""
        for entry in display:
            date_str = entry.timestamp.strftime("%Y-%m-%d")
            if date_str != current_date:
                current_date = date_str
                lines.append(f"\n## {date_str}\n")

            lines.append(
                f"### `{entry.short_hash}` {entry.subject}\n"
            )
            lines.append(f"- **Repo**: {entry.repo_name}")
            lines.append(f"- **Author**: {entry.author}")
            lines.append(
                f"- **Time**: {entry.timestamp.strftime('%H:%M:%S %z')}"
            )
            lines.append(f"- **Type**: {entry.change_type}\n")

            if entry.files_changed:
                lines.append("**Files changed**:\n")
                for fc in entry.files_changed:
                    lines.append(f"- `{fc.status_label}` {fc.path}")
                lines.append("")

        lines.append("---")
        lines.append("*Generated by Configuration Audit Trail Viewer*\n")

        return "\n".join(lines)

    def format_json(self, entries: List[AuditEntry], max_entries: int = 100) -> str:
        """Format entries as JSON output.

        Args:
            entries: Audit trail entries.
            max_entries: Maximum entries to include.

        Returns:
            JSON formatted string.
        """
        display = entries[:max_entries]
        data = {
            "generated": datetime.now().isoformat(),
            "total_entries": len(entries),
            "shown_entries": len(display),
            "entries": [e.to_dict() for e in display],
        }
        return json.dumps(data, indent=2, default=str)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser."""
    parser = argparse.ArgumentParser(
        description="Configuration Audit Trail Viewer - "
        "view chronological config changes across homelab repositories",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  %(prog)s                              Show recent config changes\n"
            "  %(prog)s --since '2 weeks ago'         Changes in last 2 weeks\n"
            "  %(prog)s --repo homelab-apps            Only homelab-apps changes\n"
            "  %(prog)s --format markdown -o report.md Export as Markdown\n"
            "  %(prog)s --all                          Include non-config files\n"
            "  %(prog)s --detail                       Show per-file details\n"
        ),
    )

    parser.add_argument(
        "--config", help="Path to .env config file", default=None
    )
    parser.add_argument(
        "--since",
        help="Show changes since date (git --since format, e.g. '2 weeks ago')",
        default=None,
    )
    parser.add_argument(
        "--until",
        help="Show changes until date (git --until format)",
        default=None,
    )
    parser.add_argument(
        "--author", help="Filter by author name or email", default=None
    )
    parser.add_argument(
        "--repo",
        help="Filter to a specific repository (e.g. homelab-apps, homelab-infra)",
        default=None,
    )
    parser.add_argument(
        "--max-entries",
        type=int,
        help="Maximum entries to display (default: from config or 100)",
        default=None,
    )
    parser.add_argument(
        "--all",
        action="store_true",
        dest="show_all",
        help="Show all commits, not just config file changes",
    )
    parser.add_argument(
        "--detail",
        action="store_true",
        help="Show detailed view with per-file changes",
    )
    parser.add_argument(
        "--format",
        choices=["table", "detail", "json", "markdown"],
        default="table",
        help="Output format (default: table)",
    )
    parser.add_argument(
        "--output", "-o",
        help="Write output to file instead of stdout",
        default=None,
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable colored output",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )

    return parser


def main() -> None:
    """Main entry point for the audit trail viewer."""
    parser = build_parser()
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Load configuration
    config = Config(env_file=args.config)

    if args.verbose:
        logger.info(f"Configuration: {config}")

    # Validate repos
    try:
        warnings = config.validate()
        for w in warnings:
            logger.warning(w)
    except ValueError as e:
        logger.error(str(e))
        sys.exit(1)

    # Filter repos if requested
    repo_paths = config.repo_paths
    if args.repo:
        repo_paths = [p for p in repo_paths if args.repo in Path(p).name]
        if not repo_paths:
            logger.error(f"No matching repository for filter: {args.repo}")
            sys.exit(1)

    max_entries = args.max_entries or config.max_entries

    # Parse git logs
    parser_obj = GitLogParser(config_patterns=config.config_patterns)
    config_only = not args.show_all

    entries = parser_obj.parse_multiple_repos(
        repo_paths=repo_paths,
        max_entries=max_entries,
        since=args.since,
        until=args.until,
        author=args.author,
        config_only=config_only,
    )

    # Format output
    use_color = not args.no_color and not args.output
    fmt = args.format
    if args.detail and fmt == "table":
        fmt = "detail"

    formatter = AuditFormatter(color=use_color)

    if fmt == "table":
        output = formatter.format_table(entries, max_entries=max_entries)
    elif fmt == "detail":
        output = formatter.format_detail(entries, max_entries=max_entries)
    elif fmt == "json":
        output = formatter.format_json(entries, max_entries=max_entries)
    elif fmt == "markdown":
        output = formatter.format_markdown(entries, max_entries=max_entries)
    else:
        output = formatter.format_table(entries, max_entries=max_entries)

    # Output
    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(output)
        logger.info(f"Report saved to {out_path}")
    else:
        print(output)


if __name__ == "__main__":
    main()
