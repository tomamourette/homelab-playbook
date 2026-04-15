# Deployment Lessons Learned

## Epic 1: SMTP Relay

### Issue 1: Docker Compose env_file + environment interpolation
- **Problem:** `env_file` loads variables INTO the container at runtime, but `${VAR}` in the `environment:` section is resolved by Docker Compose at PARSE TIME from the host shell — where those variables don't exist.
- **Fix:** Either hardcode values in `environment:`, or use only `env_file` and let the container read its own env vars.
- **Impact:** ALL stacks using `env_file` + `environment: ${VAR}` pattern are affected.

### Issue 2: Postfix requires setgid (no-new-privileges incompatible)
- **Problem:** `security_opt: no-new-privileges:true` prevents Postfix's `postdrop` binary from using its setgid bit, causing `Permission denied` on maildrop.
- **Fix:** Remove `no-new-privileges` for the smtp-relay container.
- **Impact:** SMTP relay only. Other containers that don't use setgid binaries can keep it.

### Issue 3: Postfix spool bind mount permissions
- **Problem:** Bind-mounting `/var/spool/postfix` from host creates directories owned by root, but Postfix needs specific ownership (postfix:postdrop).
- **Fix:** Remove spool bind mount. Mail queue is ephemeral — doesn't need persistence.

### Issue 4: ALLOWED_SENDER_DOMAINS enforcement
- **Problem:** boky/postfix enforces sender domain restriction. All emails must be FROM an `@bi-services.be` address. Emails from `@gmail.com` are rejected.
- **Fix:** All notification senders must use `@bi-services.be` addresses (homelab@bi-services.be, grafana@bi-services.be, etc.)

### Issue 5: Capabilities needed
- **Required caps for Postfix:** NET_BIND_SERVICE, SETGID, SETUID, SYS_CHROOT, DAC_READ_SEARCH, CHOWN, FOWNER, KILL

## Epic 2: Observability and Alerting

### Issue 6: Prometheus scrape target ordering
- **Problem:** Adding cross-host scrape targets requires ct-media-01 services (node-exporter, cadvisor) to be running first.
- **Fix:** Deploy observability-media on ct-media-01 before configuring Prometheus scrape targets.

### Issue 7: cAdvisor port conflict on ct-media-01
- **Problem:** Default cAdvisor port 8080 conflicts with other services on ct-media-01.
- **Fix:** Use port 8081 for cAdvisor on ct-media-01.
- **Impact:** Prometheus scrape config must use `192.168.50.161:8081` not `:8080`.

### Issue 8: Traefik metrics endpoint
- **Problem:** Prometheus needs to scrape Traefik metrics, but Traefik doesn't expose metrics by default.
- **Fix:** Add `metrics: prometheus:` section to `traefik.yml` static config with `addEntryPointsLabels`, `addRoutersLabels`, `addServicesLabels`.

### Issue 9: Grafana auth proxy for SSO
- **Problem:** Grafana needs to auto-login users authenticated by Authelia, but default config requires separate Grafana login.
- **Fix:** Enable `GF_AUTH_PROXY_ENABLED=true` with `Remote-User` header. Authelia passes the header, Grafana auto-signs-up users.
- **Impact:** Requires `Remote-Name` header in authelia-middleware.yml for display name pass-through.

## Epic 3: Centralized Logging

### Issue 10: Cross-host Loki access
- **Problem:** Promtail on ct-media-01 needs to push logs to Loki on ct-docker-01, but Loki listens on container network only.
- **Fix:** Expose Loki port 3101 on host (maps to container 3100). Promtail on ct-media-01 pushes to `http://192.168.50.194:3101`.
- **Impact:** Port 3101 must be open on ct-docker-01 firewall.

### Issue 11: Promtail Docker socket access
- **Problem:** Promtail needs read access to Docker socket for container log discovery.
- **Fix:** Mount `/var/run/docker.sock:/var/run/docker.sock:ro` and add `DAC_READ_SEARCH` capability.

## Epic 4: SSO Gateway

### Issue 12: Authelia healthcheck command
- **Problem:** `authelia healthcheck` CLI command doesn't work reliably in container context.
- **Fix:** Use `wget --spider http://localhost:9091/api/health` instead.

### Issue 13: Authelia needs SETGID/SETUID capabilities
- **Problem:** Authelia uses `su-exec` internally which requires setgid/setuid.
- **Fix:** Add `cap_add: SETGID, SETUID` to the authelia service.

### Issue 14: Authelia middleware is @file not @docker
- **Problem:** Defining the forward-auth middleware as a Docker label on the Authelia container creates `authelia@docker`. But the file provider creates `authelia@file` which is what services reference.
- **Fix:** Define the middleware in `config/dynamic/authelia-middleware.yml` (file provider). Services use `authelia@file` in their middleware labels.
- **Impact:** ALL services must use `authelia@file` not `authelia@docker`.

### Issue 15: Pi-hole custom.list for new subdomains
- **Problem:** New subdomains (auth.bi-services.be, home.bi-services.be) resolve externally via Cloudflare but not internally.
- **Fix:** Add entries to Pi-hole custom.list pointing to ct-docker-01 IP.

### Issue 16: Home Assistant trusted_proxies
- **Problem:** HA rejects requests from Traefik reverse proxy with 400 errors.
- **Fix:** Add `trusted_proxies` config in HA's `configuration.yaml` to trust the Docker network range.

### Issue 17: Cross-host SMTP relay binding
- **Problem:** SMTP relay bound to 127.0.0.1:25 is only accessible from ct-docker-01 itself.
- **Fix:** Bind to host IP: `192.168.50.194:25:25` so ct-media-01 can reach it.

## Epic 5: Backup and Recovery

### Issue 18: Restic repository initialization
- **Problem:** Restic backup fails on first run if the repository doesn't exist.
- **Fix:** Ansible role runs `restic init` as a pre-task, with `ignore_errors` for existing repos.

### Issue 19: Systemd timer notification on failure
- **Problem:** Systemd services don't send email on failure by default.
- **Fix:** Use `OnFailure=` unit directive pointing to a notification service that sends email via SMTP relay.

## Epic 6: Update Checks

### Issue 20: Diun Docker socket access
- **Problem:** Diun needs Docker socket access to discover running containers and their images.
- **Fix:** Mount `/var/run/docker.sock:/var/run/docker.sock:ro`.

### Issue 21: Tool version check GitHub API rate limiting
- **Problem:** Unauthenticated GitHub API calls are limited to 60/hour.
- **Fix:** Script checks a small set of tools (Terraform, Ansible, Docker Compose, Node.js) and caches results. Daily schedule stays well within limits.

## General Lessons

### Lesson 22: env_file pattern for shared variables
- **Problem:** Each stack duplicated common env vars (TZ, DOMAIN, SMTP settings).
- **Fix:** Created `global.env` at repo root with shared variables. Stacks reference via `env_file: ../../global.env`.
- **Caveat:** env_file values are only available inside the container at runtime, NOT for Docker Compose interpolation.

### Lesson 23: Docker Compose file provider directory
- **Problem:** Traefik file provider watching a single directory picks up ALL YAML files, including non-Traefik configs.
- **Fix:** Use a dedicated `config/dynamic/` subdirectory for Traefik file provider configs. The `config/traefik.yml` static config is separate.
