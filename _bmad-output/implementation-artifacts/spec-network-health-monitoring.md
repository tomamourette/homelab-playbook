---
title: 'Deploy network health monitoring with blackbox and SNMP exporters'
type: 'feature'
created: '2026-04-07'
status: 'done'
baseline_commit: 'f8acce0'
context:
  - homelab-apps/stacks/observability/docker-compose.yml
  - homelab-apps/stacks/observability/config/prometheus.yml
---

<frozen-after-approval reason="human-owned intent -- do not modify unless human renegotiates">

## Intent

**Problem:** Network issues (packet drops, latency spikes, ISP outages, router overload) are only discovered when something breaks -- like Teams calls dropping. There's no proactive monitoring or alerting for network health despite having Prometheus + Grafana already running.

**Approach:** Add blackbox exporter (ping/HTTP probes) and SNMP exporter (router metrics) to the existing observability stack on ct-docker-01. Add Prometheus scrape configs, alert rules, and a Grafana "Network Health" dashboard.

## Boundaries & Constraints

**Always:**
- Add new services to the existing `observability/docker-compose.yml` (same stack)
- Follow existing Prometheus config conventions (15s scrape interval, homelab labels)
- Follow existing alert naming convention (`{Domain}{Condition}`)
- Follow existing Grafana provisioning pattern (JSON dashboard in `dashboards/`)
- Use the same Traefik auth middleware for any exposed UIs

**Ask First:**
- Enabling SNMP on the ASUS router (requires `nvram set` commands)
- Adding alert rules that send email notifications

**Never:**
- Replace or modify existing scrape targets
- Change existing alert rules or dashboards
- Install software on the Proxmox hosts for this story

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Internet up | Blackbox probes google.com, 1.1.1.1 | probe_success=1, latency < 500ms | N/A |
| Internet down | ISP outage | probe_success=0 for all external targets | Alert fires after 2min |
| Router unreachable | Router off/rebooting | SNMP scrape fails, ICMP probe fails | Alert fires, scrape marked down |
| High latency | Network congestion | probe_duration_seconds > threshold | Alert fires after 5min |
| Target added later | User adds new probe target | Edit prometheus.yml, restart Prometheus | N/A |

</frozen-after-approval>

## Code Map

- `homelab-apps/stacks/observability/docker-compose.yml` -- Add blackbox-exporter and snmp-exporter services
- `homelab-apps/stacks/observability/config/blackbox.yml` -- Blackbox exporter module config (ICMP, HTTP, DNS)
- `homelab-apps/stacks/observability/config/prometheus.yml` -- Add scrape jobs for blackbox and SNMP targets
- `homelab-apps/stacks/observability/config/alerting/network-alerts.yml` -- Network-specific alert rules
- `homelab-apps/stacks/observability/dashboards/network-health.json` -- Grafana dashboard

## Tasks & Acceptance

**Execution:**
- [x] `homelab-apps/stacks/observability/config/blackbox.yml` -- Define ICMP, HTTP, and DNS probe modules
- [x] `homelab-apps/stacks/observability/docker-compose.yml` -- Add blackbox-exporter service (also bumped Prometheus memory 512M->1024M to fix OOM)
- [x] `homelab-apps/stacks/observability/config/prometheus.yml` -- Add blackbox probe scrape jobs (gateway, ISP, Google, Teams, Cloudflare DNS, internal services)
- [x] `homelab-apps/stacks/observability/config/alerting/network-alerts.yml` -- Alert rules: InternetDown, HighLatency, GatewayUnreachable, DNSResolutionSlow, ExternalServiceDown
- [x] `homelab-apps/stacks/observability/dashboards/network-health.json` -- Grafana dashboard with latency graphs, uptime panels, probe status table

**Acceptance Criteria:**
- Given the stack is deployed, when `curl localhost:9115/probe?target=google.com&module=http_2xx` is called, then blackbox exporter returns `probe_success 1`
- Given the stack is deployed, when Prometheus scrapes the blackbox targets, then `probe_success` and `probe_duration_seconds` metrics appear in Prometheus
- Given the internet is reachable, when the Grafana Network Health dashboard loads, then it shows latency graphs and uptime status for all probe targets
- Given a probe target is unreachable for 2+ minutes, when Prometheus evaluates alert rules, then the appropriate alert fires

## Verification

**Commands:**
- `ssh ct-docker-01 "docker ps | grep blackbox"` -- expected: blackbox-exporter container running
- `curl -s http://192.168.50.194:9115/probe?target=google.com&module=http_2xx | grep probe_success` -- expected: `probe_success 1`
- `curl -s http://192.168.50.194:9090/api/v1/targets | jq '.data.activeTargets[] | select(.labels.job | test("blackbox")) | .health'` -- expected: "up"

## Spec Change Log

- **Review R1 (2026-04-07):** 5 patches applied from adversarial review:
  1. InternetDown: `min()` -> `max()` so alert fires only when ALL external probes fail
  2. Internal probes: `https://` -> `http://` with `http_2xx` module (services don't serve TLS directly)
  3. Added `BlackboxExporterDown` alert using `absent(probe_success)`
  4. HighLatency: added `and probe_success == 1` guard to avoid firing on timeouts
  5. Added `cap_drop: ALL` to blackbox-exporter for security consistency

## Suggested Review Order

- Alert rules: InternetDown logic, HighLatency guard, new BlackboxExporterDown
  [`network-alerts.yml:7`](../../homelab-apps/stacks/observability/config/alerting/network-alerts.yml#L7)

- Blackbox probe modules: ICMP, HTTP, DNS definitions
  [`blackbox.yml:1`](../../homelab-apps/stacks/observability/config/blackbox.yml#L1)

- Prometheus scrape jobs: 4 blackbox jobs with relabel routing
  [`prometheus.yml:150`](../../homelab-apps/stacks/observability/config/prometheus.yml#L150)

- Docker Compose: blackbox-exporter service with NET_RAW capability
  [`docker-compose.yml:199`](../../homelab-apps/stacks/observability/docker-compose.yml#L199)

- Grafana dashboard: 6 panels (status, latency, uptime)
  [`network-health.json:1`](../../homelab-apps/stacks/observability/dashboards/network-health.json#L1)
