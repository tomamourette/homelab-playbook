---
stepsCompleted: ['step-01-init', 'step-02-discovery', 'step-03-success', 'step-04-journeys', 'step-05-domain', 'step-06-innovation', 'step-07-project-type', 'step-08-scoping', 'step-09-functional', 'step-10-nonfunctional', 'step-11-polish', 'step-12-complete']
inputDocuments:
  - "homelab-playbook/_bmad-output/planning-artifacts/product-brief-homelab-media-center-2026-02-05.md"
workflowType: 'prd'
briefCount: 1
researchCount: 0
brainstormingCount: 0
projectDocsCount: 0
classification:
  projectType: 'infrastructure_system'
  domain: 'media_automation'
  complexity: 'medium'
  projectContext: 'brownfield'
---

# Product Requirements Document - Homelab Media Center

**Author:** Larry
**Date:** 2026-02-05

## Success Criteria

### User Success

**Operator Success (Larry):**
- **Confidence Restored:** Can make infrastructure changes without fear of breaking working services
- **Truth Established:** Git repos are reliable source of truth (what's in git = what's running)
- **Media Pipeline Works:** Family can request content and it appears in Plex

**Measurable Outcomes:**
- Complete drift audit report within 1 day
- Zero unknown configurations (all changes documented in git)
- Successful end-to-end media test: Overseerr request → Plex playback < 24 hours

**Family Success (Media Consumers):**
- Request movie or show via Overseerr
- Content appears in Plex library automatically
- No manual intervention needed from Larry

### Business Success

**Homelab ROI:**
- **Time Savings:** Future infrastructure changes take minutes (confident deployment from git), not hours (debugging mystery configs)
- **Family Satisfaction:** Media requests fulfilled reliably without manual work
- **Maintenance Burden:** Reduced cognitive load ("What did I change?" → documented git history)

**Measurable Outcomes:**
- Infrastructure change velocity: Can deploy updates confidently within 30 minutes
- Family satisfaction: Zero complaints about missing content (requests work)
- Documentation complete: All services have current config in git

### Technical Success

**Infrastructure Quality:**
- **Zero Configuration Drift:** Running configurations match git repositories 100%
- **Clean Repositories:** No stale files, clear structure, accurate documentation
- **Pipeline Validated:** Overseerr → Prowlarr → Radarr/Sonarr → qBittorrent (VPN) → Plex integration confirmed working
- **Reproducible:** Can rebuild infrastructure from git repos if needed

**Measurable Outcomes:**
- Audit report: All drift identified and documented
- Repository cleanup: Remove stale configs, organize structure
- End-to-end test passes: Request → Download → Plex < 24h

### MVP Success Gate

**Validation Test:**
1. Request test movie via Overseerr
2. Radarr receives request and searches indexers via Prowlarr
3. qBittorrent downloads via VPN (Gluetun container)
4. Radarr detects completed download and moves file to Plex media folder
5. Plex library scan detects new movie and adds to library
6. Movie is playable on Plex client (web, mobile, TV)

**Success = All 6 steps complete without manual intervention**

## Product Scope

### MVP - Configuration Remediation & Validation

**Phase 1: Audit**
- Compare running configurations vs git repos (homelab-infra, homelab-apps)
- Document all configuration drift
- Identify services with manual CLI changes
- Generate audit report

**Phase 2: Repository Sync**
- Update git repos to match running state
- Backport all live changes to IaC files
- Clean up stale configurations
- Improve documentation

**Phase 3: Validation**
- Test media pipeline end-to-end
- Verify all *arr stack integrations
- Confirm Plex library updates work
- Document known issues

### Growth Features (Post-MVP)

**Enhanced Automation:**
- Authentik SSO for *arr apps and Overseerr
- Prometheus metrics for download pipeline
- Restic backups for media library metadata
- Automated quality upgrades (1080p → 4K)

**Pipeline Improvements:**
- Subtitle automation (Bazarr integration)
- Music automation (Lidarr for full library)
- Book automation (Readarr for ebooks/audiobooks)
- Request approval workflow (parental controls)

### Vision (Future)

**Complete Home Media Platform:**
- Multi-user request quotas and permissions
- Integration with TV/streaming service availability checks
- Automatic duplicate detection and upgrade management
- Family dashboard showing request status and library stats

## User Journeys

### Journey 1: Larry - "The Drift Audit" (Operator Mode)

**Opening Scene:**
Saturday morning. Larry needs to add a new service but he's hesitant. Last time he touched infrastructure, something broke. He opens the `homelab-apps` repo and sees the Pi-hole config doesn't match what's running. He changed DNS servers via SSH months ago—never committed. How many other undocumented changes exist?

**Rising Action:**
Larry decides: "Enough. I need to know what's real." He tells me (his AI supervisor): "Audit configuration drift across homelab-infra and homelab-apps."

I spawn Claude Code CLI. The agent:
- SSH into ct-docker-01 and ct-media-01
- Dumps running Docker Compose configs
- Compares against git versions
- Generates drift report

**Climax:**
Audit report: 8 services have drift. Pi-hole DNS, Radarr profiles, qBittorrent paths, Prometheus targets—all CLI changes, none in git. Some Larry remembers. Others he doesn't. One explains why downloads went to the wrong folder last month.

**Resolution:**
Sunday afternoon: coordinated fixes. For each drifted service, Claude Code CLI reads live config, updates git, creates PR. Larry reviews and merges. By evening, git matches reality. He updates README: "Last audit: 2026-02-05. Zero drift." The infrastructure is knowable again.

**Journey Requirements:**
- Automated drift detection (running vs git)
- Multi-service audit capability
- Clear difference reporting
- PR-based remediation
- Documentation updates

---

### Journey 2: Larry - "The Pipeline Test" (Validation Mode)

**Opening Scene:**
Repos are clean. Drift fixed. But Larry doesn't trust the media pipeline. Family complained a requested movie never arrived. The Overseerr → Radarr → qBittorrent flow is broken somewhere.

**Rising Action:**
Larry tests with "Big Buck Bunny" (open source, fast). Requests via Overseerr... nothing happens. Checks Radarr logs manually. Request came through but Radarr can't reach Prowlarr—API key is wrong.

He tells me: "Validate the entire pipeline. Test end-to-end and document failures."

Claude Code CLI checks:
- Overseerr → Radarr integration
- Radarr → Prowlarr API
- Prowlarr indexer search
- qBittorrent VPN routing
- Plex folder permissions

**Climax:**
Three issues found:
1. Prowlarr API key in Radarr is stale
2. qBittorrent download path doesn't match Radarr import folder
3. Plex library scan is manual, not automatic

Fixes generated, PRs created. Larry reviews, merges, deploys.

**Resolution:**
Test retry: Requests "Big Buck Bunny" → Radarr receives ✅ → Prowlarr search ✅ → qBittorrent download (VPN) ✅ → Radarr import ✅ → Plex library add ✅

10 minutes: movie playable. Larry texts wife: "Try Overseerr." She requests a show. 30 min later: "It's on Plex! How'd you fix it?" The pipeline works.

**Journey Requirements:**
- End-to-end pipeline testing
- Service integration validation
- Automated failure detection
- Configuration fix generation
- Success confirmation

---

### Journey 3: Emma (Family) - "Movie Night Request"

**Opening Scene:**
Emma (14) wants to watch "Spider-Man: Across the Spider-Verse" with friends Friday. Checks Plex—not there.

**Rising Action:**
She remembers Dad's request tool. Opens Overseerr, searches "Spider-Man Across," requests. Done. Notification: "Request received."

**Climax:**
Friday afternoon: checks Plex. Spider-Man is there. Didn't ask Dad. It just appeared.

**Resolution:**
Movie night works. Emma doesn't know about Radarr, Prowlarr, or VPNs. She doesn't need to. System works invisibly: "Want → Request → Watch."

**Journey Requirements:**
- Simple request interface (Overseerr)
- No technical knowledge needed
- Automatic fulfillment
- Notifications
- Reliable delivery

---

### Journey Requirements Summary

**Larry (Operator):**
- Configuration drift detection and audit reporting
- Multi-repo comparison (infra + apps vs running state)
- Automated remediation PR generation
- End-to-end pipeline validation testing
- Service integration health checks
- Documentation updates

**Larry (Validator):**
- API connectivity testing
- Download path/permission validation
- Plex library scan configuration
- Success confirmation workflow

**Family (Consumer):**
- Simple request UI (Overseerr)
- Invisible automation
- Reliable delivery
- Status notifications

## Functional Requirements

### FR-1: Configuration Drift Detection

**Capability Area:** Infrastructure Audit

**Requirements:**

- **FR-1.1 Repository Discovery:** System shall identify all infrastructure-as-code repositories (homelab-infra, homelab-apps)
- **FR-1.2 Running State Capture:** System shall capture current running configurations from target hosts (ct-docker-01, ct-media-01)
- **FR-1.3 Configuration Comparison:** System shall compare running configurations against git repository versions
- **FR-1.4 Drift Identification:** System shall identify all configuration mismatches between running state and git
- **FR-1.5 Drift Reporting:** System shall generate comprehensive drift audit report listing all differences
- **FR-1.6 Change Classification:** System shall categorize drift by severity (breaking, functional, cosmetic)

### FR-2: Repository Remediation

**Capability Area:** Infrastructure Synchronization

**Requirements:**

- **FR-2.1 Configuration Backport:** System shall update git repositories to match running configurations
- **FR-2.2 Pull Request Generation:** System shall create Pull Requests for each drift remediation
- **FR-2.3 Change Documentation:** System shall document reason for each configuration change in PR description
- **FR-2.4 Repository Cleanup:** System shall identify and remove stale configuration files
- **FR-2.5 Structure Validation:** System shall ensure repository structure follows conventions
- **FR-2.6 Documentation Update:** System shall update README and documentation to reflect current state

### FR-3: Media Pipeline Validation

**Capability Area:** Service Integration Testing

**Requirements:**

- **FR-3.1 Service Health Check:** System shall verify all media stack services are running (Overseerr, Radarr, Sonarr, Prowlarr, qBittorrent, Plex)
- **FR-3.2 API Connectivity Test:** System shall validate API connections between services (Radarr ↔ Prowlarr, Radarr ↔ qBittorrent, Radarr ↔ Overseerr)
- **FR-3.3 Indexer Validation:** System shall test Prowlarr indexer search functionality
- **FR-3.4 VPN Routing Check:** System shall confirm qBittorrent traffic routes through VPN (Gluetun)
- **FR-3.5 Download Path Validation:** System shall verify download paths match between qBittorrent and *arr import configs
- **FR-3.6 Plex Library Scan:** System shall test Plex automatic library scanning functionality
- **FR-3.7 End-to-End Test:** System shall execute test media request and track through full pipeline (Overseerr → Plex)
- **FR-3.8 Failure Reporting:** System shall report specific failure points when pipeline test fails

### FR-4: Configuration Fix Generation

**Capability Area:** Automated Remediation

**Requirements:**

- **FR-4.1 API Key Synchronization:** System shall update stale API keys across integrated services
- **FR-4.2 Path Alignment:** System shall align download and import paths between services
- **FR-4.3 Settings Validation:** System shall verify service settings match recommended configurations
- **FR-4.4 Fix Proposal:** System shall generate configuration fixes as Pull Requests
- **FR-4.5 Human Review Gate:** System shall require human approval before applying configuration changes
- **FR-4.6 Rollback Capability:** System shall support reverting configuration changes via git

### FR-5: Media Content Automation

**Capability Area:** User-Facing Content Delivery

**Requirements:**

- **FR-5.1 Content Request Interface:** Users shall request media via Overseerr web interface
- **FR-5.2 Automatic Search:** Radarr/Sonarr shall automatically search for requested content via Prowlarr
- **FR-5.3 Quality Selection:** System shall select media downloads based on configured quality profiles
- **FR-5.4 Secure Download:** qBittorrent shall download content through VPN tunnel
- **FR-5.5 Automatic Import:** Radarr/Sonarr shall automatically import completed downloads to Plex media folders
- **FR-5.6 Library Update:** Plex shall automatically scan and add new media to library
- **FR-5.7 Request Status:** Users shall receive notifications when requested content becomes available
- **FR-5.8 Content Playback:** Users shall play media on Plex clients (web, mobile, TV)

### FR-6: System Documentation

**Capability Area:** Knowledge Management

**Requirements:**

- **FR-6.1 Service Catalog:** System shall maintain current list of deployed services
- **FR-6.2 Configuration Documentation:** System shall document current configuration state in git
- **FR-6.3 Architecture Diagrams:** System shall maintain infrastructure topology documentation
- **FR-6.4 Audit Trail:** System shall maintain history of configuration changes via git commits
- **FR-6.5 Troubleshooting Guides:** System shall provide runbooks for common failure scenarios
- **FR-6.6 Dependency Mapping:** System shall document service integration dependencies

## Non-Functional Requirements

### NFR-1: Reliability

**Media Pipeline Availability:**
- Media request pipeline (Overseerr → Plex) shall operate with >95% success rate
- Service health checks shall detect failures within 5 minutes
- Failed requests shall provide clear error messages indicating failure point

**Infrastructure Stability:**
- Configuration changes shall not cause service downtime >15 minutes
- Rollback capability shall restore previous working state within 10 minutes
- Backup configurations shall be maintained for all critical services

### NFR-2: Performance

**Drift Audit Performance:**
- Configuration drift audit shall complete within 30 minutes for all services
- Drift report generation shall complete within 5 minutes

**Media Pipeline Performance:**
- Content search (Prowlarr) shall return results within 30 seconds
- Download initiation (qBittorrent) shall start within 2 minutes of search completion
- Plex library scan shall detect new media within 15 minutes of file arrival
- End-to-end test request shall complete within 24 hours (dependent on download speed)

### NFR-3: Security

**Internal Network Security:**
- All services shall operate on internal network only (no public internet exposure)
- Download traffic shall route exclusively through VPN (Gluetun) - no IP leaks
- Service-to-service communication shall use API keys (no plaintext passwords)
- Sensitive credentials shall be stored in environment files (not committed to git)

**Access Control:**
- Overseerr access limited to family member accounts
- Administrative interfaces (Radarr, Sonarr, Prowlarr, qBittorrent) accessible only from internal network
- Plex shall support user-based content restrictions (parental controls)

### NFR-4: Maintainability

**Infrastructure as Code:**
- 100% of running configurations shall be version-controlled in git
- All configuration changes shall be reviewable via Pull Request
- Git commit history shall provide complete audit trail
- Repositories shall follow clear naming and organization conventions

**Documentation Quality:**
- README files shall be current and accurate
- Service dependencies shall be clearly documented
- Troubleshooting guides shall exist for common failure scenarios
- Architecture documentation shall be updated with infrastructure changes

### NFR-5: Operational Monitoring

**System Observability:**
- Service health status shall be queryable on-demand
- Configuration drift shall be detectable through automated audits
- Integration failures shall generate diagnostic reports
- Test results shall provide clear pass/fail indicators with failure details

**Change Tracking:**
- All infrastructure changes shall be traceable to git commits
- Configuration modifications shall be attributed to specific change requests
- Audit history shall be preserved indefinitely in git

### NFR-6: Recoverability

**Disaster Recovery:**
- Infrastructure shall be reproducible from git repositories
- Service configurations shall be restorable from backups within 1 hour
- Failed deployments shall be revertable via `git revert` within 10 minutes
- Documentation shall enable rebuilding infrastructure from scratch

**Graceful Degradation:**
- Individual service failures shall not cascade to entire pipeline
- Manual workarounds shall be documented for common failure scenarios
- System shall continue operating with degraded functionality during partial outages
