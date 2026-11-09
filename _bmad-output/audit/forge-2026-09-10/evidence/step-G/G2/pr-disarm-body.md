Step G of the 2026-09-10 network review (`homelab-playbook/_bmad-output/audit/forge-2026-09-10/network-review-2026-09-10.md`
§4 Step 3, §8 CRITICAL-1), executed per `g-plan-2026-09-10.md` §3(a), §3(a2), §3(a3).

## Why

`homelab-gateway` (the Tailscale subnet router on ct-docker-01 / CT 101) runs with
`RouteAll: true` — measured live 2026-09-10. It **advertises** `192.168.50.0/24` and it
**lives on** that subnet. Accepting the route it advertises installs `192.168.50.0/24` via
`tailscale0`, which outranks `eth0` and blackholes the LAN on the single host that runs
Pi-hole, Traefik, Authelia and the only public ingress.

It is inert **today** only because CT 101 has no `/dev/net/tun` (userspace/netstack mode, so
`tailscale0` does not exist). The moment anyone grants the device — which is exactly what
Step 4-A of the review proposes — the trap springs. This PR removes the trap first.

## Why `=false` and not "just delete the flag"

`RouteAll` is a **persisted** pref in `tailscaled.state`. `tailscale set` only mutates the
prefs named on its command line, so dropping `--accept-routes` from the `set` call would leave
`RouteAll=true` in place from earlier starts. Hence the asymmetry in the diff:

- the **authenticated / warm** path (`tailscale set`) asserts `--accept-routes=false` explicitly;
- the **first-join / cold** path (`tailscale up`) simply drops the flag, because a fresh join
  starts from `RouteAll=false`.

Reference for the rule itself: `homelab-infra/ansible/roles/remote-access/defaults/main.yml:32-42`
(`remote_access_tailscale_accept_routes: false` at :42).

`--advertise-routes=192.168.50.0/24` is untouched on both paths. Remote LAN access through the
subnet router is unaffected; `Self.PrimaryRoutes` must stay `["192.168.50.0/24"]`.

The live pref has already been disarmed with no restart
(`docker exec tailscale tailscale set --accept-routes=false`, Step G1). This PR makes that
state the declared one so a `compose up` cannot silently re-arm it — `dd96ed4`, the auth-key
hygiene fix, is the commit that introduced the `--accept-routes=true` re-assertion being undone
here.

## Also in this PR — two artifacts rescued from the dirty clone

CT 101's `/opt/homelab-apps` clone is 5 months behind `origin/main` with 45 dirty entries. Of
those, exactly two carry content that exists nowhere else. Both are authored here, in the clean
repo, rather than committed on the container (committing there would commit a plaintext secret,
re-add ~30 duplicate Traefik labels and revert the media-downloads stack by 5 months):

1. `stacks/dns-pihole/config/custom.list` — three records:
   `192.168.50.156 ct-dev-homelab`, `192.168.50.163 ct-hermes-hub`, and
   `192.168.50.194 hermes.bi-services.be` — the last one **backs the Cloudflare Tunnel and the
   Linear webhook**. Losing the working-tree edit would take the public ingress with it.
   Verified: the file in this branch is now a set-identical match to live (41 records, zero
   difference in either direction).
2. `stacks/infra-core/config/dynamic/homeassistant.yml` — the Traefik file-provider route
   `Host(ha.bi-services.be)` → `http://192.168.50.86:8123`. Copied verbatim from live; md5
   `eb78e39ca31873d2c8d5dbf7f7e99b77`, byte-identical, 298 B. Landing it changes no behaviour,
   it just stops the route living only on a dirty clone.

`.gitignore` is widened to catch the `*.bak-*` / `*.bak_*` sprawl the existing `*.bak` and
`.env.bak-*` rules miss, and to hard-block
`stacks/observability/config/alertmanager/ntfy-password`, a plaintext secret that sits untracked
on CT 101 today.

## Rollback — corrected

The review's own Step-3 rollback one-liner (line 278) is **unsafe and must not be used**:

```bash
# DO NOT RUN - defective
ssh root@192.168.50.194 'cd /opt/homelab-apps && git checkout HEAD~1 -- stacks/networking-tailscale/docker-compose.yml && ...'
```

On CT 101 `HEAD` is `fafe4a8` (2026-04-16), so `HEAD~1` is `a8902ec` — a revision that carries
`--authkey=${TS_AUTHKEY}` in the container's argv. That rollback would **re-introduce the auth
key into `ps` output**, undoing the security fix `dd96ed4` shipped, and would disarm nothing.

Use these instead:

```bash
SSH="ssh -i ~/.ssh/homelab_ed25519 root@192.168.50.194"

# Fastest, no restart - re-arm the pref if something LAN-side regresses unexpectedly.
$SSH 'docker exec tailscale tailscale set --accept-routes=true'

# Revert the compose file on CT 101 to the previous upstream content and recreate.
$SSH 'cd /opt/homelab-apps && git checkout dd96ed4 -- stacks/networking-tailscale/docker-compose.yml && \
      cd stacks/networking-tailscale && docker compose -f docker-compose.yml -p networking-tailscale up -d'

# Revert this commit upstream.
git revert --no-edit 714b737 && git push

# Restore the tailnet identity if tailscaled.state is somehow lost (the node would otherwise
# re-join as a NEW node and the subnet route would need re-approval in the admin console).
$SSH 'docker stop tailscale'
cat ~/g-backup-*/ts-state.tgz | $SSH 'tar -C /opt/appdata/networking-tailscale -xzf -'
$SSH 'cd /opt/homelab-apps/stacks/networking-tailscale && docker compose up -d'

# If the LAN is ever genuinely blackholed and SSH is gone, pct exec from pve1 is the only path:
ssh root@pve1 'pct exec 101 -- docker exec tailscale tailscale set --accept-routes=false'
```

## Verification after deploy (Step G5)

```bash
$SSH 'docker exec tailscale tailscale debug prefs' | grep -iE 'routeall|advertiseroutes' -A2
#   RouteAll: false        AdvertiseRoutes: ["192.168.50.0/24"]
$SSH 'docker exec tailscale tailscale status --json' | jq '.BackendState, .Self.Online, .Self.PrimaryRoutes'
#   "Running", true, ["192.168.50.0/24"]   <- PrimaryRoutes proves the route is still APPROVED
$SSH 'ip link show tailscale0 2>&1'   # still "does not exist"
$SSH 'dig +short @192.168.50.194 hermes.bi-services.be forge.bi-services.be'
#   192.168.50.194 / 192.168.50.167 - Pi-hole untouched
```

## Blast radius

`network_mode: host`, no published ports, no bridge, compose project `networking-tailscale`
with exactly one service — it cannot enumerate or recreate anything in `dns-pihole` or
`infra-core`. Recreating it costs ~10 s of off-LAN-to-LAN-IP reachability and nothing else:
LAN-to-LAN SSH, CT 250's own tailnet identity, and the Cloudflare-Tunnel public ingress all run
on paths that do not traverse this container.

**This PR does not authorize Step 4-A** (kernel mode / `/dev/net/tun` on CT 101). It only
removes its blocker. §8 CRITICAL-2 still stands: any CT 101 restart goes through the Ansible
`reboot` module in a declared window, with `ct:101` HA `started` and replication current.
`pct reboot 101` remains forbidden.

🤖 Generated with [claude-flow](https://github.com/ruvnet/claude-flow)

https://claude.ai/code/session_01TxFor1Kqf5zgJmBcYp3cw9
