# Story 1.5 - Pull Request Generation for Drift Remediation

**Status:** Development Complete ✅  
**Date:** 2026-02-06  
**Branch:** `feature/story-1.5-pr-generation`

## Implementation Summary

Implemented automated Pull Request generation for drift remediation, enabling the system to automatically create PRs that backport running configurations to git repositories.

### Files Created

1. **`pr_generator.py`** (565 lines)
   - Core PR generation logic
   - GitHub API integration
   - Branch creation and management
   - Compose file updates
   - Conventional commit generation

2. **`drift_remediate.py`** (329 lines)
   - End-to-end CLI orchestration
   - Three subcommands: `detect`, `remediate`, `full`
   - Integrates all drift detection modules

### Key Features

#### PR Generator (`pr_generator.py`)
- **Branch Management**: Creates feature branches (`fix/drift-<stack>-<timestamp>`)
- **Compose Updates**: Parses YAML, applies drift fixes, writes back
- **Conventional Commits**: Generates structured commit messages with severity classification
- **GitHub Integration**: Creates PRs via API with detailed descriptions
- **Error Handling**: Graceful cleanup on failures, comprehensive error messages
- **Dry-Run Mode**: Test workflow without creating actual PRs

#### PR Metadata
- **Title**: `fix(<stack>): Sync <service> config with running state`
- **Body**: Includes:
  - Drift summary table
  - Before/after values for each drift item
  - Severity classification (🔴 BREAKING, 🟡 FUNCTIONAL, 🔵 COSMETIC, ⚪ INFORMATIONAL)
  - Review notes and context
- **Labels**: `drift-remediation`, `automated`

#### Remediation CLI (`drift_remediate.py`)
- **`detect`**: Run drift detection and save report
- **`remediate`**: Generate PRs from existing drift report
- **`full`**: End-to-end workflow (detect + remediate in one command)

### Dependencies Added
- `requests>=2.31.0` (GitHub API calls)

### Usage Examples

```bash
# Detect drift only
python drift_remediate.py detect --output drift-report.json

# Generate PRs from existing report (dry-run)
python drift_remediate.py remediate \
    --report drift-report.json \
    --repo /path/to/homelab-apps \
    --dry-run

# Full workflow (detect + remediate)
python drift_remediate.py full \
    --repo /path/to/homelab-apps \
    --dry-run

# Actual PR generation (remove --dry-run)
python drift_remediate.py full --repo /path/to/homelab-apps
```

### Environment Configuration

Required environment variables for PR creation:
- `GITHUB_TOKEN`: GitHub personal access token with repo permissions
- `GITHUB_REPO`: Target repository (e.g., `user/homelab-apps`)

### Design Decisions

1. **One PR per Service**: Each drifted service gets its own PR for cleaner review
2. **YAML Parsing**: Using `pyyaml` for safe compose file manipulation
3. **Conventional Commits**: Following commit message standards for automated changelog generation
4. **API-First**: Using GitHub REST API directly for more control vs PyGithub wrapper
5. **Graceful Cleanup**: Failed PR generation cleans up branches automatically

### Technical Implementation

#### Commit Message Format
```
<type>(<scope>): <subject>

<body with drift details>
```

Example:
```
fix(dns-pihole): sync pihole config with running state

Detected 3 configuration drift(s) in pihole:

- labels.traefik.http.routers.pihole.rule: FUNCTIONAL
  Git: Host(`pihole.local`)
  Running: Host(`pihole.home.lan`)
- environment.TZ: COSMETIC
  Git: UTC
  Running: Europe/Brussels

This PR backports the running configuration to git to eliminate drift.
```

#### PR Workflow
1. Create feature branch from `main`
2. Load compose file from git
3. Apply drift fixes (update YAML structure)
4. Commit with conventional commit message
5. Push branch to remote
6. Create PR via GitHub API
7. Add labels to PR

### Acceptance Criteria Status

✅ **PR automation module** - `pr_generator.py` implements complete workflow  
✅ **Branch creation** - Automatic feature branch naming and creation  
✅ **Commit generation** - Conventional commits with detailed drift info  
✅ **PR body with drift details** - Structured markdown with severity tables  
✅ **One PR per service** - Isolated changes for easier review  
✅ **Dry-run mode** - Safe testing without actual PR creation  
✅ **Error handling** - Graceful failures with cleanup

## Code Statistics

- **Total Lines**: 894 (pr_generator.py: 565, drift_remediate.py: 329)
- **Functions**: 15+ public functions
- **Classes**: 3 (PRGenerator, DriftItem, PRMetadata)
- **API Integration**: GitHub REST API v3

## Next Steps

1. **Code Review** (Story 1.5)
2. **QA Automation** (Story 1.5) - Unit tests for:
   - Branch creation/cleanup
   - Compose file updates
   - Commit message generation
   - PR metadata generation
   - API mocking for GitHub calls
3. **Integration Testing** - Full workflow test with real drift data

## Notes

- **Network Independence**: PR generation works offline until push/API calls
- **Repository Agnostic**: Works with any git repository (homelab-apps, homelab-infra)
- **Extensible**: Easy to add support for GitLab, Gitea, or other platforms
