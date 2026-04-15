# Story 2.1: Deploy Prometheus with Scrape Targets for All Services

**Epic:** 2 - Observability and Alerting
**Status:** done
**Implements:** FR7
**Target repo:** homelab-apps

---

## User Story

**As a** homelab operator,
**I want** Prometheus collecting metrics from all running containers and host nodes,
**So that** I have the raw data foundation for dashboards and alerting.

---

## Acceptance Criteria

### AC1: Prometheus scrapes all services
**Given** the observability stack is deployed on ct-docker-01
**When** Prometheus starts up
**Then** it scrapes metrics from all running containers that expose `/metrics` endpoints
**And** it scrapes host-level metrics (node-exporter and cAdvisor) on ct-docker-01
**And** scrape targets are defined in configuration files (not runtime state)

### AC2: ct-media-01 host metrics
**Given** node-exporter is running on ct-media-01 (VMID 200, IP .200)
**When** Prometheus evaluates scrape targets
**Then** it collects host metrics from ct-media-01 via the node-exporter endpoint at `ct-media-01.internal:9100`
**And** the target is labeled with `instance: ct-media-01`

### AC3: New service discovery
**Given** a new service is deployed that exposes `/metrics`
**When** its scrape target is added to `prometheus.yml`
**Then** Prometheus discovers and scrapes it within one scrape interval (15s default)

### AC4: SMTP relay scrape target
**Given** the smtp-relay service from Epic 1 is running
**When** Prometheus evaluates scrape targets
**Then** it attempts to scrape the SMTP relay (if metrics are exposed)
**And** the scrape target is present in the configuration for future metrics enablement

---

## Technical Context

### Existing Stack
- `stacks/observability/docker-compose.yml` already defines: prometheus, grafana, node-exporter, cadvisor
- `stacks/observability/config/prometheus.yml` has 5 scrape jobs: prometheus, node-exporter, cadvisor, docker, traefik, portainer
- All services use `proxy` and `monitoring` networks

### Services to Add as Scrape Targets

**ct-docker-01 services (on Docker network):**
- n8n (port 5678, `/healthz` only - no native /metrics)
- pihole (port 80, Pi-hole API - needs pihole-exporter or API scrape)
- traefik (port 8080, `/metrics` - already configured)
- portainer (port 9000 - already configured)
- homepage (port 3000, no /metrics)
- gluetun (port 8000, `/metrics` if enabled)
- qbittorrent (port 8080, no native /metrics)
- sabnzbd (port 8080, no native /metrics)
- sonarr (port 8989, no native /metrics)
- radarr (port 7878, no native /metrics)
- prowlarr (port 9696, no native /metrics)
- bazarr (port 6767, no native /metrics)
- organizr (port 80, no /metrics)
- organizr-db (MariaDB, no /metrics exposed)
- obsidian-couchdb (port 5984, `/_stats` endpoint)
- smtp-relay (port 25, no /metrics)
- prometheus (port 9090, already configured)
- grafana (port 3000, `/metrics`)
- node-exporter (port 9100, already configured)
- cadvisor (port 8080, already configured)

**ct-media-01 services (cross-host, IP-based targets):**
- plex (port 32400)
- tautulli (port 8181)
- jellyfin (port 8096)
- jellyseerr (port 5055)
- overseerr (port 5055)
- threadfin (port 34400)
- tuliprox (port 8088)
- tailscale (no /metrics)
- portainer-agent (port 9001)

### Key Decisions
- Most services do NOT expose native `/metrics` endpoints
- cAdvisor already collects per-container resource metrics (CPU, memory, network, disk I/O) - this is the PRIMARY source for FR7
- node-exporter collects host-level metrics (CPU, memory, disk, network) - already configured for ct-docker-01
- Add node-exporter on ct-media-01 as cross-host scrape target
- Grafana exposes `/metrics` - add as scrape target
- Services without /metrics are monitored via cAdvisor container metrics (sufficient for FR7)

---

## Implementation Plan

### Files Modified
1. `stacks/observability/config/prometheus.yml` - Add comprehensive scrape targets
2. `stacks/observability/docker-compose.yml` - No changes needed (stack already complete for 2.1)

### Scrape Target Strategy
1. **Self-monitoring:** prometheus (existing)
2. **Host metrics ct-docker-01:** node-exporter (existing)
3. **Host metrics ct-media-01:** node-exporter at ct-media-01 IP (NEW)
4. **Container metrics:** cadvisor (existing) - covers ALL containers automatically
5. **Docker daemon:** host.docker.internal:9323 (existing)
6. **Traefik:** traefik:8080 (existing)
7. **Grafana:** grafana:3000/metrics (NEW)
8. **Portainer:** portainer:9000 (existing, fix metrics_path)

---

## Dev Checklist

- [x] Read existing prometheus.yml and docker-compose.yml
- [x] Identify all services across both hosts
- [x] Determine which services expose /metrics endpoints
- [x] Add ct-media-01 node-exporter scrape target
- [x] Add Grafana metrics scrape target
- [x] Add relabel configs for instance identification
- [x] Organize scrape configs by category with comments
- [x] Code review: verify against FR7, architecture patterns
- [x] Apply review fixes
