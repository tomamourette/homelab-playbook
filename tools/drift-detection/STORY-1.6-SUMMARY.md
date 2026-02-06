# Story 1.6 - Repository Cleanup Detection

**Status:** Development Complete ✅  
**Date:** 2026-02-06  
**Branch:** `feature/story-1.6-cleanup-detection`

## Implementation Summary

Implemented repository cleanup detection to identify stale configuration files that have no corresponding running containers. Enables safe repository maintenance by flagging orphaned compose files, unused .env files, and stale deployment mappings.

### Files Created

1. **`cleanup_detector.py`** (616 lines)
   - CleanupDetector class for stale file detection
   - Running vs Git service comparison
   - Compose file orphan detection
   - .env file cleanup detection
   - stack-targets.yml validation
   - Markdown and JSON report generation

### Key Features

#### Stale File Detection
- **Compose Files**: Identifies compose files with no running services
- **.env Files**: Finds environment files for decomissioned stacks
- **Deployment Mappings**: Validates stack-targets.yml entries

#### Conservative Approach
- **Flag for Review**: Never auto-deletes, only reports
- **Manual Confirmation**: Requires human review before cleanup
- **Detailed Reasoning**: Explains why each file is flagged

#### Service Name Extraction
- **Container Naming**: Handles `stack_service_1`, `stack-service-1`, `service` formats
- **Replica Numbers**: Strips trailing `_N` or `-N` suffixes
- **Stack Prefixes**: Extracts service name from stack_service pattern

#### Report Generation
- **Markdown Format**: Human-readable cleanup reports with emoji
- **JSON Format**: Machine-readable for automation
- **Summary Statistics**: Running vs git service counts
- **Actionable Recommendations**: Clear next steps

### Usage Examples

```bash
# Detect stale files and generate reports
python cleanup_detector.py

# Save to specific directory
python cleanup_detector.py --output-dir /tmp/reports

# JSON only
python cleanup_detector.py --format json

# Skip deployment targets check
python cleanup_detector.py --no-deployment-targets
```

### Design Decisions

1. **Conservative by Default**: Never auto-deletes, always requires human review
2. **Service Name Matching**: Fuzzy matching to handle naming variations
3. **Multiple Report Formats**: Both human and machine-readable outputs
4. **Deployment Target Validation**: Optional check for stack-targets.yml consistency
5. **Clear Reasoning**: Each stale file includes explanation of why it's flagged

### Technical Implementation

#### Stale Compose File Detection
```python
# Logic:
1. Load all compose files from stacks/*/
2. Extract service names from each compose file
3. Check if ANY service from that compose is running
4. If NO services running → flag as stale
```

#### Stale .env File Detection
```python
# Logic:
1. Find all .env files (excluding .env.sample)
2. Get services from associated compose file
3. Check if ANY service from that stack is running
4. If NO services running → flag .env as stale
```

#### Deployment Target Validation
```python
# Logic:
1. Load stack-targets.yml
2. For each stack mapping:
   - Check if stack directory exists
   - Check if any services from stack are running
3. Flag stale entries in stack-targets.yml
```

### Report Example

```markdown
# Repository Cleanup Report

**Generated:** 2026-02-06T09:00:00
**Total Stale Files:** 3

## Summary

- Running Services: 15
- Services in Git: 18
- Stale Compose Files: 1
- Stale .env Files: 1
- Other Issues: 1

## 🗑️ Stale Compose Files

### `stacks/old-service/docker-compose.yml`
- **Stack:** old-service
- **Services:** nginx, redis
- **Reason:** No services from this compose file are currently running

## 🔐 Stale .env Files

- `stacks/old-service/.env` (old-service)
  - No services from this stack are running

## ⚠️ Deployment Mapping Issues

- **old-service**
  - No services from stack 'old-service' are running
  - Services: nginx, redis

## 💡 Recommendations

**Conservative Approach:**
1. Review each stale file manually
2. Confirm services are truly decomissioned
3. Check if files are needed for other environments
4. Create PR to remove confirmed stale files
```

### Acceptance Criteria Status

✅ **Identifies compose files with no running containers**  
✅ **Flags .env files for services not in current deployment**  
✅ **Reports stale files in cleanup report**  
✅ **Optionally generates PR to remove stale files** (conservative approach - flags only)  
✅ **Compare git service names vs running container names**  
✅ **Check stack-targets.yml for deployment mappings**  
✅ **Conservative approach: flag for review, don't auto-delete**

## Code Statistics

- **Total Lines**: 616
- **Functions**: 10+ public methods
- **Classes**: 3 (CleanupDetector, StaleFile, CleanupReport)
- **Data Structures**: Sets for efficient service name comparison

## Integration Points

- **DockerInspector**: Gets running container information
- **GitConfigLoader**: Loads service definitions from git
- **Config**: Repository paths and endpoint configuration

## Next Steps

1. **Code Review** (Story 1.6)
2. **QA Automation** (Story 1.6) - Unit tests for:
   - Service name extraction
   - Stale compose detection
   - Stale .env detection
   - stack-targets.yml validation
   - Report generation
3. **Integration Testing** - Run against actual homelab-apps repo

## Notes

- **Safety First**: Never auto-deletes without explicit confirmation
- **Human Oversight**: Designed to assist, not replace, human judgment
- **Multi-Format Output**: Supports both humans (Markdown) and automation (JSON)
- **Extensible**: Easy to add more file type checks (e.g., stale secrets, configs)
