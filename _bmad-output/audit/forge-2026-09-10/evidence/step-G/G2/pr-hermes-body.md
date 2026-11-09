Pushes a branch that has been **local-only and unpushed** since it was authored, and that the
2026-09-10 network review initially mistook for live-only content on CT 101. It is one clean
commit off `origin/main` (`e268da1`, merge-base `4b778f8`).

## What it lands

- `stacks/infra-core/config/hermes-saply.yml` — Traefik file-provider route
  `Host(hermes.bi-services.be)` → `http://192.168.50.164:8644` (ct-saply-ai), `websecure` +
  `letsencrypt`, deliberately **no Authelia middleware** because the Linear webhook
  authenticates by HMAC (`X-Hub-Signature-256`, validated per-route in the hermes-agent
  gateway). This file is **byte-identical to what is running on ct-docker-01 today**.
- `stacks/infra-core/docker-compose.yml` — mounts that file into Traefik and adds the
  `cloudflared` service (`tunnel --no-autoupdate run`, `proxy` network, capped json-file logs).
  This is the homelab's first public ingress, a narrow, deliberate amendment to the
  Tailscale-only policy.

## Why it has to be pushed now

Step G4 of `g-plan-2026-09-10.md` reconciles CT 101's 5-month-stale clone with
`git reset --hard origin/main`. That reset is only safe for
`stacks/infra-core/docker-compose.yml` once this branch is on `main` — otherwise the reset
discards the live `cloudflared` block and the Linear webhook ingress goes with it. The live
`infra-core/docker-compose.yml` differs from this branch only by one duplicate portainer
Traefik label and a stray blank line, both of which are noise upstream already has.

## Secret check

`TUNNEL_TOKEN` is an env-var **reference**, `${CLOUDFLARE_TUNNEL_TOKEN}`, not a literal. The
full branch diff was scanned before pushing for `eyJ` (JWT), `tskey`, any `TUNNEL_TOKEN=` not
followed by `${`, and `password=` — zero hits. The token itself stays in the ungitted
`stacks/infra-core/.env` on CT 101.

🤖 Generated with [claude-flow](https://github.com/ruvnet/claude-flow)

https://claude.ai/code/session_01TxFor1Kqf5zgJmBcYp3cw9
