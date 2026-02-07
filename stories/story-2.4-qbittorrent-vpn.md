# Story 2.4: qBittorrent VPN Routing Validation

**Epic:** Epic 2: Media Pipeline Validation & Automated Fixes
**Story:** 2.4 (VPN Routing Check)

## Goal

Create a test `tests/pipeline/test_qbittorrent_vpn.py` that verifies qBittorrent traffic is routed through the Gluetun VPN container, ensuring download traffic is secure and IP-masked.

## Acceptance Criteria

1.  **Test File:** `tests/pipeline/test_qbittorrent_vpn.py` exists.
2.  **Network Mode Check:** Verify qBittorrent container is using `network_mode: "service:gluetun"` (or similar VPN-enforced config).
3.  **IP Leak Test:** Query qBittorrent's external IP and assert it does NOT match the home network IP range (`192.168.x.x`).
    *   Alternative: Check if the IP matches a known VPN provider range (if available).
4.  **Gluetun Health:** Verify the Gluetun container is running and healthy.
5.  **Failure Reporting:** If the test fails, report whether it's due to:
    *   "VPN not configured" (wrong network mode)
    *   "VPN leak detected" (home IP exposed)
    *   "Gluetun unhealthy"

## Technical Approach

### 1. Docker Inspection
Use Docker SDK (or `docker inspect`) to check qBittorrent's `NetworkMode`:
*   Expected: `"container:<gluetun-container-id>"` or similar.

### 2. IP Leak Test
Query an IP check service via qBittorrent's web API (if supported) or use a known torrent tracker's IP reflection endpoint.
*   Alternative: Use `curl ifconfig.me` via `docker exec` inside the qBittorrent container.

### 3. Gluetun Health
*   Check if Gluetun container exists and status is "running".
*   Optional: Check Gluetun logs for VPN connection confirmation.

## Dependencies

*   `conftest.py` fixtures (Story 2.1)
*   Docker SDK or CLI access

## Definition of Done

*   [ ] `tests/pipeline/test_qbittorrent_vpn.py` created.
*   [ ] Test verifies qBittorrent uses Gluetun network.
*   [ ] Test confirms external IP is NOT the home network IP.
*   [ ] Test confirms Gluetun container is healthy.
