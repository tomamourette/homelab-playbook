---
stepsCompleted: ['step-01-validate-prerequisites', 'step-02-design-epics', 'step-03-create-stories']
inputDocuments:
  - "homelab-playbook/_bmad-output/planning-artifacts/prd-homelab-media-center.md"
  - "homelab-playbook/_bmad-output/planning-artifacts/architecture-homelab-media-center.md"
  - "homelab-playbook/_bmad-output/planning-artifacts/product-brief-homelab-media-center-2026-02-05.md"
workflowType: 'epics-and-stories'
project_name: 'homelab-media-center'
user_name: 'Larry'
date: '2026-02-05'
---

# Epics and Stories - Homelab Media Center

**Author:** Larry  
**Date:** 2026-02-05  
**Project:** Homelab Media Center - Configuration Remediation & Pipeline Validation

## Requirements Extraction

### Functional Requirements (from PRD)

**FR-1: Configuration Drift Detection**
- FR-1.1: Repository Discovery - Identify all IaC repositories
- FR-1.2: Running State Capture - Capture current running configurations from target hosts
- FR-1.3: Configuration Comparison - Compare running vs git repository versions
- FR-1.4: Drift Identification - Identify all configuration mismatches
- FR-1.5: Drift Reporting - Generate comprehensive drift audit report
- FR-1.6: Change Classification - Categorize drift by severity

**FR-2: Repository Remediation**
- FR-2.1: Configuration Backport - Update git repositories to match running state
- FR-2.2: Pull Request Generation - Create Pull Requests for each drift remediation
- FR-2.3: Change Documentation - Document reason for each configuration change
- FR-2.4: Repository Cleanup - Identify and remove stale configuration files
- FR-2.5: Structure Validation - Ensure repository structure follows conventions
- FR-2.6: Documentation Update - Update README and documentation

**FR-3: Media Pipeline Validation**
- FR-3.1: Service Health Check - Verify all media stack services running
- FR-3.2: API Connectivity Test - Validate API connections between services
- FR-3.3: Indexer Validation - Test Prowlarr indexer search functionality
- FR-3.4: VPN Routing Check - Confirm qBittorrent traffic routes through VPN
- FR-3.5: Download Path Validation - Verify download paths match import paths
- FR-3.6: Plex Library Scan - Test Plex automatic library scanning
- FR-3.7: End-to-End Test - Execute test media request through full pipeline
- FR-3.8: Failure Reporting - Report specific failure points when tests fail

**FR-4: Configuration Fix Generation**
- FR-4.1: API Key Synchronization - Update stale API keys across services
- FR-4.2: Path Alignment - Align download and import paths between services
- FR-4.3: Settings Validation - Verify service settings match recommended configs
- FR-4.4: Fix Proposal - Generate configuration fixes as Pull Requests
- FR-4.5: Human Review Gate - Require human approval before applying changes
- FR-4.6: Rollback Capability - Support reverting configuration changes via git

**FR-5: Media Content Automation**
- FR-5.1: Content Request Interface - Users request media via Overseerr
- FR-5.2: Automatic Search - Radarr/Sonarr search via Prowlarr
- FR-5.3: Quality Selection - Select downloads based on quality profiles
- FR-5.4: Secure Download - qBittorrent downloads through VPN tunnel
- FR-5.5: Automatic Import - Radarr/Sonarr import to Plex media folders
- FR-5.6: Library Update - Plex automatically scans and adds new media
- FR-5.7: Request Status - Users receive notifications when content available
- FR-5.8: Content Playback - Users play media on Plex clients

**FR-6: System Documentation**
- FR-6.1: Service Catalog - Maintain current list of deployed services
- FR-6.2: Configuration Documentation - Document current configuration state in git
- FR-6.3: Architecture Diagrams - Maintain infrastructure topology documentation
- FR-6.4: Audit Trail - Maintain history of configuration changes via git commits
- FR-6.5: Troubleshooting Guides - Provide runbooks for common failure scenarios
- FR-6.6: Dependency Mapping - Document service integration dependencies

### Non-Functional Requirements (from PRD)

**NFR-1: Reliability**
- Media pipeline >95% success rate
- Service health checks detect failures within 5 minutes
- Configuration changes <15 minutes downtime
- Rollback capability <10 minutes

**NFR-2: Performance**
- Configuration drift audit <30 minutes
- Drift report generation <5 minutes
- Content search <30 seconds
- Download initiation <2 minutes
- Plex library scan <15 minutes
- End-to-end test <24 hours

**NFR-3: Security**
- All services internal network only
- Download traffic exclusively through VPN
- Service-to-service API keys (no plaintext passwords)
- Sensitive credentials in environment files (not git)

**NFR-4: Maintainability**
- 100% of running configs version-controlled in git
- All configuration changes via Pull Request
- Git commit history complete audit trail
- Repositories follow clear conventions

**NFR-5: Operational Monitoring**
- Service health status queryable on-demand
- Configuration drift detectable through automated audits
- Integration failures generate diagnostic reports
- Test results provide clear pass/fail with failure details

**NFR-6: Recoverability**
- Infrastructure reproducible from git repositories
- Service configs restorable from backups within 1 hour
- Failed deployments revertable via git revert within 10 minutes
- Documentation enables rebuilding from scratch

### Technical Context (from Architecture)

**Implementation Approach:**
- Drift Detection: Python scripts + Docker SDK
- Repository Remediation: Automated PR workflow with AI review
- Pipeline Validation: pytest test framework
- AI Coordination: OpenClaw supervisor spawns Claude Code CLI, autonomous merge

**Key Architectural Decisions:**
- Python + Docker SDK for container inspection
- PR-based workflow for all changes
- pytest for structured integration testing
- Autonomous merge after supervisor validation

**Implementation Patterns:**
- Docker Compose v2, pinned tags, Traefik v3 labels
- Conventional commits, PR process
- PEP 8, type hints, pytest fixtures

**Project Structure:**
- `homelab-playbook/tools/drift-detection/` - Detection tooling
- `homelab-playbook/tests/pipeline/` - Integration tests
- Target repos: `homelab-infra/`, `homelab-apps/`

## Epic List

### Epic 1: Configuration Drift Discovery & Remediation

**User Outcome:** As an operator, I can audit my infrastructure to identify all configuration drift between running services and git repositories, then automatically remediate that drift through Pull Requests.

**FR Coverage:** FR-1 (all 6 requirements), FR-2 (all 6 requirements)

**Value:** Operator gains confidence in infrastructure state. Git becomes reliable source of truth. Fear of breaking changes eliminated because repos match reality.

### Epic 2: Media Pipeline Validation & Automated Fixes

**User Outcome:** As an operator, I can validate the entire media automation pipeline (Overseerr → *arr → qBittorrent → Plex) to identify integration failures, then automatically generate configuration fixes for broken integrations.

**FR Coverage:** FR-3 (all 8 requirements), FR-4 (all 6 requirements), FR-5 (validation aspects)

**Value:** Operator knows the media pipeline works end-to-end. Family can request content with confidence. Broken integrations are automatically detected and fixed.

### Epic 3: System Documentation & Observability

**User Outcome:** As an operator, I can view comprehensive system documentation including service catalog, architecture diagrams, configuration audit trail, and troubleshooting guides.

**FR Coverage:** FR-6 (all 6 requirements), NFR-5 (Operational Monitoring)

**Value:** Operator has complete visibility into infrastructure. New services are self-documenting. Troubleshooting is guided by runbooks.

## FR Coverage Map

| Epic | Functional Requirements | Estimated Stories |
|------|------------------------|-------------------|
| Epic 1 | FR-1 (6), FR-2 (6) | 8-10 stories |
| Epic 2 | FR-3 (8), FR-4 (6), FR-5 (partial) | 10-12 stories |
| Epic 3 | FR-6 (6), NFR-5 | 6-8 stories |

**Total Coverage:** All 40 FRs across 3 epics (~24-30 implementation stories)

---

## Epic 1: Configuration Drift Discovery & Remediation

**Goal:** Enable operators to audit infrastructure for configuration drift and automatically remediate through Pull Requests.

**FR Coverage:** FR-1.1-1.6 (Drift Detection), FR-2.1-2.6 (Repository Remediation)

### Story 1.1: SSH Connection & Docker Inspection Setup

As an operator,
I want to establish SSH connections to target hosts and inspect running Docker containers,
So that I can extract current runtime configurations for drift analysis.

**Acceptance Criteria:**

**Given** dev-vm has SSH access to ct-docker-01 and ct-media-01  
**When** the drift detector connects to a target host  
**Then** it successfully authenticates via SSH key  
**And** uses Docker SDK to list all running containers  
**And** extracts container inspect data (labels, networks, volumes, environment)  
**And** handles connection failures gracefully with clear error messages

**Technical Notes:**
- Use Python `paramiko` or `fabric` for SSH
- Use `docker` SDK for container inspection
- Store host credentials in environment config

---

### Story 1.2: Git Repository Baseline Loader

As an operator,
I want to load baseline configurations from git repositories,
So that I can compare them against running container states.

**Acceptance Criteria:**

**Given** homelab-apps and homelab-infra repos are cloned locally  
**When** the drift detector loads git baselines  
**Then** it parses all Docker Compose files in `homelab-apps/stacks/*/`  
**And** handles endpoint-specific overrides (`docker-compose.<endpoint>.yml`)  
**And** extracts compose configurations (services, labels, networks, volumes)  
**And** stores normalized config data for comparison

**Technical Notes:**
- Use `docker-compose` CLI or `python-compose` library to parse YAML
- Merge base + endpoint-specific compose files
- Handle `.env` variable substitution

---

### Story 1.3: Configuration Comparison Engine

As an operator,
I want to compare running container configs against git baselines,
So that I can identify all configuration drift.

**Acceptance Criteria:**

**Given** running container data and git baseline configs loaded  
**When** the comparison engine executes  
**Then** it matches containers to their git compose definitions by service name + stack  
**And** compares labels, networks, volumes, environment variables, image tags  
**And** identifies differences with specific field-level detail  
**And** classifies drift severity (breaking, functional, cosmetic)  
**And** outputs structured diff data (JSON format)

**Technical Notes:**
- Deep dict comparison with path tracking
- Ignore ephemeral fields (container IDs, timestamps)
- Classify based on impact (image tag = breaking, label = cosmetic)

---

### Story 1.4: Drift Report Generation

As an operator,
I want a human-readable drift audit report,
So that I can understand what configurations have diverged from git.

**Acceptance Criteria:**

**Given** structured drift data from comparison engine  
**When** report generation executes  
**Then** it produces Markdown report with:
- Executive summary (X services drifted, Y total differences)
- Per-service drift sections with before/after diffs
- Severity classification per drift item
- Suggested remediation actions  
**And** it produces JSON report for programmatic consumption  
**And** reports are saved to `homelab-playbook/reports/drift-YYYY-MM-DD.md`

**Technical Notes:**
- Use Jinja2 templates for Markdown formatting
- Color-code severity in terminal output
- Include git commit hashes for baseline versions

---

### Story 1.5: Pull Request Generation for Drift Remediation

As an operator,
I want the system to automatically create Pull Requests to backport running configs to git,
So that I can review and approve drift fixes without manual file editing.

**Acceptance Criteria:**

**Given** drift report identifies configuration differences  
**When** PR generation executes for a drifted service  
**Then** it creates a new git branch (`fix/drift-<service>-<timestamp>`)  
**And** updates the compose file in target repo (homelab-apps or homelab-infra)  
**And** commits changes with conventional commit message (`fix(pihole): sync DNS config with running state`)  
**And** opens Pull Request via GitHub/Gitea API with:
- Detailed description of changes
- Link to drift report
- Before/after diff summary  
**And** PR is tagged with `drift-remediation` label

**Technical Notes:**
- Use `PyGithub` or `python-gitlab` for API calls
- One PR per service (not monolithic)
- Include API token from environment config

---

### Story 1.6: Repository Cleanup Detection

As an operator,
I want to identify stale configuration files in git repos,
So that I can remove files for services that no longer exist.

**Acceptance Criteria:**

**Given** git repository contains compose files  
**When** cleanup detection runs  
**Then** it identifies compose files with no corresponding running containers  
**And** flags `.env` files for services not in current deployment  
**And** reports stale files in cleanup report  
**And** optionally generates PR to remove stale files (with confirmation)

**Technical Notes:**
- Compare git service names vs running container names
- Check stack-targets.yml for deployment mappings
- Conservative approach: flag for review, don't auto-delete

---

### Story 1.7: Repository Structure Validation

As an operator,
I want to validate that repositories follow conventions,
So that I can maintain consistency across all infrastructure code.

**Acceptance Criteria:**

**Given** homelab-apps and homelab-infra repositories  
**When** structure validation runs  
**Then** it checks:
- Compose files use v2 syntax (no `version` field)
- Image tags are pinned (no `latest`)
- `.env.sample` exists for each stack
- Traefik labels follow v3 conventions
- Networks reference external `proxy` network  
**And** reports validation failures with remediation guidance  
**And** validation passes/fails overall (exit code 0/1)

**Technical Notes:**
- YAML linting with custom rules
- Regex patterns for convention checks
- Output format compatible with CI/CD

---

### Story 1.8: Documentation Update Automation

As an operator,
I want README files automatically updated when configurations change,
So that documentation stays current with infrastructure state.

**Acceptance Criteria:**

**Given** configuration changes are committed via PRs  
**When** README update automation runs  
**Then** it updates service lists in repository READMEs  
**And** refreshes deployment target mappings in stack-targets.yml  
**And** updates "Last Audit" timestamp in main README  
**And** commits documentation updates to same PR

**Technical Notes:**
- Parse compose files to extract service metadata
- Update markdown tables with current service inventory
- Include in PR automation workflow

---

## Epic 2: Media Pipeline Validation & Automated Fixes

**Goal:** Validate media automation pipeline end-to-end and automatically fix broken integrations.

**FR Coverage:** FR-3.1-3.8 (Pipeline Validation), FR-4.1-4.6 (Fix Generation), FR-5 (validation aspects)

### Story 2.1: pytest Test Framework Setup

As an operator,
I want a pytest test framework for pipeline validation,
So that I can run structured integration tests with clear reporting.

**Acceptance Criteria:**

**Given** homelab-playbook repository  
**When** test framework is set up  
**Then** `tests/pipeline/conftest.py` defines shared fixtures:
- API client factories (Overseerr, Radarr, Sonarr, Prowlarr, qBittorrent, Plex)
- Service connection fixtures (baseURL + API key from environment)
- Test data fixtures (test movie/show IDs)  
**And** `tests/pipeline/requirements.txt` lists dependencies (pytest, requests, python-dotenv)  
**And** tests are runnable via `pytest tests/pipeline/ -v`

**Technical Notes:**
- Use `requests` library for HTTP API calls
- Load credentials from `.env` file
- pytest fixtures provide reusable test setup

---

### Story 2.2: Service Health Check Tests

As an operator,
I want tests that verify all media services are running and reachable,
So that I can quickly identify service availability issues.

**Acceptance Criteria:**

**Given** media services running on ct-media-01  
**When** health check tests execute (`test_service_health.py`)  
**Then** each test verifies:
- Overseerr: HTTP 200 on `/api/v1/status`
- Radarr: HTTP 200 on `/api/v3/system/status` with valid API key
- Sonarr: HTTP 200 on `/api/v3/system/status` with valid API key
- Prowlarr: HTTP 200 on `/api/v1/system/status` with valid API key
- qBittorrent: Login successful, API reachable
- Plex: HTTP 200 on `/status/sessions`  
**And** test failures provide clear diagnostic info (service down, API key invalid, network unreachable)

---

### Story 2.3: Radarr-Prowlarr Integration Test

As an operator,
I want to test that Radarr can successfully communicate with Prowlarr,
So that I know movie searches will work.

**Acceptance Criteria:**

**Given** Radarr and Prowlarr services running  
**When** integration test executes (`test_radarr_prowlarr.py`)  
**Then** test verifies:
- Radarr indexer settings include Prowlarr endpoint
- Radarr can authenticate with Prowlarr API key
- Test indexer connection returns success
- Radarr can query Prowlarr for test movie results  
**And** test fails with specific error if API key is invalid or endpoint unreachable

---

### Story 2.4: qBittorrent VPN Routing Validation

As an operator,
I want to verify qBittorrent traffic routes through Gluetun VPN,
So that I know downloads are secure and IP address is masked.

**Acceptance Criteria:**

**Given** qBittorrent container configured with `network_mode: service:gluetun`  
**When** VPN routing test executes (`test_qbittorrent_vpn.py`)  
**Then** test verifies:
- qBittorrent container network mode is attached to Gluetun service
- IP leak test: query external IP via qBittorrent API matches VPN provider IP (not home IP)
- Gluetun healthcheck status is healthy  
**And** test fails if qBittorrent uses home IP (VPN leak detected)

**Technical Notes:**
- Use qBittorrent web API to check external IP
- Compare against known home IP range (192.168.50.x)
- May require test torrent or IP check service

---

### Story 2.5: Download Path Validation Test

As an operator,
I want to verify download paths match between qBittorrent and *arr import folders,
So that I know completed downloads will be detected and imported.

**Acceptance Criteria:**

**Given** qBittorrent and Radarr/Sonarr configurations  
**When** path validation test executes (`test_download_paths.py`)  
**Then** test verifies:
- qBittorrent download directory matches Radarr's "Remote Path Mapping" or import path
- Sonarr download directory matches configured import path
- Paths are accessible from both containers (shared volume)  
**And** test fails if paths don't align with specific mismatch details

---

### Story 2.6: Plex Library Auto-Scan Test

As an operator,
I want to test that Plex automatically scans for new media,
So that I know new downloads will appear in the library without manual intervention.

**Acceptance Criteria:**

**Given** Plex Media Server configured  
**When** auto-scan test executes (`test_plex_autoscan.py`)  
**Then** test verifies:
- Plex library settings have "Scan my library automatically" enabled
- Plex library paths match Radarr/Sonarr output folders  
**And** optionally: test creates dummy media file, waits, verifies Plex detects it  
**And** test fails if auto-scan is disabled or paths don't match

---

### Story 2.7: End-to-End Pipeline Test

As an operator,
I want an end-to-end test that validates a complete media request flow,
So that I can confirm the entire pipeline works from request to playback.

**Acceptance Criteria:**

**Given** all media services configured and running  
**When** end-to-end test executes (`test_end_to_end.py`)  
**Then** test performs:
1. (Optional) Request test movie via Overseerr API
2. Verify Radarr receives request
3. (Simulated) Verify Radarr searches Prowlarr for release
4. (Simulated) Verify qBittorrent receives download job
5. (Manual verification step) Confirm download completes
6. Verify Radarr imports file to Plex folder
7. Verify Plex library includes new movie  
**And** test provides detailed step-by-step status report  
**And** test can run in "dry-run" mode (checks without triggering real download)

**Technical Notes:**
- Use test movie with known availability
- May require test completion over hours (skip in CI, run manually)
- Document manual verification steps

---

### Story 2.8: API Key Synchronization Fix Generator

As an operator,
I want the system to detect stale API keys and generate PRs to update them,
So that service integrations are automatically repaired.

**Acceptance Criteria:**

**Given** test results identify API key authentication failures  
**When** fix generator runs for API key issues  
**Then** it extracts current valid API keys from running services  
**And** updates compose files with correct API key environment variables  
**And** creates PR with updated configs and explanation of fix

**Technical Notes:**
- Extract API keys from service web UI configs (if accessible)
- Update `.env.sample` with placeholder, actual `.env` handled by operator
- PR description explains which API keys were updated

---

### Story 2.9: Path Alignment Fix Generator

As an operator,
I want the system to detect path mismatches and generate PRs to align them,
So that download/import pipeline works correctly.

**Acceptance Criteria:**

**Given** path validation tests identify mismatched directories  
**When** path alignment fix generator runs  
**Then** it proposes standardized path configuration:
- qBittorrent: `/media/downloads/incomplete`
- Radarr import: `/media/downloads/complete/movies`
- Sonarr import: `/media/downloads/complete/tv`  
**And** generates PR updating compose files with aligned paths  
**And** PR includes volume mount updates if needed

---

### Story 2.10: Pipeline Test Report Generation

As an operator,
I want a consolidated test report showing pipeline health status,
So that I can quickly see what's working and what needs attention.

**Acceptance Criteria:**

**Given** pytest execution completes  
**When** report generation runs  
**Then** it produces:
- HTML report with pass/fail status per test
- Summary dashboard (X/Y tests passing)
- Failed test details with diagnostic info
- Suggested fixes for common failures  
**And** report is saved to `homelab-playbook/reports/pipeline-test-YYYY-MM-DD.html`

---

## Epic 3: System Documentation & Observability

**Goal:** Provide comprehensive system documentation and on-demand observability for infrastructure state.

**FR Coverage:** FR-6.1-6.6 (System Documentation), NFR-5 (Operational Monitoring)

### Story 3.1: Service Catalog Generator

As an operator,
I want an automatically generated service catalog,
So that I have an up-to-date inventory of all deployed services.

**Acceptance Criteria:**

**Given** Docker containers running on ct-docker-01 and ct-media-01  
**When** service catalog generator runs  
**Then** it produces `SERVICE_CATALOG.md` with:
- Table of all services (name, stack, endpoint, image, version)
- Service purpose/description
- Access URLs (via Traefik ingress)
- Health status (running/stopped)  
**And** catalog is committed to homelab-playbook repo

---

### Story 3.2: Architecture Diagram Generator

As an operator,
I want automatically generated architecture diagrams,
So that I can visualize infrastructure topology without manual drawing.

**Acceptance Criteria:**

**Given** infrastructure configuration data  
**When** diagram generator runs  
**Then** it produces diagrams showing:
- Host topology (dev-vm, ct-docker-01, ct-media-01)
- Service deployments per host
- Network connections (Traefik routing, VPN, etc.)
- Data flows (media pipeline)  
**And** diagrams are generated as Mermaid markdown or SVG  
**And** diagrams are saved to `homelab-playbook/docs/architecture/`

**Technical Notes:**
- Use Mermaid.js syntax for diagram-as-code
- Generate from service catalog + network data

---

### Story 3.3: Configuration Audit Trail Viewer

As an operator,
I want to view git commit history for configuration changes,
So that I can audit who changed what and when.

**Acceptance Criteria:**

**Given** git repositories with commit history  
**When** audit trail viewer runs  
**Then** it generates report showing:
- Recent configuration changes (last 30 days)
- Commit messages grouped by stack/service
- Links to full diffs on GitHub/Gitea  
**And** report is saved as `AUDIT_TRAIL.md`

---

### Story 3.4: Troubleshooting Runbook Generator

As an operator,
I want automatically generated troubleshooting runbooks for common failures,
So that I can quickly resolve issues without searching documentation.

**Acceptance Criteria:**

**Given** common failure patterns from test results  
**When** runbook generator runs  
**Then** it creates runbooks for scenarios like:
- "Service won't start" → Check logs, verify dependencies
- "Pipeline test fails" → Validate API keys, check paths
- "Drift detected" → Review PR, verify changes safe  
**And** runbooks are saved to `homelab-playbook/docs/troubleshooting/`

---

### Story 3.5: Service Dependency Map

As an operator,
I want a dependency map showing which services depend on each other,
So that I understand impact of service changes or failures.

**Acceptance Criteria:**

**Given** service integration data  
**When** dependency map generator runs  
**Then** it produces diagram showing:
- Service dependencies (Radarr → Prowlarr, qBittorrent)
- Network dependencies (services requiring Traefik)
- Data dependencies (Plex requires Radarr output)  
**And** map is saved as Mermaid diagram in docs

---

### Story 3.6: On-Demand Status Dashboard

As an operator,
I want a command to check current infrastructure status,
So that I can quickly see system health without running full test suite.

**Acceptance Criteria:**

**Given** CLI command `drift-detector status`  
**When** operator runs status check  
**Then** it displays:
- Service health status (running/stopped)
- Last drift audit date and result (clean/drift detected)
- Last pipeline test date and pass/fail
- Quick recommendations (run audit, run tests, etc.)  
**And** status check completes in <30 seconds

**Technical Notes:**
- Read cached status from last test runs
- Optionally: quick ping checks to services
