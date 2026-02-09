# Network Topology - Homelab Infrastructure

> Auto-generated from drift report and architecture docs (2026-02-08)

## Network Architecture

```mermaid
graph TB
    subgraph lan["LAN — 192.168.50.0/24"]
        direction TB

        subgraph pve["Proxmox VE Host"]
            direction LR
            devvm["dev-vm<br/>192.168.50.115"]
            ct101["ct-docker-01<br/>192.168.50.19<br/>LXC 101"]
            ct102["ct-media-01<br/>192.168.50.161<br/>LXC 102"]
        end

        workstation["Windows Workstation<br/>VS Code Remote SSH"]
    end

    subgraph docker_nets_101["Docker Networks — ct-docker-01"]
        proxy_101["proxy (external)<br/>Traefik ingress network"]
        obs_net["observability_default"]
        n8n_net["automations-n8n_default"]
        org_net["organizr_default"]
    end

    subgraph docker_nets_102["Docker Networks — ct-media-01"]
        proxy_102["proxy (external)<br/>Traefik ingress network"]
        media_net["media-plex_media"]
        idx_net["media-indexers_default"]
        dl_net["media-downloads_default"]
    end

    subgraph vpn["VPN / Overlay"]
        tailscale_net["Tailscale Mesh<br/>100.x.x.x/32"]
        gluetun_tun["Gluetun VPN Tunnel<br/>Provider VPN IP"]
    end

    internet(["Internet<br/>Cloudflare DNS / VPN Provider"])

    workstation -- "SSH :22" --> devvm
    devvm -- "SSH :22" --> ct101
    devvm -- "SSH :22" --> ct102

    ct101 --> proxy_101
    ct101 --> obs_net
    ct101 --> n8n_net
    ct101 --> org_net

    ct102 --> proxy_102
    ct102 --> media_net
    ct102 --> idx_net
    ct102 --> dl_net

    proxy_101 -. "HTTP :80 / HTTPS :443" .-> internet
    tailscale_net -. "WireGuard :41641" .-> internet
    gluetun_tun -. "OpenVPN / WireGuard" .-> internet

    classDef host fill:#1a1a2e,stroke:#16213e,color:#e0e0e0
    classDef dockernet fill:#0f3460,stroke:#533483,color:#e0e0e0
    classDef vpnnet fill:#6a040f,stroke:#d00000,color:#fff
    classDef external fill:#495057,stroke:#adb5bd,color:#fff

    class devvm,ct101,ct102,workstation host
    class proxy_101,proxy_102,obs_net,n8n_net,org_net,media_net,idx_net,dl_net dockernet
    class tailscale_net,gluetun_tun vpnnet
    class internet external
```

## Docker Network Detail

```mermaid
graph LR
    subgraph ct_docker["ct-docker-01"]
        subgraph proxy1["proxy network"]
            traefik["Traefik :80/:443"]
            portainer["Portainer"]
            organizr["Organizr"]
            n8n["n8n"]
            grafana["Grafana"]
            pihole["Pi-hole :53"]
        end

        subgraph obs["observability_default"]
            prometheus["Prometheus"]
            grafana2["Grafana"]
            nodeexp["Node Exporter"]
            cadvisor["cAdvisor"]
        end

        subgraph n8n_int["n8n internal"]
            n8n2["n8n"]
            n8n_db["PostgreSQL"]
            n8n_redis["Redis"]
        end
    end

    subgraph ct_media["ct-media-01"]
        subgraph proxy2["proxy network"]
            plex["Plex"]
            tautulli["Tautulli"]
            radarr["Radarr"]
            sonarr["Sonarr"]
            prowlarr["Prowlarr"]
            bazarr["Bazarr"]
            overseerr["Overseerr"]
        end

        subgraph media_int["media-plex_media"]
            plex2["Plex"]
            tautulli2["Tautulli"]
        end

        subgraph dl_int["media-downloads_default"]
            gluetun["Gluetun VPN"]
            qbit["qBittorrent<br/>(network_mode: service:gluetun)"]
            sabnzbd["SABnzbd"]
        end
    end

    traefik -- "Reverse proxy" --> proxy2

    classDef proxynet fill:#2d6a4f,stroke:#1b4332,color:#fff
    classDef internal fill:#264653,stroke:#2a9d8f,color:#fff
    classDef vpnservice fill:#6a040f,stroke:#d00000,color:#fff

    class traefik,portainer,organizr,n8n,grafana,pihole,plex,tautulli,radarr,sonarr,prowlarr,bazarr,overseerr proxynet
    class prometheus,grafana2,nodeexp,cadvisor,n8n2,n8n_db,n8n_redis,plex2,tautulli2 internal
    class gluetun,qbit,sabnzbd vpnservice
```

## Port Exposure

| Service | Port | Protocol | Exposure |
|---------|------|----------|----------|
| Traefik | 80, 443, 8080 | HTTP/HTTPS | LAN (ingress for all HTTP services) |
| Pi-hole | 53 | DNS (TCP/UDP) | LAN (DNS resolver) |
| Plex | 32400 | HTTP | LAN + Tailscale (media streaming) |
| Tailscale | 41641 | WireGuard | Internet (VPN mesh) |
| Gluetun | — | OpenVPN/WG | Internet (download VPN tunnel) |
| All others | — | — | Internal only (via Traefik proxy network) |

## Network Security Zones

| Zone | Networks | Access |
|------|----------|--------|
| **Ingress** | proxy (external) | Traefik terminates all external HTTP/HTTPS |
| **Internal** | stack-specific defaults | Service-to-service only, no host ports |
| **VPN Tunnel** | Gluetun container network | qBittorrent traffic exits via VPN provider |
| **Mesh VPN** | Tailscale 100.x.x.x | Remote access to Traefik ingress |
| **Management** | LAN SSH :22 | dev-vm to LXC containers |
