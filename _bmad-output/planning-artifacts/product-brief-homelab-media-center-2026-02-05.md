---
stepsCompleted: []
inputDocuments: []
date: 2026-02-05
author: Larry
---

# Product Brief: Homelab Media Center

## Executive Summary

A self-hosted media automation pipeline that enables on-demand media requests through Overseerr, automatically downloads content via the *arr stack (Sonarr, Radarr, Lidarr, Prowlarr, Bazarr, Readarr), and hosts it on Plex Media Server. The system is managed as Infrastructure-as-Code across two repositories (homelab-infra for provisioning, homelab-apps for Docker Compose stacks), with the current MVP focused on auditing configuration drift, cleaning up repositories, and validating the end-to-end media pipeline functionality.

---

## Core Vision

### Problem Statement

**Current State:** Services were deployed months ago via homelab-infra (Terraform/Ansible) and homelab-apps (Docker Compose). Since then, configurations have been modified through CLI/SSH without updating git repositories. This creates **configuration drift** - the running infrastructure no longer matches the documented IaC state.

**Immediate Problem:** 
- Unknown what changes were made directly on hosts
- Git repos are stale and potentially incorrect
- Cannot confidently make infrastructure changes (fear of breaking working services)
- Media pipeline may have misconfigurations preventing proper automation

### Problem Impact

**Configuration Drift Consequences:**
- Git repos are unreliable as source of truth
- Cannot reproduce infrastructure from code
- Future changes risk breaking working services
- No clear documentation of current state

**Media Pipeline Impact:**
- Overseerr requests may not trigger proper downloads
- *arr stack integration may be misconfigured
- Download paths, quality profiles, or indexer configs may be wrong
- Plex may not see downloaded media

### MVP Goal

**Phase 1 - Audit & Remediation:**
1. **Audit Current State:** Compare running configurations vs git repos (find drift)
2. **Update Repositories:** Backport all live changes to git (make repos match reality)
3. **Clean Up Repos:** Remove stale configs, organize structure, improve documentation
4. **Validate Media Pipeline:** Test Overseerr request → *arr download → Plex availability flow

**Success Criteria:**
- Git repos accurately reflect running infrastructure
- Test media request completes end-to-end successfully
- Documentation is current and correct

### Target Users

**Primary User:** Larry (Tom) - Homelab operator
- **Role:** Solo infrastructure operator managing Proxmox-based homelab
- **Environment:** Windows workstation → VS Code Remote SSH → dev-vm (192.168.50.115)
- **Current Pain:** Configuration drift from CLI changes, uncertain infrastructure state
- **Desired Outcome:** Clean, documented infrastructure that matches git repos; working media automation

**Secondary Users:** Family members
- **Role:** Media consumers (Plex users)
- **Need:** Reliable media availability, ability to request content
- **Pain Point:** Broken automation = no new content

### Key Differentiators

**This is NOT:**
- A new deployment (services already running)
- Building homelab-playbook methodology documentation
- Creating new features

**This IS:**
- Infrastructure remediation (fixing drift)
- Validation and cleanup
- Ensuring media automation works as intended
- Establishing clean baseline for future work

## Success Metrics

**MVP Complete When:**
1. ✅ All configuration drift identified (audit report)
2. ✅ Git repos updated to match running state
3. ✅ Repos cleaned and organized
4. ✅ End-to-end media test passes: Overseerr request → *arr download → Plex library update
5. ✅ Documentation reflects current architecture

**Validation Test:**
- Request a movie via Overseerr
- Radarr searches indexers via Prowlarr
- qBittorrent downloads via VPN
- Radarr moves file to Plex media folder
- Plex detects and adds movie to library
- Movie playable on Plex client

## Out of Scope (Post-MVP)

- Adding new services
- Infrastructure upgrades (Proxmox, Docker versions)
- Authentik SSO integration
- Prometheus monitoring expansion
- Restic backup automation

---

**Next Step:** Create PRD to define detailed requirements for drift audit, repo cleanup, and pipeline validation.
