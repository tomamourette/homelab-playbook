#!/usr/bin/env bash
set -uo pipefail
SSH="ssh -o BatchMode=yes -i /home/developer/.ssh/homelab_ed25519 root@192.168.50.194"
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
BK="$HOME/g-backup-$STAMP"
mkdir -p "$BK"
echo "BACKUP_DIR=$BK"

echo "=== CMD: tar ts-state ==="
$SSH "tar -C /opt/appdata/networking-tailscale -czf - tailscale" > "$BK/ts-state.tgz"
echo "rc=$?"

echo "=== CMD: tar opt-homelab-apps ==="
$SSH "tar -C /opt -czf - homelab-apps" > "$BK/opt-homelab-apps.tgz"
echo "rc=$?"

echo "=== CMD: tailscale debug prefs ==="
$SSH 'docker exec tailscale tailscale debug prefs'    > "$BK/prefs.before.json"; echo "rc=$?"
echo "=== CMD: tailscale status --json ==="
$SSH 'docker exec tailscale tailscale status --json'  > "$BK/status.before.json"; echo "rc=$?"
echo "=== CMD: ip route / link ==="
$SSH 'ip -4 route show; ip link show tailscale0 2>&1' > "$BK/routes.before.txt"; echo "rc=$?"
echo "=== CMD: dig ==="
$SSH 'dig +short @192.168.50.194 hermes.bi-services.be forge.bi-services.be' > "$BK/dns.before.txt"; echo "rc=$?"
echo "=== CMD: docker ps ==="
$SSH 'docker ps --format "{{.Names}}\t{{.Status}}"'   > "$BK/ps.before.txt"; echo "rc=$?"

echo "=== GATE: tarball sizes ==="
ls -la "$BK"
echo "=== GATE: tar -tzf ts-state.tgz (head) ==="
tar -tzf "$BK/ts-state.tgz" | head -20
echo "ts-state entries: $(tar -tzf "$BK/ts-state.tgz" | wc -l)"
echo "=== GATE: tar -tzf opt-homelab-apps.tgz (head) ==="
tar -tzf "$BK/opt-homelab-apps.tgz" | head -10
echo "clone entries: $(tar -tzf "$BK/opt-homelab-apps.tgz" | wc -l)"
echo "BACKUP_DIR=$BK"
