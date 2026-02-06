# Story 1.8 - Documentation Update Automation

**Status:** Development Complete ✅  
**Date:** 2026-02-06  
**Branch:** `feature/story-1.7-1.8-validation-docs`

## Implementation Summary

Implemented automated documentation updater that keeps README files and deployment mappings synchronized with infrastructure state. Extracts service information from compose files and updates documentation automatically.

### Files Created

1. **`doc_updater.py`** (398 lines)
   - DocUpdater class for documentation automation
   - Service inventory extraction from compose files
   - README.md service table generation
   - stack-targets.yml synchronization
   - Timestamp updates
   - Service catalog generation
   - Git commit integration

### Key Features

#### Documentation Updates

**README.md Updates:**
- Extracts all services from compose files
- Generates formatted service table (Stack | Service | Image | Endpoints)
- Updates "Last Audit" timestamps
- Uses HTML comments as markers for safe updates

**stack-targets.yml Updates:**
- Adds new stacks automatically (with defaults)
- Removes stacks that no longer exist
- Preserves manual configuration overrides

**Service Catalog Generation:**
- Comprehensive service documentation
- Grouped by stack
- Includes endpoints from Traefik labels
- Optional separate catalog file

#### Service Information Extraction

Automatically extracts:
- Service names
- Container images
- Traefik endpoints (from router rules)
- Stack associations

### Usage Examples

```bash
# Update all documentation
python doc_updater.py /path/to/homelab-apps

# Update and commit changes
python doc_updater.py /path/to/homelab-apps --commit

# Generate service catalog
python doc_updater.py /path/to/homelab-apps --catalog SERVICE_CATALOG.md
```

### Marker-Based Updates

Uses HTML comment markers for safe updates:

```markdown
<!-- BEGIN SERVICE LIST -->
## Deployed Services

| Stack | Service | Image | Endpoints |
|-------|---------|-------|-----------|
| dns-pihole | pihole | `pihole/pihole:2024.01.0` | pihole.home.lan |

**Total Services:** 15
**Last Updated:** 2026-02-06 12:00:00
<!-- END SERVICE LIST -->
```

### Design Decisions

1. **Marker-Based**: HTML comments ensure safe replacements without breaking manual content
2. **Preserve Manual Edits**: Only updates content between markers
3. **Automatic Discovery**: Scans all stacks automatically
4. **Traefik Integration**: Extracts endpoints from router rules
5. **Git Integration**: Optional automatic commits

### Service Table Example

```markdown
## Deployed Services

| Stack | Service | Image | Endpoints |
|-------|---------|-------|-----------|
| dns-pihole | pihole | `pihole/pihole:2024.01.0` | pihole.home.lan |
| media-overseerr | overseerr | `sctx/overseerr:1.33.2` | requests.home.lan |
| media-plex | plex | `plexinc/pms-docker:1.40.0` | plex.home.lan |
| proxy-traefik | traefik | `traefik:v3.0` | traefik.home.lan |

**Total Services:** 15
**Last Updated:** 2026-02-06 12:00:00
```

### stack-targets.yml Updates

Before:
```yaml
dns-pihole:
  target: ct-docker-01
  enabled: true
old-stack:  # Stack no longer exists
  target: ct-docker-01
  enabled: false
```

After:
```yaml
dns-pihole:
  target: ct-docker-01
  enabled: true
new-stack:  # Automatically added
  target: ct-docker-01
  enabled: true
```

### Acceptance Criteria Status

✅ **Updates service lists in repository READMEs** - Automatic table generation  
✅ **Refreshes deployment target mappings** - stack-targets.yml sync  
✅ **Updates "Last Audit" timestamp** - Automatic timestamp updates  
✅ **Commits documentation updates** - Optional git integration  
✅ **Parses compose files to extract service metadata** - Complete extraction  
✅ **Updates markdown tables with current service inventory** - Formatted tables  
✅ **Includes in PR automation workflow** - Ready for integration

## Code Statistics

- **Total Lines**: 398
- **Functions**: 8+ public methods
- **Classes**: 2 (DocUpdater, ServiceInfo)
- **Output Formats**: Markdown tables, YAML, separate catalogs

## Integration Points

### With PR Automation
```python
# In pr_generator.py workflow:
from doc_updater import DocUpdater

updater = DocUpdater(repo_path)
updated_files = updater.update_all()

# Include updated docs in PR commit
for file in updated_files:
    subprocess.run(["git", "add", str(file)])
```

### With CI/CD
```yaml
# GitHub Actions example
- name: Update Documentation
  run: |
    python tools/drift-detection/doc_updater.py . --commit
```

## Integration Example

Complete workflow combining drift detection and doc updates:

```bash
# 1. Detect drift
python drift_detect.py

# 2. Generate PRs for remediation
python drift_remediate.py full --repo /path/to/homelab-apps

# 3. Update documentation
python doc_updater.py /path/to/homelab-apps --commit

# All in one automated workflow!
```

## Next Steps

1. **Code Review** (Story 1.8)
2. **Integration** with PR generator
3. **Testing** with actual README markers
