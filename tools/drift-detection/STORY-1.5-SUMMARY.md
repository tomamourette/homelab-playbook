# Story 1.5: Pull Request Generation for Drift Remediation - Implementation Summary

**Date**: 2026-02-06  
**Branch**: `feature/story-1.5-pr-generation`

## Overview

Implemented automated Pull Request generation for drift remediation, enabling review-based synchronization of git repositories with running container configurations.

## Files Created

### pr_generator.py (475 lines, 16.7KB)

**Main Class: PRGenerator**

Complete PR workflow automation:

**Core Methods:**

1. **`create_branch()`** - Create git branch for drift fix
   - Checkout base branch
   - Pull latest changes
   - Create new feature branch with naming convention

2. **`update_compose_file()`** - Update Docker Compose with running config
   - Load and parse YAML compose file
   - Update service configuration (image, env, ports, volumes, networks, labels)
   - Write updated compose file

3. **`commit_changes()`** - Conventional commit message
   - Stage all changes
   - Create commit with format: `fix(service): sync config with running state`

4. **`push_branch()`** - Push branch to remote
   - Push with upstream tracking

5. **`create_pr_description()`** - Generate comprehensive PR description
   - Header with service/stack info
   - Summary of drift items
   - Before/after configuration changes
   - Drift report link
   - Review checklist
   - Auto-generated labels

6. **`create_github_pr()`** - Create PR via GitHub API
   - Use PyGithub library
   - Create pull request
   - Add labels: `drift-remediation`, `automated`

7. **`generate_pr_for_service()`** - Complete workflow orchestration
   - Execute all steps in sequence
   - Error handling and logging
   - Return PR URL

**Features:**
- Branch naming: `fix/drift-<service>-<timestamp>`
- Conventional commits: `fix(service): description`
- Comprehensive PR descriptions with:
  - Configuration change details
  - Severity indicators
  - Drift report references
  - Review checklists
- GitHub API integration with PyGithub
- Configurable via environment variables
- Graceful degradation if GitHub token not available

**Configuration:**
- `GITHUB_TOKEN` - Personal access token
- `GITHUB_REPO_OWNER` - Repository owner/org
- `GITHUB_REPO_NAME` - Repository name

### Updated Files

**requirements.txt**
- Added `PyGithub>=2.1.1` for GitHub API integration

**__init__.py**
- Added pr_generator exports:
  - PRGenerator class
  - PRGenerationError, GitOperationError exceptions
  - generate_pr() convenience function

## Acceptance Criteria Met

✅ **Creates new git branch (`fix/drift-<service>-<timestamp>`)**
- Implemented in `create_branch()`
- Naming convention includes service name and timestamp

✅ **Updates compose file in target repo**
- Implemented in `update_compose_file()`
- Updates image, environment, ports, volumes, networks, labels

✅ **Commits with conventional commit message**
- Format: `fix(service): sync config with running state`
- Implemented in `commit_changes()`

✅ **Opens PR via GitHub API with details**
- Implemented in `create_github_pr()` using PyGithub
- Includes:
  - Detailed description of changes
  - Before/after diff summary
  - Drift report link
  - Review checklist

✅ **PR tagged with `drift-remediation` label**
- Automatically adds `drift-remediation` and `automated` labels

## Technical Implementation

### Git Operations
Uses `subprocess` to execute git commands:
- `git checkout` - Switch branches
- `git pull` - Update base branch
- `git checkout -b` - Create new branch
- `git add -A` - Stage changes
- `git commit -m` - Commit with message
- `git push -u origin` - Push with tracking

### GitHub API Integration
Uses PyGithub library:
- `Github(token)` - Initialize client
- `get_repo(owner/name)` - Get repository
- `create_pull()` - Create PR
- `add_to_labels()` - Add labels

### Compose File Updates
Uses PyYAML for safe YAML manipulation:
- Load existing compose file
- Update service configuration
- Write back preserving structure

### Error Handling
Custom exceptions:
- `PRGenerationError` - PR workflow failures
- `GitOperationError` - Git command failures

## Workflow Example

```python
from pr_generator import PRGenerator

generator = PRGenerator(
    github_token="ghp_...",
    repo_owner="tomamourette",
    repo_name="homelab-apps"
)

pr_url = generator.generate_pr_for_service(
    repo_path=Path("/path/to/homelab-apps"),
    service_name="pihole",
    stack_name="dns-pihole",
    running_config={
        "image": "pihole/pihole:2024.01",
        "environment": {"TZ": "Europe/Brussels"}
    },
    drift_items=[{
        "field_path": "image",
        "baseline_value": "pihole/pihole:2023.05",
        "running_value": "pihole/pihole:2024.01",
        "severity": "breaking"
    }]
)

print(f"PR created: {pr_url}")
```

## Generated PR Structure

### Branch Name
```
fix/drift-pihole-20260206-080000
```

### Commit Message
```
fix(pihole): sync config with running state
```

### PR Title
```
fix(pihole): sync config with running state
```

### PR Description
```markdown
# Drift Remediation: pihole

**Stack**: dns-pihole
**Auto-generated**: 2026-02-06T08:00:00

## Summary

This PR updates the git baseline configuration for `pihole` to match
the current running state, remediating 1 configuration drift item(s).

## Configuration Changes

### image

- **Severity**: breaking
- **Baseline**: `pihole/pihole:2023.05`
- **Running**: `pihole/pihole:2024.01`

## Drift Report

See full drift analysis: `reports/drift-2026-02-06.md`

## Review Checklist

- [ ] Running configuration is correct and intentional
- [ ] Changes align with deployment standards
- [ ] No sensitive data exposed in configuration
- [ ] Documentation updated if needed

---
*Auto-generated by drift detection tool*
**Labels**: `drift-remediation`, `automated`
```

## Integration Points

### With Existing Modules

**drift_comparator.py:**
- Uses ServiceDrift data as input
- Extracts drift_items for PR description

**drift_report_generator.py:**
- Links to generated drift reports
- References report paths in PR descriptions

**config.py:**
- Could extend to include GitHub config
- Current implementation uses environment variables

## Known Limitations

1. **GitHub Token Required**
   - PR creation requires valid GitHub token
   - Gracefully degrades if not available
   - Should document token permissions needed

2. **Compose File Path Assumptions**
   - Assumes structure: `stacks/<stack-name>/docker-compose.yml`
   - Falls back to: `<stack-name>/docker-compose.yml`
   - May need configuration for custom structures

3. **Simplified Running Config**
   - Convenience function reconstructs config from drift items
   - Full workflow should use complete ContainerInfo

4. **No Conflict Resolution**
   - Assumes clean merge to base branch
   - Manual resolution needed for conflicts

5. **One PR Per Service**
   - Creates separate PR for each service
   - Can't batch multiple services
   - Intentional per requirements

## Security Considerations

**Token Management:**
- Token loaded from environment variable
- Not stored in code or logs
- Should use GitHub fine-grained tokens with minimal permissions

**Required Permissions:**
- `contents: write` - Push branches, create commits
- `pull_requests: write` - Create PRs, add labels
- `metadata: read` - Read repository info

**Sensitive Data:**
- Compose files may contain secrets
- PR descriptions show before/after values
- **Recommendation**: Sanitize environment variables before PR creation

## Testing Requirements

**Unit Tests Needed:**
- Test PRGenerator initialization
- Test branch naming convention
- Test compose file updates (with mocked YAML)
- Test commit message format
- Test PR description generation
- Test error handling

**Integration Tests Needed (Requires GitHub Access):**
- Test complete PR workflow against test repository
- Test with various drift scenarios
- Test label addition
- Test with merge conflicts

**Manual Testing Checklist:**
1. Set up test GitHub repository
2. Configure GITHUB_TOKEN, GITHUB_REPO_OWNER, GITHUB_REPO_NAME
3. Run PR generation for sample drift
4. Verify PR created with correct structure
5. Verify labels applied
6. Test merge process

## Next Steps

1. **Story 1.5 Code Review** - Review PR generation logic
2. **Story 1.5 QA-Automate** - Create test suite
3. **Story 1.6** - Repository cleanup detection
4. **Story 1.7** - Repository structure validation
5. **Story 1.8** - Documentation update automation

## Configuration Example

```bash
# ~/.bashrc or .env
export GITHUB_TOKEN="ghp_xxxxxxxxxxxxxxxxxxxx"
export GITHUB_REPO_OWNER="tomamourette"
export GITHUB_REPO_NAME="homelab-apps"
```

## Performance Considerations

**Workflow Steps:**
1. Git operations: ~2-5 seconds (depends on repo size, network)
2. Compose file update: <1 second
3. GitHub API: ~1-2 seconds
4. **Total**: ~5-10 seconds per PR

**Acceptable For:**
- Small to medium repositories (<100MB)
- Individual service remediation
- Review-based workflow (not time-critical)

**Future Optimization:**
- Parallel PR creation for multiple services
- Local git operations before push (batch commits)
- PR templates for consistent descriptions

---

**Implementation Status**: ✅ COMPLETE (dev)  
**Next Step**: Code review  
**Lines of Code**: 475
