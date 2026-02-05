---
stepsCompleted: ['step-01-init', 'step-02-context', 'step-03-starter', 'step-04-decisions', 'step-05-patterns', 'step-06-structure', 'step-07-validation', 'step-08-complete']
inputDocuments:
  - "homelab-playbook/_bmad-output/planning-artifacts/prd-homelab-media-center.md"
  - "homelab-playbook/_bmad-output/planning-artifacts/product-brief-homelab-media-center-2026-02-05.md"
workflowType: 'architecture'
project_name: 'homelab-media-center'
user_name: 'Larry'
date: '2026-02-05'
---

# Architecture Decision Document - Homelab Media Center

**Author:** Larry  
**Date:** 2026-02-05  
**Project:** Homelab Media Center - Configuration Remediation & Pipeline Validation

_This document builds collaboratively through step-by-step discovery. Sections are appended as we work through each architectural decision together._

## Project Context

### Requirements Summary

**From PRD (40 Functional Requirements across 6 capability areas):**

1. **Configuration Drift Detection (FR-1):** Repository discovery, running state capture, comparison, drift identification, reporting, change classification
2. **Repository Remediation (FR-2):** Configuration backport, PR generation, documentation, cleanup, structure validation
3. **Media Pipeline Validation (FR-3):** Service health checks, API connectivity tests, indexer validation, VPN routing checks, path validation, Plex library scan, end-to-end testing, failure reporting
4. **Configuration Fix Generation (FR-4):** API key sync, path alignment, settings validation, fix proposals, human review gates, rollback capability
5. **Media Content Automation (FR-5):** Request interface, automatic search, quality selection, secure downloads, automatic import, library updates, status notifications, playback
6. **System Documentation (FR-6):** Service catalog, configuration docs, architecture diagrams, audit trail, troubleshooting guides, dependency mapping

**Non-Functional Requirements:**
- **Reliability:** >95% pipeline success rate, <15min downtime tolerance
- **Performance:** <30min drift audit, <24h media delivery
- **Security:** Internal network only, VPN routing, API keys (no plaintext), environment file secrets
- **Maintainability:** 100% git-tracked configs, PR-based changes, audit trail
- **Monitoring:** On-demand status, automated drift detection, diagnostic reports
- **Recoverability:** Reproducible from git, <10min rollback via `git revert`

### Existing Infrastructure

**Hypervisor Platform:**
- Proxmox VE 8.x
- Development VM: 192.168.50.115 (Ubuntu 22.04, full IaC tooling)
- Access: Windows workstation → VS Code Remote SSH → dev-vm

**Target Hosts:**
- **ct-docker-01** (LXC ID: 101)
  - IP: 192.168.50.19
  - Purpose: Application host (Traefik, Portainer, observability, DNS, networking)
  - Deployed stacks: infra-core, observability, organizr, automations-n8n, dns-pihole, networking-tailscale
  
- **ct-media-01** (LXC ID: 102)
  - IP: 192.168.50.161
  - Purpose: Media server with iGPU hardware transcoding
  - Deployed stacks: portainer-agent, media-plex, media-indexers, media-downloads

**Infrastructure-as-Code Repositories:**

1. **homelab-infra** (Terraform + Ansible)
   - VM/CT provisioning via Proxmox provider
   - Host-level configuration (Docker setup, user management)
   - Ansible inventory with dynamic host discovery
   - Helper scripts for deployment and validation

2. **homelab-apps** (Docker Compose + Portainer GitOps)
   - 11 Docker Compose stacks across 2 endpoints
   - Conventions: Compose v2, pinned tags, Traefik v3 labels, external `proxy` network
   - Storage: `/opt/appdata/<stack>/` for app data, `/media/` for media files
   - Deployment: Portainer webhooks (merge to `main` → redeploy changed stacks)
   - Environment: `.env.sample` committed, real `.env` not in git

**Current Media Stack (ct-media-01):**
- **media-plex:** Plex Media Server with iGPU transcoding
- **media-indexers:** Sonarr, Radarr, Prowlarr, Bazarr
- **media-downloads:** qBittorrent + Gluetun (VPN enforcement)
- **Missing:** Overseerr (content request interface) - not currently deployed

**Development Workflow:**
- VS Code Remote SSH from Windows → dev-vm
- Direct network access from dev-vm to all containers
- Terraform/Ansible execution from dev-vm
- Git-based change management with PR reviews

### Project Scale

**MVP Scope:** Medium complexity, 3-phase brownfield remediation
- **Phase 1:** Configuration drift audit (compare running vs git)
- **Phase 2:** Repository synchronization (backport changes, cleanup)
- **Phase 3:** Pipeline validation (end-to-end media request test)

**Implementation Approach:**
- AI supervisor (OpenClaw) coordinates BMAD workflow
- Claude Code CLI executes technical implementation (spawned sessions)
- Generated code targets homelab-infra or homelab-apps repos
- All changes via Pull Request with human review

### Architectural Drivers

**Primary Constraints:**
1. **Brownfield System:** Services running for months, configs modified via CLI/SSH
2. **Unknown Drift:** Extent of config drift is unknown until audit
3. **Multi-Repository:** Changes span homelab-infra (Ansible) and homelab-apps (Compose)
4. **Multi-Host:** Must SSH to ct-docker-01 and ct-media-01 from dev-vm
5. **GitOps Deployment:** Portainer webhooks redeploy on git merge
6. **Human Review Gate:** All automated fixes require PR approval before merge

**Key Technical Challenges:**
1. **Drift Detection:** Compare running Docker Compose configs vs git versions
2. **Endpoint-Specific Overrides:** Handle `docker-compose.<endpoint>.yml` files
3. **API Key Discovery:** Extract runtime API keys for integration validation
4. **VPN Validation:** Confirm qBittorrent traffic routes through Gluetun
5. **Path Validation:** Verify download paths match between qBittorrent and *arr importers
6. **Plex Integration:** Test automatic library scanning functionality

## Core Architectural Decisions

### Decision 1: Drift Detection Implementation

**Approach:** Python script using Docker SDK

**Rationale:**
- Development VM already has Python environment
- `docker-py` library provides structured container introspection
- Programmatic comparison of running configs vs git versions
- Type-safe, testable, maintainable code
- Extensible for additional validation checks

**Implementation:**
- SSH from dev-vm to ct-docker-01 and ct-media-01
- Use Docker SDK to inspect running containers
- Extract compose-equivalent configs from container metadata
- Compare against git repository versions (homelab-apps/stacks/*/docker-compose.yml)
- Handle endpoint-specific overrides (docker-compose.<endpoint>.yml)
- Generate structured drift report (JSON/YAML) with differences

**Key Components:**
- `drift_detector.py` - Main detection engine
- `docker_inspector.py` - Container state extraction
- `git_config_loader.py` - Repository baseline loader
- `diff_generator.py` - Configuration comparison logic

---

### Decision 2: Repository Remediation Workflow

**Approach:** Automated Pull Request generation with autonomous merge

**Rationale:**
- Preserves git audit trail
- Enables review before deployment
- Aligns with existing GitOps workflow (Portainer webhooks)
- Prevents bypassing version control

**Implementation:**
1. Claude Code CLI generates configuration fixes in target repo (homelab-infra or homelab-apps)
2. Creates git branch with descriptive name (`fix/drift-pihole-dns-config`)
3. Commits changes with conventional commit messages
4. Opens Pull Request via GitHub/Gitea API with detailed description
5. AI supervisor reviews PR against requirements and conventions
6. Supervisor merges PR if validation passes
7. Supervisor notifies operator with merge summary
8. Portainer webhook triggers automatic redeployment of changed stacks

**Safety Mechanisms:**
- All changes version-controlled (revertable via `git revert`)
- PR description documents reason for each change
- Supervisor validation before merge (syntax, conventions, requirements)
- Operator notification after merge with link to changes

---

### Decision 3: Pipeline Validation Framework

**Approach:** pytest-based integration testing

**Rationale:**
- Structured test cases for each integration point
- Clear failure diagnostics and reporting
- Extensible for additional service validations
- Maintainable test fixtures and assertions

**Implementation:**
- Test suite in `homelab-playbook/tests/pipeline/`
- Fixtures for service API connections (Overseerr, Radarr, Prowlarr, qBittorrent, Plex)
- Test cases covering:
  - Service health checks (HTTP 200, API reachability)
  - API key validation (authentication success)
  - Integration connectivity (Radarr → Prowlarr API calls)
  - VPN routing (qBittorrent traffic through Gluetun)
  - Path configuration (download paths match import paths)
  - Library scanning (Plex automatic scan enabled)
  - End-to-end flow (Overseerr request → Plex playback)

**Test Execution:**
- Run from dev-vm with network access to target hosts
- Pytest generates structured failure reports
- Failed tests identify specific integration issues
- Test results guide configuration fix generation

---

### Decision 4: AI Agent Workflow Architecture

**Approach:** Supervisor-Coder coordination with autonomous merge

**Architecture:**

```
OpenClaw (Supervisor)
    ↓
  Spawn Claude Code CLI (Coder)
    ↓
  Pass Context:
    - Story requirements (from BMAD artifacts)
    - Architecture decisions (this document)
    - Pattern examples (existing compose files, Ansible roles)
    - Topology data (node IPs, service locations)
    ↓
Claude Code CLI generates implementation:
    - Creates git branch in target repo
    - Writes code (Python scripts, compose files, Ansible playbooks)
    - Commits with conventional messages
    - Opens Pull Request
    ↓
OpenClaw (Supervisor) reviews PR:
    - Validates against story requirements
    - Checks conventions (Compose v2, pinned tags, Traefik labels)
    - Verifies syntax (docker compose config, ansible-playbook --syntax-check)
    - Confirms no hardcoded secrets
    ↓
OpenClaw merges PR (if validation passes)
    ↓
Notifies operator:
    - Merge summary
    - Link to PR and commits
    - Notable changes or observations
    ↓
Portainer webhook redeploys changed stacks
```

**Context Passing to Coder:**
- Story specification file path
- Architecture document (design decisions)
- Example code (reference compose files, Ansible roles)
- Conventions documentation (from CONFIGURATION.md, engineer guide)
- Topology registry (node inventory, service locations)

**Output Validation:**
- Supervisor checks generated code against story acceptance criteria
- Validates adherence to repository conventions
- Tests syntax correctness
- Merges autonomously if validation passes

**Operator Notification:**
- Summary of merged changes
- Links to PR and commits
- Deployment status (Portainer webhook triggered)

## Implementation Patterns & Consistency Rules

### Docker Compose Conventions

**Required patterns for all compose file generation:**

- **Compose v2 syntax:** No `version` field, use modern syntax
- **Pinned image tags:** Never use `latest`, specify exact versions (e.g., `linuxserver/radarr:5.2.6`)
- **Healthchecks:** Define for all long-running services with appropriate intervals
- **Traefik v3 labels** (for HTTP-exposed services):
  ```yaml
  labels:
    - "traefik.enable=true"
    - "traefik.http.routers.<service>.rule=Host(`${APP_HOST}`)"
    - "traefik.http.routers.<service>.entrypoints=web"
    - "traefik.http.services.<service>.loadbalancer.server.port=<internal_port>"
    - "traefik.docker.network=proxy"
  ```
- **Networking:** Join external `proxy` network, no host port publishing unless required (DNS:53, VPN)
- **Volume paths:**
  - Application data: `/opt/appdata/<stack>/<service>`
  - Media files: `/media/tv/`, `/media/movies/`, `/media/downloads/`
- **Environment variables:**
  - `TZ=Europe/Brussels` (timezone)
  - `PUID=1000`, `PGID=1000` (user/group IDs)
  - Secrets via `.env` file (not committed to git)
- **File structure:**
  - `docker-compose.yml` (base configuration)
  - `docker-compose.<endpoint>.yml` (endpoint-specific overrides, e.g., iGPU passthrough)
  - `.env.sample` (template with placeholder values)

### Repository Structure Patterns

**homelab-apps structure:**
```
stacks/<stack-name>/
  docker-compose.yml              # Base compose file
  docker-compose.<endpoint>.yml   # Optional endpoint-specific overrides
  .env.sample                     # Environment template
  config/                         # Optional static config files
```

**homelab-infra structure:**
```
ansible/roles/<role>/
  tasks/main.yml
  defaults/main.yml
  templates/

terraform/modules/<module>/
  main.tf
  variables.tf
  outputs.tf
```

**homelab-playbook structure:**
```
tools/
  drift-detection/
    drift_detector.py           # Main CLI entry point
    docker_inspector.py         # Container state extraction
    git_config_loader.py        # Repository baseline loader
    diff_generator.py           # Configuration comparison
    reporters/
      json_reporter.py
      markdown_reporter.py
      
tests/
  pipeline/
    test_overseerr.py
    test_radarr_integration.py
    test_prowlarr_indexers.py
    test_qbittorrent_vpn.py
    test_plex_library.py
    conftest.py                 # Shared pytest fixtures
```

### Git Commit Conventions

**Format:** Conventional Commits specification

- **Types:** `feat`, `fix`, `docs`, `chore`, `refactor`, `test`
- **Scope:** Stack name or component (optional)
- **Examples:**
  - `feat(drift): add configuration drift detection tool`
  - `fix(pihole): sync DNS upstream servers with running config`
  - `docs(readme): update deployment instructions`
  - `chore(deps): update radarr to version 5.2.6`

**Branch naming:**
- `feat/<feature-name>`
- `fix/<issue-description>`
- Pattern: `<type>/<brief-description-kebab-case>`

### Python Code Patterns

**Style:**
- PEP 8 compliance
- Type hints for function signatures
- Docstrings for public functions (Google style)
- Error handling with specific exceptions

**Testing:**
- pytest framework
- Fixtures in `conftest.py` for shared setup
- One test file per module/integration
- Test naming: `test_<function>_<scenario>.py`
- Assertions with descriptive failure messages

**Example:**
```python
def test_radarr_prowlarr_connectivity(radarr_client, prowlarr_api_key):
    """Verify Radarr can authenticate with Prowlarr API.
    
    Args:
        radarr_client: Configured Radarr API client fixture
        prowlarr_api_key: Valid Prowlarr API key from environment
    """
    response = radarr_client.test_indexer(prowlarr_api_key)
    assert response.success, f"Prowlarr connection failed: {response.error}"
```

### Configuration Management Patterns

**Environment Variables:**
- All secrets and host-specific values in `.env` files
- `.env.sample` committed with placeholders
- Never commit actual `.env` files

**API Keys:**
- Extract from running services during validation
- Store temporarily in test fixtures
- Never hardcode in scripts

**Paths:**
- Use environment variables for host-specific paths
- Default to standard paths (`/opt/appdata`, `/media`)
- Document path requirements in `.env.sample`

### Error Handling Patterns

**Drift Detection:**
- Graceful degradation if host unreachable (report, continue to next)
- Clear error messages identifying which service/host failed
- Structured error reporting (JSON with context)

**Pipeline Validation:**
- Continue testing all integrations even if one fails
- Collect all failures before reporting
- Provide actionable remediation suggestions

**PR Generation:**
- Validate git repository state before branching
- Handle merge conflicts gracefully
- Retry failed API calls with exponential backoff
