# Story 1.7 - Repository Structure Validation

**Status:** Development Complete ✅  
**Date:** 2026-02-06  
**Branch:** `feature/story-1.7-1.8-validation-docs`

## Implementation Summary

Implemented repository structure validator to ensure consistency across all infrastructure code. Validates Docker Compose files against best practices and conventions with clear severity classification.

### Files Created

1. **`structure_validator.py`** (556 lines)
   - StructureValidator class for convention checking
   - Compose v2 syntax validation
   - Image tag pinning enforcement
   - Traefik v3 label validation
   - Network configuration checks
   - .env.sample requirement checking
   - Markdown and JSON report generation

### Key Features

#### Validation Rules

**ERROR Level (must fix):**
- Image tags must be pinned (no `:latest` or untagged)
- YAML syntax must be valid
- External proxy network must be marked as external
- Files must be readable

**WARNING Level (should fix):**
- Compose v2 should not have `version` field
- Traefik-enabled services should have `traefik.enable` label
- Stacks should have `.env.sample` file

**INFO Level (optional):**
- Traefik router names should match service names
- Convention suggestions

#### Severity Classification
```python
class ValidationSeverity(Enum):
    ERROR = "ERROR"      # Must fix before merge
    WARNING = "WARNING"  # Should fix, but not blocking
    INFO = "INFO"        # Nice to have, optional
```

#### Exit Code Support
- Exit 0: All checks passed
- Exit 1: Errors found (or warnings with `--fail-on-warning`)
- Perfect for CI/CD integration

### Usage Examples

```bash
# Validate repository
python structure_validator.py /path/to/homelab-apps

# Save report to file
python structure_validator.py /path/to/homelab-apps --output validation-report.md

# JSON output for CI/CD
python structure_validator.py /path/to/homelab-apps --format json

# Fail on warnings (strict mode)
python structure_validator.py /path/to/homelab-apps --fail-on-warning
```

### Validation Checks Implemented

1. **Compose v2 Syntax**
   - Detects deprecated `version` field
   - Provides line numbers for issues

2. **Image Tags**
   - Ensures all images have specific version tags
   - Prevents `:latest` usage
   - Detects untagged images

3. **Traefik Labels**
   - Validates v3 label conventions
   - Checks for `traefik.enable` label
   - Suggests consistent router naming

4. **Networks**
   - Validates external proxy network
   - Ensures proper network configuration

5. **Environment Files**
   - Checks for `.env.sample` presence
   - Ensures stacks have example configs

### Report Example

```markdown
# Repository Structure Validation Report

**Generated:** 2026-02-06T12:00:00
**Files Checked:** 15
**Total Issues:** 3

## Summary

- ❌ Errors: 1 (must fix)
- ⚠️  Warnings: 1 (should fix)
- ℹ️  Info: 1 (optional)

**Status:** ❌ FAILED

## ❌ Errors (Must Fix)

### stacks/web/docker-compose.yml
- **Rule:** `pinned-tags`
- **Issue:** Service 'nginx' uses :latest tag: nginx:latest
- **Fix:** Pin to a specific version instead of :latest

## ⚠️  Warnings (Should Fix)

### stacks/media/docker-compose.yml
- **Rule:** `compose-v2-syntax`
- **Issue:** Compose file contains 'version' field (deprecated in Compose v2)
- **Line:** 1
- **Fix:** Remove the 'version' field - it's ignored in Compose v2
```

### Design Decisions

1. **Severity Levels**: Clear ERROR/WARNING/INFO classification
2. **Line Numbers**: Provided when possible for quick fixes
3. **Actionable Suggestions**: Every issue includes fix recommendation
4. **Multiple Formats**: Both human (Markdown) and machine (JSON) outputs
5. **CI/CD Ready**: Exit codes for automated checks

### Acceptance Criteria Status

✅ **Compose files use v2 syntax** - Validates and warns about version field  
✅ **Image tags are pinned** - Enforces specific versions, blocks :latest  
✅ **.env.sample exists for each stack** - Checks and warns if missing  
✅ **Traefik labels follow v3 conventions** - Validates label structure  
✅ **Networks reference external proxy network** - Validates external flag  
✅ **Reports validation failures with remediation guidance** - Clear suggestions  
✅ **Validation passes/fails overall** - Exit codes 0/1

## Code Statistics

- **Total Lines**: 556
- **Functions**: 15+ methods
- **Classes**: 3 (StructureValidator, ValidationIssue, ValidationReport)
- **Validation Rules**: 7+ checks implemented

## Integration

Perfect for CI/CD pipelines:

```yaml
# GitHub Actions example
- name: Validate Repository Structure
  run: |
    python tools/drift-detection/structure_validator.py . --fail-on-warning
```

## Next Steps

1. **Code Review** (Story 1.7)
2. **Integration** with PR automation workflow
3. **CI/CD** pipeline integration
