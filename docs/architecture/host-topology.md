# Host Topology - Homelab Infrastructure

> Auto-generated from drift report and service catalog data (2026-02-08)

```mermaid
graph TB
    subgraph proxmox["Proxmox VE 8.x Hypervisor"]
        direction TB

        subgraph devvm["dev-vm (192.168.50.115) — Ubuntu 22.04"]
            direction LR
            devtools["IaC Tooling<br/>Terraform / Ansible / Python"]
            playbook["homelab-playbook<br/>Drift Detection & Tests"]
            openclaw["OpenClaw Supervisor<br/>Claude Code CLI"]
        end

        subgraph ct_docker["ct-docker-01 (192.168.50.19) — LXC 101"]
            direction TB

            subgraph stack_infra["infra-core"]
                traefik["Traefik v3<br/>Reverse Proxy<br/>:80 :443 :8080"]
                portainer["Portainer<br/>Container Mgmt"]
            end

            subgraph stack_obs["observability"]
                prometheus["Prometheus"]
                grafana["Grafana"]
                nodeexp["Node Exporter"]
                cadvisor["cAdvisor"]
            end

            subgraph stack_org["organizr"]
                organizr["Organizr"]
                organizr_db["Organizr DB"]
            end

            subgraph stack_n8n["automations-n8n"]
                n8n["n8n"]
                n8n_db["n8n DB<br/>PostgreSQL"]
                n8n_redis["n8n Redis"]
            end

            subgraph stack_dns["dns-pihole"]
                pihole["Pi-hole<br/>DNS :53"]
            end

            subgraph stack_ts["networking-tailscale"]
                tailscale["Tailscale<br/>VPN Mesh"]
            end
        end

        subgraph ct_media["ct-media-01 (192.168.50.161) — LXC 102 — iGPU"]
            direction TB

            subgraph stack_plex["media-plex"]
                plex["Plex Media Server<br/>HW Transcoding"]
                tautulli["Tautulli<br/>Plex Analytics"]
            end

            subgraph stack_idx["media-indexers"]
                radarr["Radarr<br/>Movies"]
                sonarr["Sonarr<br/>TV Shows"]
                prowlarr["Prowlarr<br/>Indexer Manager"]
                bazarr["Bazarr<br/>Subtitles"]
            end

            subgraph stack_dl["media-downloads"]
                gluetun["Gluetun<br/>VPN Gateway"]
                qbit["qBittorrent<br/>via Gluetun network"]
                sabnzbd["SABnzbd<br/>Usenet"]
            end

            subgraph stack_pa["portainer-agent"]
                pa["Portainer Agent"]
            end

            subgraph stack_unmanaged["unmanaged"]
                overseerr["Overseerr<br/>Request Mgmt"]
                flaresolverr["FlareSolverr"]
                viniplay["Viniplay"]
            end
        end
    end

    devvm -- "SSH + Docker SDK" --> ct_docker
    devvm -- "SSH + Docker SDK" --> ct_media
    portainer -- "Agent API" --> pa

    classDef host fill:#1a1a2e,stroke:#16213e,color:#e0e0e0
    classDef stack fill:#0f3460,stroke:#533483,color:#e0e0e0
    classDef service fill:#533483,stroke:#e94560,color:#fff
    classDef unmanaged fill:#4a4a4a,stroke:#888,color:#ccc,stroke-dasharray: 5 5

    class devvm,ct_docker,ct_media host
    class stack_infra,stack_obs,stack_org,stack_n8n,stack_dns,stack_ts,stack_plex,stack_idx,stack_dl,stack_pa stack
    class traefik,portainer,prometheus,grafana,nodeexp,cadvisor,organizr,organizr_db,n8n,n8n_db,n8n_redis,pihole,tailscale,plex,tautulli,radarr,sonarr,prowlarr,bazarr,gluetun,qbit,sabnzbd,pa service
    class overseerr,flaresolverr,viniplay,stack_unmanaged unmanaged
```

## Host Summary

| Host | LXC ID | IP Address | Role | Stacks | Services |
|------|--------|------------|------|--------|----------|
| dev-vm | — | 192.168.50.115 | Orchestration | — | Terraform, Ansible, Python tooling |
| ct-docker-01 | 101 | 192.168.50.19 | Application Host | 6 | 12 |
| ct-media-01 | 102 | 192.168.50.161 | Media Server | 4 (+unmanaged) | 14 |
