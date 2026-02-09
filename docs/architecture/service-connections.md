# Service Connections - Media Pipeline & Integrations

> Auto-generated from drift report, service catalog, and architecture docs (2026-02-08)

## Media Request Pipeline

```mermaid
flowchart LR
    user(["User / Family"])

    subgraph request["Content Request"]
        overseerr["Overseerr<br/>Request Portal"]
    end

    subgraph search["Search & Index"]
        radarr["Radarr<br/>Movies"]
        sonarr["Sonarr<br/>TV Shows"]
        prowlarr["Prowlarr<br/>Indexer Hub"]
        bazarr["Bazarr<br/>Subtitles"]
    end

    subgraph download["Download"]
        gluetun["Gluetun<br/>VPN Tunnel"]
        qbit["qBittorrent"]
        sabnzbd["SABnzbd<br/>Usenet"]
    end

    subgraph serve["Media Serving"]
        plex["Plex<br/>Media Server"]
        tautulli["Tautulli<br/>Analytics"]
    end

    user -- "Request movie/show" --> overseerr
    overseerr -- "Send to arr" --> radarr
    overseerr -- "Send to arr" --> sonarr
    radarr -- "Search indexers" --> prowlarr
    sonarr -- "Search indexers" --> prowlarr
    radarr -- "Add torrent" --> qbit
    sonarr -- "Add torrent" --> qbit
    radarr -- "Add NZB" --> sabnzbd
    sonarr -- "Add NZB" --> sabnzbd
    qbit -. "All traffic via VPN" .-> gluetun
    gluetun -- "Encrypted tunnel" --> internet(["Internet"])
    sabnzbd --> internet

    radarr -- "Import complete" --> plex
    sonarr -- "Import complete" --> plex
    bazarr -- "Fetch subtitles" --> radarr
    bazarr -- "Fetch subtitles" --> sonarr
    plex -- "Stream" --> user
    tautulli -. "Monitor" .-> plex

    classDef request fill:#2d6a4f,stroke:#1b4332,color:#fff
    classDef search fill:#264653,stroke:#2a9d8f,color:#fff
    classDef download fill:#6a040f,stroke:#d00000,color:#fff
    classDef serve fill:#7b2cbf,stroke:#c77dff,color:#fff
    classDef external fill:#495057,stroke:#adb5bd,color:#fff

    class overseerr request
    class radarr,sonarr,prowlarr,bazarr search
    class gluetun,qbit,sabnzbd download
    class plex,tautulli serve
    class internet external
```

## Infrastructure Integrations

```mermaid
flowchart TB
    subgraph infra["Infrastructure Services — ct-docker-01"]
        traefik["Traefik v3<br/>Reverse Proxy"]
        portainer["Portainer<br/>Container Mgmt"]
        pihole["Pi-hole<br/>DNS"]
        tailscale["Tailscale<br/>VPN Mesh"]
    end

    subgraph obs["Observability — ct-docker-01"]
        prometheus["Prometheus"]
        grafana["Grafana"]
        nodeexp["Node Exporter"]
        cadvisor["cAdvisor"]
    end

    subgraph auto["Automation — ct-docker-01"]
        n8n["n8n"]
        n8n_db["PostgreSQL"]
        n8n_redis["Redis"]
        organizr["Organizr"]
    end

    subgraph media["Media Services — ct-media-01"]
        pa["Portainer Agent"]
        media_svc["Plex / arr / Downloads"]
    end

    subgraph dev["dev-vm"]
        openclaw["OpenClaw + Claude CLI"]
    end

    traefik -- "Reverse proxy all HTTP" --> media_svc
    traefik -- "Reverse proxy" --> organizr
    traefik -- "Reverse proxy" --> n8n
    traefik -- "Reverse proxy" --> grafana
    traefik -- "Reverse proxy" --> portainer

    portainer -- "Manage containers" --> pa
    prometheus -- "Scrape metrics" --> nodeexp
    prometheus -- "Scrape metrics" --> cadvisor
    grafana -- "Query" --> prometheus

    n8n --> n8n_db
    n8n --> n8n_redis

    pihole -- "DNS for all containers" --> traefik
    tailscale -. "Remote access" .-> traefik

    openclaw -- "SSH + Docker SDK" --> infra
    openclaw -- "SSH + Docker SDK" --> media

    classDef infra fill:#0f3460,stroke:#533483,color:#e0e0e0
    classDef obs fill:#1a535c,stroke:#4ecdc4,color:#fff
    classDef auto fill:#3d405b,stroke:#81b29a,color:#fff
    classDef media fill:#5e548e,stroke:#9f86c0,color:#fff
    classDef dev fill:#2b2d42,stroke:#8d99ae,color:#fff

    class traefik,portainer,pihole,tailscale infra
    class prometheus,grafana,nodeexp,cadvisor obs
    class n8n,n8n_db,n8n_redis,organizr auto
    class pa,media_svc media
    class openclaw dev
```

## Data Flow Summary

| Flow | Path | Protocol |
|------|------|----------|
| Content Request | User -> Overseerr -> Radarr/Sonarr | HTTP API |
| Indexer Search | Radarr/Sonarr -> Prowlarr -> Indexers | HTTP API |
| Torrent Download | Radarr/Sonarr -> qBittorrent -> Gluetun -> Internet | BitTorrent over VPN |
| Usenet Download | Radarr/Sonarr -> SABnzbd -> Usenet Providers | NNTP/TLS |
| Media Import | Radarr/Sonarr -> Plex library folders | Filesystem (shared volume) |
| Media Playback | User -> Plex (via Traefik) | HTTP/HTTPS |
| Subtitle Fetch | Bazarr -> OpenSubtitles/Subscene | HTTP API |
| Monitoring | Prometheus -> Node Exporter / cAdvisor -> Grafana | HTTP scrape |
| DNS | All containers -> Pi-hole | DNS :53 |
| Remote Access | Tailscale mesh -> Traefik | WireGuard |
| Management | dev-vm -> ct-docker-01 / ct-media-01 | SSH + Docker SDK |
