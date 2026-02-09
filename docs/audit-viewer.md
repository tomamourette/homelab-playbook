# Configuration Audit Trail Viewer

The Audit Trail Viewer is a CLI tool designed to provide a chronological history of configuration changes across your homelab repositories. It parses git logs from `homelab-infra` and `homelab-apps` to show exactly what changed, when, and by whom.

## Features
- **Cross-Repo Timeline**: Unified view of changes across infrastructure and applications.
- **Config-First Filtering**: Automatically identifies changes to YAML, JSON, ENV, and Terraform files.
- **Flexible Formats**: Output as a clean terminal table, detailed per-file list, JSON, or Markdown.
- **Deep Integration**: Uses the same `.env` configuration as the drift detection tools.

## Usage

### Basic View
Show the most recent configuration changes across all repos:
```bash
python3 tools/audit_viewer.py
```

### Detailed View
Show exactly which files were modified in each commit:
```bash
python3 tools/audit_viewer.py --detail
```

### Filter by Repository
Only show changes from the application stack:
```bash
python3 tools/audit_viewer.py --repo homelab-apps
```

### Filter by Time
Show changes from the last 7 days:
```bash
python3 tools/audit_viewer.py --since "7 days ago"
```

### Export to Markdown
Generate a report for documentation:
```bash
python3 tools/audit_viewer.py --format markdown -o reports/audit-trail.md
```

## Configuration
The tool reads from `tools/drift-detection/.env` for repository paths. You can override these using environment variables:
- `HOMELAB_APPS_PATH`: Path to the apps repo.
- `HOMELAB_INFRA_PATH`: Path to the infra repo.
- `AUDIT_MAX_ENTRIES`: Limit the number of commits processed.
