# Story 1.3: Configuration Comparison Engine - Implementation Summary

**Date**: 2026-02-06  
**Branch**: `feature/story-1.3-comparison-engine`

## Overview

Implemented comprehensive configuration drift comparison engine that matches running Docker containers to git baseline configurations and performs deep comparison with severity classification.

## Files Created

### drift_comparator.py (547 lines, 20KB)

**Core Classes:**

1. **DriftSeverity (Enum)**
   - BREAKING - Changes that break functionality (image tags, critical env vars)
   - FUNCTIONAL - Changes that affect behavior (ports, non-critical env vars)
   - COSMETIC - No functional impact (labels, ordering)
   - INFORMATIONAL - Expected/acceptable differences

2. **DriftItem (Dataclass)**
   - Represents individual configuration drift
   - Fields: field_path, baseline_value, running_value, severity, description
   - Supports JSON serialization

3. **ServiceDrift (Dataclass)**
   - Drift analysis for single service/container
   - Tracks matched status, drift items, severity counts
   - Methods: get_severity_counts(), has_breaking_drift(), to_dict()

4. **DriftReport (Dataclass)**
   - Complete drift analysis report
   - Summary statistics: services_analyzed, services_with_drift, total_drift_items
   - Methods: get_severity_summary(), get_breaking_services(), to_dict()

5. **DriftComparator (Class)**
   - Main comparison engine
   - Methods:
     - `normalize_value()` - Value normalization for comparison
     - `compare_images()` - Image drift detection with version awareness
     - `classify_field_severity()` - Classify drift severity by field type
     - `deep_compare()` - Recursive deep comparison with path tracking
     - `match_container_to_baseline()` - Container-to-baseline matching
     - `compare_configurations()` - Main comparison orchestration

**Key Features:**
- Deep recursive comparison with dot-notation path tracking
- Severity classification based on field type and impact
- Image version comparison (major vs minor version drift)
- Critical environment variable detection
- Ephemeral field filtering
- Structured diff output (JSON-serializable)

### drift_detect.py (226 lines, 7KB)

**Complete drift detection workflow orchestration:**

1. Load configuration from .env
2. Connect to target hosts and inspect running containers
3. Load git baseline configurations
4. Perform drift comparison
5. Generate and save report (JSON format)

**CLI Options:**
- `--config` - Path to .env config file
- `--output-dir` - Output directory for reports
- `--format` - Report format (json, markdown, both)
- `--verbose` - Enable debug logging

**Exit Codes:**
- 0 - No drift detected
- 1 - Drift detected
- 2 - Error during execution

### Updated Files

**__init__.py**
- Added drift_comparator exports:
  - DriftComparator, DriftReport, ServiceDrift, DriftItem, DriftSeverity
  - compare_drift() convenience function

## Acceptance Criteria Met

✅ **Match containers to git baselines**
- Implemented in `match_container_to_baseline()`
- Handles direct name matches and stack-prefixed names
- Tracks matched vs unmatched baselines

✅ **Compare configuration fields**
- Deep comparison of: labels, networks, volumes, environment, image tags
- Recursive dict comparison with path tracking
- List comparison (TODO: order-insensitive for certain fields)

✅ **Identify differences with field-level detail**
- DriftItem captures: field_path, baseline_value, running_value, description
- Dot-notation paths (e.g., 'labels.traefik.http.routers.service.rule')

✅ **Classify drift severity**
- Four-level severity: BREAKING, FUNCTIONAL, COSMETIC, INFORMATIONAL
- Image version-aware classification (major vs minor changes)
- Critical environment variable detection
- Traefik routing label awareness

✅ **Output structured diff data (JSON)**
- Complete JSON serialization via to_dict() methods
- Hierarchical structure: DriftReport → ServiceDrift → DriftItem
- Summary statistics and severity breakdowns

## Technical Implementation

### Comparison Logic

**Field-Level Severity Rules:**
- Image tags: Major version change = BREAKING, minor = FUNCTIONAL
- Environment variables:
  - DATABASE_URL, API_KEY, VPN_* = BREAKING
  - Other env vars = FUNCTIONAL
- Ports, volumes, networks = FUNCTIONAL
- Traefik routing labels = FUNCTIONAL
- Other labels = COSMETIC

**Matching Strategy:**
1. Direct name match (container.name == baseline.name)
2. Stack-prefixed match (container_name.startswith(stack_name_))
3. Unmatched containers = baseline_missing
4. Unmatched baselines = container_missing

**Value Normalization:**
- Empty strings and None treated as equivalent
- Boolean string normalization ('true'/'false')
- TODO: List ordering normalization for certain fields

### Example Output Structure

```json
{
  "timestamp": "2026-02-06T07:00:00",
  "services_analyzed": 10,
  "services_with_drift": 3,
  "total_drift_items": 8,
  "severity_summary": {
    "breaking": 1,
    "functional": 4,
    "cosmetic": 3,
    "informational": 0
  },
  "breaking_services": 1,
  "service_drifts": [
    {
      "service_name": "pihole",
      "stack_name": "dns-pihole",
      "container_id": "abc123def456",
      "has_drift": true,
      "matched": true,
      "drift_items": [
        {
          "field_path": "image",
          "baseline_value": "pihole/pihole:2023.05",
          "running_value": "pihole/pihole:2024.01",
          "severity": "breaking",
          "description": "Field 'image' changed from '...' to '...'"
        }
      ],
      "severity_counts": {
        "breaking": 1,
        "functional": 0,
        "cosmetic": 0,
        "informational": 0
      }
    }
  ]
}
```

## Usage Example

```bash
# Basic drift detection
cd /root/.openclaw/workspace/homelab-playbook/tools/drift-detection
./drift_detect.py

# With custom config and output
./drift_detect.py --config /path/to/.env --output-dir /reports --verbose

# Check exit code
./drift_detect.py && echo "No drift!" || echo "Drift detected!"
```

## Integration with Existing Modules

**docker_inspector.py:**
- Uses ContainerInfo objects as input
- Inspects running containers from target hosts

**git_config_loader.py:**
- Uses GitBaselineConfig objects as input
- Loads baseline configs from git repositories

**config.py:**
- Uses Config object for SSH connection settings
- Specifies target_hosts, homelab_apps_path, endpoint

## Known Limitations

1. **List Comparison**: Currently order-sensitive for all list fields
   - TODO: Make order-insensitive for networks, volumes where appropriate

2. **Ephemeral Field Detection**: Hard-coded list of ephemeral fields
   - TODO: Make configurable or auto-detect

3. **Critical Env Var Patterns**: Hard-coded patterns for critical variables
   - TODO: Make configurable via config file

4. **Markdown Report**: Not yet implemented (Story 1.4)
   - drift_detect.py has placeholder for Markdown generation

## Testing Requirements

**Unit Tests Needed:**
- Test DriftItem, ServiceDrift, DriftReport dataclasses
- Test DriftComparator methods:
  - normalize_value()
  - compare_images() (all version scenarios)
  - classify_field_severity() (all field types)
  - deep_compare() (nested dicts, lists, primitives)
  - match_container_to_baseline() (name variations)
- Test compare_drift() convenience function

**Integration Tests Needed:**
- Full workflow test with mock containers and baselines
- Real infrastructure test (if safe)
- Edge cases: empty containers, empty baselines, all matched

## Next Steps

1. **Story 1.3 Code Review** - Review comparison logic and severity classification
2. **Story 1.3 QA-Automate** - Create comprehensive pytest test suite
3. **Story 1.4** - Implement Markdown report generation
4. **Story 1.5** - Implement PR generation for drift remediation

## Performance Considerations

**Current Approach:**
- In-memory comparison (no database)
- O(n*m) matching (containers × baselines)
- Deep dict comparison is recursive

**Acceptable For Current Scale:**
- ~10-20 running containers
- ~20-30 git baselines
- Comparison completes in <5 seconds

**Future Optimization (if needed):**
- Index baselines by name for O(1) lookup
- Parallel comparison of services
- Incremental comparison (cache previous results)

---

**Implementation Status**: ✅ COMPLETE (dev)  
**Next Step**: Code review  
**Lines of Code**: 773 (547 comparator + 226 orchestrator)
