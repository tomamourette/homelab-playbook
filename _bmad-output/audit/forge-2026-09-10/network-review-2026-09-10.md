# Network review — remote access, DNS and the Forge off-LAN path

**Date:** 2026-09-10 · **Scope:** tailnet `taildf9e93.ts.net`, Pi-hole/dnsmasq on CT 101, ingress on CT 101 + CT 167, remote reachability of Forge
**Inputs:** 4 read-only inventories, 1 impact analysis, 5 adversarial judges (correctness, security, reliability-ops, IaC maintainability, portability)
**Method:** strictly read-only. No config change, no restart, no playbook run, no `tailscale set`. Every claim below carries live output.
**Secrets:** none printed. Auth keys, tokens and password hashes are referenced by vault variable name only.

---

## 1. Is this issue "for everything"?

**No. It is not one issue, and it is not everything.** Three unrelated things were being read as a single tailnet outage, and the one the audit finding named — a userspace subnet router that drops UDP — **does not exist**.

### CONFIRMED (verified live today, read-only)

| # | Defect | Who it hits | Layer |
|---|---|---|---|
| C1 | `forge.bi-services.be` and every `*.forge` preview name answer **NXDOMAIN to AAAA** while answering A correctly | **Everyone** — LAN, tailnet, phone, Coder agents. Symptom surfaces on Windows only. | DNS answer content |
| C2 | Before 2026-09-09 17:09:18 UTC the name did not exist at all (`config forge.bi-services.be is NXDOMAIN`) | Everyone. Explains every report before 2026-09-09. | DNS answer content |
| C3 | Five names missing from the live `custom.list`: `gemma`, `forge`, `ct-forge-01`, `ct-saply-ai`, `ct-crypto-quant` → NXDOMAIN on the LAN | **LAN clients too**, not just remote | DNS answer content |
| C4 | `local=/bi-services.be/` makes Pi-hole authoritative and non-forwarding, black-holing the entire public half of the zone (apex, `www`, `autodiscover`/`sip`/`lyncdiscover`/`enterprise*`, M365 mail discovery, `zeroclaw`) | Everyone on the LAN and every tailnet client using split DNS | DNS answer content |
| C5 | `roles/forge-dns` verification is `dig +short` = **A-only**, so C1 passes all four of its own checks green | Future regressions of this class | IaC verification gap |
| C6 | CT 167 has no tailscaled and no `/dev/net/tun` — Forge has **zero tailnet identity** and no fallback if CT 101 or its node dies | Forge remote access | Topology / SPOF |

### FALSIFIED (the premise the finding was built on)

| # | Claim in R0-P1-S4-004 | What the evidence says |
|---|---|---|
| F1 | "netstack cannot proxy UDP to Pi-hole on its own host address; Pi-hole never sees them" | **False.** `netstack: UDP session … timed out` is forwardUDP's *idle teardown*, not an error. The operator's four sessions pair with four Pi-hole answers **30.000 s earlier**. Across the log window 2035/2038 = 99.85 % of session-start seconds carry a matching Pi-hole query, vs a 16.7 % control. |
| F2 | "Pi-hole has NEVER logged a forge query from the gateway's SNAT address" | **Measurement artefact.** netstack SNATs to the host IP, so a proxied query is logged *identically* to a host-originated one. Verified by probe: a raw UDP query bound `0.0.0.0` logged as `from 192.168.50.194`. |
| F3 | "homelab-gateway is relay-only (DERP ams/par) from every peer observed" | **False.** `tailscale ping` → `pong … via 192.168.50.194:41641 in 1ms` and `via 82.146.102.244:41641 in 23ms`; 181 direct-path selections in the log. The `Relay:` field is the peer's **home DERP region**, not the active path. The direct path to the laptop came up at 08:47:59 UTC — *before* the 08:49:52 UTC DNS sessions. |

### UNPROVEN — the one genuinely open transport question

**Does the DNS *reply* reach an off-LAN peer?** Nothing inside the LAN can answer this: every remaining tailnet node reaches `192.168.50.194` over `eth0`, never over the subnet route. The gateway log and `pihole.log` both end at Pi-hole answering; neither can show the netstack → WireGuard → laptop return leg. **One command on the laptop settles it** (§5).

### CONFIRMED IMPOSSIBLE BY DESIGN (unrelated to any option)

Broadcast/multicast never crosses a Tailscale subnet route in *any* mode, kernel included: mDNS 5353, SSDP 1900, Plex GDM 32410-14, NetBIOS 137/138, DLNA. Plex/Jellyfin local discovery and SMB browsing are LAN-only permanently.

### Per-client answer

- **LAN clients** — affected, by C1/C3/C4 only. Transport is untouched.
- **Remote tailnet (laptop)** — inbound DNS leg CONFIRMED working; affected by C1/C2/C3/C4; return leg UNPROVEN.
- **Phone / ntfy** — the memory note "Tailscale-only, no `bi-services.be` name" is **wrong**: the ntfy container publishes no host port and has exactly one router, `Host(ntfy.bi-services.be)`. A MagicDNS name or `https://100.74.151.44/` reaches Traefik with a non-matching Host and gets 404. That resolution *was* working — hourly A queries from the SNAT'd `.194` client on Sep 7-8, ending 2026-09-08 21:12:44. Resilient because the ntfy connection is a long-lived TCP stream needing DNS only at reconnect.
- **Coder agents inside workspaces** — unaffected by the tailnet path. CT 167 `/etc/resolv.conf` = `nameserver 192.168.50.194`, a LAN query over eth0. Exposed to C1/C3 only.
- **Public hermes tunnel / Linear webhook** — CONFIRMED unaffected. Cloudflare edge → outbound QUIC → `http://192.168.50.164:8644`. No Pi-hole, no tailnet, no subnet route.

---

## 2. Root cause, with the evidence chain

### Primary: the answer is wrong, not the packet

1. `/etc/dnsmasq.d/02-homelab.conf` declares `local=/bi-services.be/` → **Pi-hole is authoritative for the zone and never forwards it upstream.**
   Proof: `query[A] probe-b-22460.bi-services.be from 192.168.50.156` → `config probe-b-22460.bi-services.be is NXDOMAIN` — no `forwarded` line, unlike a `.home.io` probe in the same second which shows `forwarded … to 8.8.8.8`.
2. `/etc/dnsmasq.d/05-forge.conf`, rendered by `roles/forge-dns/templates/05-forge.conf.j2` from `defaults/main.yml`, contains exactly one **IPv4-only** directive: `address=/forge.bi-services.be/192.168.50.167`.
3. An **AAAA** query does not match an `address=` with an IPv4 literal. It falls through to the authoritative-zone catch-all from step 1 and is answered NXDOMAIN.
4. Live proof, and the missing `aa` flag is the mechanism's fingerprint:
   - `dig @192.168.50.194 A forge.bi-services.be` → `NOERROR`, flags `qr aa rd ra`, `192.168.50.167`
   - `dig @192.168.50.194 AAAA forge.bi-services.be` → **`NXDOMAIN`**, flags `qr rd ra` — **no `aa`**
   - `dig @192.168.50.194 AAAA judge-probe.forge.bi-services.be` → `NXDOMAIN` (wildcard label, same fault)
   - Contrast `dig @192.168.50.194 AAAA hermes.bi-services.be` → `NOERROR`, `ANSWER: 0` — correct NODATA, because `hermes` is an `addn-hosts` entry which makes the *name* exist.
5. **Windows' DNS Client caches a negative NXDOMAIN against the NAME.** An A+AAAA pair where AAAA returns NXDOMAIN is the textbook way for `nslookup` / `Resolve-DnsName` / Chrome to report "Non-existent domain" for a name that has a perfectly good A record. *(Inference — the strongest available explanation of the reported symptom, testable from the laptop in §5.)*
6. Before the fix: `05-forge.conf` mtime `2026-09-09 17:09:18 UTC`; last A NXDOMAIN Sep 9, first correct answer `Sep 9 19:07:53 dnsmasq[253220]: config forge.bi-services.be is 192.168.50.167`.

### Why the transport hypothesis is dead

- Source of the log line, tailscale v1.96.5 `wgengine/netstack/netstack.go`:
  `ns.logf("netstack: UDP session between %s and %s timed out", backendListenAddr, backendRemoteAddr)` — fired by `time.AfterFunc(idleTimeout)`, **reset on every packet copied in either direction**. `idleTimeout` = 2 min generally, **30 s for dport 53**. Both addresses are netstack's own, which is why the source reads `0.0.0.0:port`.
- Operator's retries: `2026/09/10 08:50:22 netstack: UDP session between 0.0.0.0:54308 and 192.168.50.194:53 timed out` (×4, same second).
  Pi-hole, exactly 30.000 s earlier: `Sep 10 10:49:52 query[A] forge.bi-services.be from 192.168.50.194` / `config … is 192.168.50.167` / `query[AAAA] …` / `config … is NXDOMAIN`. **Four queries, four sessions.**
- The non-DNS timeout obeys the 2-minute rule: bind at `06:00:11`, teardown at `06:02:11` for `:5351`.
- Aggregate: 2038 distinct netstack `:53` session-start seconds; 2035 have a matching `.194` query in that exact second; control at −90 s = 340/2038 = 16.7 %, equal to the base rate. The 3 misses are sub-second rounding.
- Host path proven healthy anyway: `dig @192.168.50.194 forge.bi-services.be +short` → `192.168.50.167`; a raw UDP socket bound `0.0.0.0` got a 54-byte reply in 0.001 s; the same socket with `SO_MARK=0x80000` (Tailscale's bypass mark) also replied.
- The 98 % of timeouts to `.194:53` are *successful* sessions going idle. The remaining 129 are to ports with **no listener** — `192.168.50.1:5351` NAT-PMP and `:1900` SSDP on a router that runs neither (`netcheck PortMapping:` is blank), plus hairpinned laptop LAN addresses. Neither proves nor disproves anything.

### Secondary: why it shipped green

`roles/forge-dns` probes, waits and verifies with `dig +short @127.0.0.1 {{ item.domain }}` — **A-only**. A record that answers A correctly and AAAA with NXDOMAIN passes all four checks. This is the defect that let C1 ship.

### Tertiary: the zone-wide fault behind all of it

`local=/bi-services.be/` plus an IPv4-only `address=` plus a stale `custom.list` (37 live records vs 41 generated, +1 hand-added `hermes`). And `/opt/appdata/dns-pihole/dnsmasq.d/02-homelab.conf` is a **zero-byte file** shadowed by a read-only file-level bind from a dirty clone: one compose regeneration silently drops `local=`, `domain=` and `expand-hosts` and changes the whole zone's behaviour.

---

## 3. The five judges, side by side — disagreements shown, not averaged

### Ranking of the five given options (1 = best, among A-E only)

| Option | J1 correctness | J2 security | J3 reliability-ops | J4 IaC | J5 portability | Spread |
|---|---|---|---|---|---|---|
| **A** kernel mode on CT 101 | **1** | 4 | 4 | 2 | 3 | 1-4 |
| **B** second subnet router | 3 | 3 | **1** | 4 | 4 | 1-4 |
| **C** Tailscale on CT 167 | 2 | **5 (last)** | 3 | **1** | **1** | **1-5** |
| **D** move split-DNS target | 4 | **1** | 2 | **5 (last)** | 2 | **1-5** |
| **E** MagicDNS/ts.net redesign | 5 | 2 | 5 | 3 | 5 | 2-5 |

### The unanimous verdict — on an option that was not on the list

**5/5 judges independently invented the same sixth option and put it first or as an unconditional prerequisite:** fix the AAAA answer content in `roles/forge-dns`, land the five missing records additively, then run one off-LAN laptop probe before spending any blast radius.

- J1 calls it **F**; J2 calls it **Step 1** of "disarm, govern, decouple, then decide"; J3 calls it **H** (+ **G** for the probe); J4 calls it **F**; J5 calls it **G**.
- J1 states the decisive point bluntly: *"A, B, C, D and E would ALL have failed to prevent today's failure, because none of them changes a DNS answer."*
- J4 adds the durability point: *"A record that answers A correctly and AAAA with NXDOMAIN passes all four checks."*

### The four sharpest disagreements

**1. Option C is both the best and the worst option on the table.**
J4 and J5 rank it **first** of the five: purely additive IaC (one line in `[remote_access_hosts]`, one ID in `lxc_tun_ctids`), tag inherited from `group_vars/all`, blast radius one `pct reboot 167`, and it is exactly what `create-project-container` step 15 already prescribes.
J2 ranks it **dead last**, and the reason is specific, not stylistic: it puts a tailnet identity and `/dev/net/tun` on the one host running attacker-controlled compute (`docker:x:991:developer,coder`; Coder's provisioner runs user-authored Terraform against that socket; docker-group membership is root-equivalent), under an ACL that **exists nowhere in the repo** — only as a snippet at `homelab-infra/docs/remote-access.md:83-100` reading `"src": ["autogroup:member","tag:control"], "dst": ["tag:container","tag:control"], "users": ["autogroup:nonroot","root"]`. Tag CT 167 `tag:container` and every tailnet member gets root SSH on the Coder host, with a lateral path to `tag:control` (the box holding the vault password, the SSH key and all the IaC).
**Not averaged.** Both are right about different things. C is correct *after* the ACL is a committed, drift-checked artifact and CT 167 gets a dedicated `tag:workspace` with `RunSSH=false` and no SSH grants. C as written today is the only option in the set that creates a new lateral path from untrusted code into the control plane.

**2. Option D is first for security and last for IaC — same fact, opposite conclusions.**
J2: D adds zero device grants, zero capabilities, zero tailnet identities, zero new auth-key consumers, no crown-jewel reboot, and its failure mode is bounded to remote DNS.
J4: the split-DNS route is admin-console state with **no artifact anywhere in the repo**; a second person cannot re-apply D at all, and if the entry is lost every off-LAN `bi-services.be` name breaks silently with nothing to restore from.
**Not averaged.** Both correct. D satisfies the *letter* of "IaC-only changes" (no repo file changes) while violating its *intent*, and creates a **second** unversioned control-plane object alongside the ACL. If D is ever taken it must be recorded in `tailscale-policy.md` and brought under the Tailscale Terraform provider in the same change.

**3. A direct factual contradiction about ordering — B before or after A.**
Standing operator note in auto-memory: *"Do not add a second subnet router until `--accept-routes` is off CT 101."*
J3 argues this is **backwards for today's state**: CT 101 is userspace, so `RouteAll: true` installs nothing (`ip route | grep -c 100.` = 0, `iptables -S | grep -c ts-` = 0). The second router is safe *precisely while CT 101 stays userspace*; it is **A** that arms the blackhole.
J1 and J2 keep the original ordering because they treat `--accept-routes` as a latent trip-wire that must come out regardless.
**Resolution — both are satisfied by the same move:** remove `--accept-routes` from the compose *unconditionally and first*, as debt payment. It costs a ~10 s tailnet blip, is not conditional on which option wins, and after it the ordering dispute evaporates.

**4. Option E is the only near-consensus rejection, and it is blocked on a fact, not a preference.**
J1, J3 and J5 all land on the same blocker: **Tailscale issues certs only for the exact machine FQDN and does not issue wildcards for `*.host.tailnet.ts.net`** (`tailscale/tailscale#7081`, still open). `CODER_WILDCARD_ACCESS_URL=*.forge.bi-services.be` is live in `/etc/coder.d/coder.env`, and Coder preview URLs are subdomain-based — the whole point of the PoC and its acceptance gate. E either breaks previews or forces Coder to path-based apps, which Coder itself warns is a confidentiality regression (shared origin, session-token bleed).
J2 ranks E **second** — but explicitly on *end state*, not on doing it now: E is the only option that deletes the console-only split-DNS route from the trust path and retires the justification for 43 public unproxied A records publishing the complete internal `192.168.50.0/24` host plan.

### One finding no judge disputes and no option addresses

**Any tailnet node today reaches every LAN service unauthenticated on raw IP:port.** Authelia is name-based only. `pihole:8053` bypasses its own Authelia router; a stale `.home.arpa` sonarr/radarr/prowlarr/bazarr stack sits on `0.0.0.0` on CT 101; `ha.bi-services.be` proxies to Home Assistant with **no auth middleware at all**; every ct-media-01 backend listens on `0.0.0.0`. J2 rates this the largest live security finding in the whole review. Fixing the subnet route (A or B) makes this exposure **worse**, not better. It needs its own workstream.

---

## 4. Recommendation

**Not a single option — an ordered combination, with a decision gate in the middle.** Nothing on the A-E list is correct as a first move, because none of them changes a DNS answer and the only confirmed defect *is* a DNS answer.

### Step 1 — **F: fix the answer** (do first, alone, today)

Amend `roles/forge-dns` so forge names return **NOERROR/NODATA** for AAAA instead of NXDOMAIN; land the five missing records additively through the same drop-in mechanism; extend the role's probe/wait/verify tasks to assert the **AAAA rcode**, not just the A answer.

**Why first:** it is the only change in this entire review that touches a defect proven to exist; it is the only change that would have prevented today's failure; it is additive, needs no container restart anywhere, is trivially revertible, and may close the ticket outright.

### Step 2 — **P: the probe** (zero cost, run in parallel with Step 1's PR)

One command on the laptop, off-LAN, hosts file cleared. A random wildcard label no hosts file can fake. **This is the single measurement that separates "content bug, already fixed" from "the return leg is genuinely broken."** Nobody should spend a privilege grant or a crown-jewel reboot before running it.

### Step 3 — **G: disarm and govern** (unconditional, independent of which option wins)

Remove `--accept-routes` from **both** code paths of the gateway compose, merge `fix/tailscale-authkey-argv`, commit the live-only artifacts on CT 101, and add `networking-tailscale` to `deploy-applications.yml`.

**Why unconditional:** the compose asserts `--accept-routes=true` on every start and has re-armed **44 times**. It is inert only because userspace installs no kernel routes. It contradicts the role's own hard rule (`roles/remote-access/defaults/main.yml:36-42`) and gotcha #1 (`remote-access-recovery.md:136`), and it is the blocker on both A and B. It recreates **only** the tailscale container — a separate compose stack from `dns-pihole` and `infra-core`, so Pi-hole, Traefik and cloudflared never restart. In parallel: commit the tailnet ACL as a versioned artifact with a drift check, and narrow the `dst: ["tag:container"], users: [… "root"]` grant off `autogroup:member`.

### Step 4 — branch on what the probe said

- **Probe answers →** the subnet-route DNS path is sound end to end. **A, B and D are all unnecessary.** Stop. Optionally add **C** as defence in depth, scoped honestly (Tailscale SSH + removal of CT 101 as Forge's sole remote dependency — **not** a browser path: Caddy has one site block and no `ts.net` cert, and Coder redirects to `CODER_ACCESS_URL` regardless), and **gated on the ACL landing first** with a dedicated `tag:workspace`, `RunSSH=false`, no SSH grants.
- **Probe times out →** the return leg is the real defect. Take **A** (kernel mode on CT 101), which is only safe because Step 3 already removed `--accept-routes`. Consider the **D-variant** first if you want to avoid the crown-jewel reboot: publish `127.0.0.1:53` alongside the existing `192.168.50.194:53` and retarget split DNS to the gateway's own tailnet address `100.74.151.44` — verify with `tcpdump -i lo port 53` **before** committing, because if netstack dials `.194` rather than loopback for self-addressed traffic, D fails closed.

### Follow-on, not blocking

Bring `02-homelab.conf` under Ansible (today a zero-byte file shadowed by a read-only bind from a dirty clone) and reconsider `local=/bi-services.be/` — the single directive causing both the AAAA NXDOMAIN and the black-holing of the entire public half of the zone. Separately, open a workstream on the flat-LAN unauthenticated exposure (§3, last item).

### Explicitly do NOT

**Do not reach for `update-dynamic-configs.yml` to land the missing records.** Its registering task is `state: present` — an unattended `terraform apply` — the `ct_docker_ip` dereference is broken, and it copies `generated/pihole-custom.list` verbatim, **deleting the hand-added `hermes` record that backs the only public ingress and the Linear webhook.** `deploy-all.yml:31` imports it under tags `infrastructure`/`infra`/`ip-update`, so that path is armed too.

---

## 5. Rollout plan

### 5.1 IaC touch points, in order

**Step 1 — F (Ansible only, `homelab-infra`)**

| File | Change |
|---|---|
| `ansible/roles/forge-dns/templates/05-forge.conf.j2` | render the directive that yields NOERROR/NODATA for AAAA alongside the existing IPv4 `address=` |
| `ansible/roles/forge-dns/defaults/main.yml` | extend `forge_dns_records` with `gemma`, `forge`, `ct-forge-01`, `ct-saply-ai`, `ct-crypto-quant` |
| `ansible/roles/forge-dns/tasks/main.yml` | replace the four `dig +short` probes with checks asserting **both** the A answer and the AAAA rcode |
| entry point | `ansible-playbook -i inventories/homelab/hosts.ini playbooks/forge-dns.yml` |
| writes to | `/opt/appdata/dns-pihole/dnsmasq.d/05-forge.conf` on CT 101 — the **rw appdata mount**, deliberately not the dirty `homelab-apps` clone. `/etc/pihole/custom.list` is never touched, so the hand-added `hermes` line survives. |

Consider renaming the role (it now owns internal DNS records generally, not just forge) so the estate does not gain a second non-obvious owner of internal DNS.

**Step 3 — G (`homelab-apps` + `homelab-infra`)**

| File | Change |
|---|---|
| `homelab-apps/stacks/networking-tailscale/docker-compose.yml` | delete `--accept-routes=true` (authenticated path) **and** `--accept-routes` (first-join path) |
| `homelab-apps` branch `fix/tailscale-authkey-argv` (dd96ed4) | merge to `main` — `main` still carries the argv auth-key form and would regress a security fix |
| `/opt/homelab-apps` on CT 101 | commit the live-only `cloudflared` service block and `config/hermes-saply.yml`, then reconcile the 45 dirty files. **Commit-what-is-live — never `git checkout --force`**: those two artifacts exist nowhere else and losing them takes the only public ingress with them. |
| `homelab-infra/ansible/deploy-applications.yml` | add `networking-tailscale` to the ten stacks it deploys; template its `.env` from vault |
| tailnet ACL | commit as a versioned artifact with a drift check; today it exists only as a doc snippet |

**Step 4 conditional — A**

| File | Change |
|---|---|
| `homelab-infra/ansible/playbooks/lxc-enable-tun.yml` | add `101` to `lxc_tun_ctids` (currently `[151, 250]`) |
| same compose | drop `--tun=userspace-networking` |
| note | the playbook writes its block with `blockinfile` into `/etc/pve/lxc/101.conf`, which carries `#Managed by Terraform` — confirm a `terraform apply` does not strip it |

**Step 4 optional — C**

| File | Change |
|---|---|
| `ansible/inventories/homelab/hosts.ini:50` | add `ct-forge-01` to `[remote_access_hosts]` |
| `ansible/playbooks/lxc-enable-tun.yml` | add `167` to `lxc_tun_ctids` |
| host_vars | keep `remote_access_tailscale_accept_routes: false` (role default, and correct — CT 167 is *inside* the advertised subnet) |
| **must not** | put any tailscale task inside `roles/forge-coder-host` — that makes the product tailnet-coupled and un-shippable elsewhere |

### 5.2 Expected downtime

| Step | Blast radius | Downtime |
|---|---|---|
| **1 — F** | dnsmasq drop-in reload on CT 101 | **Zero.** Rescue path if the reload misbehaves is `docker restart pihole` = seconds of estate-wide DNS. **Never `pihole restartdns`** — the role's own header warns it hangs forever on this image and can leave the s6 service down. |
| **2 — P** | none | **Zero** |
| **3 — G** | recreates the `tailscale` container only; separate compose stack from `dns-pihole` and `infra-core` | **~10 s remote-access blip.** Pi-hole, Traefik, cloudflared, ntfy, Prometheus untouched. |
| **4 — A** | `pct reboot 101`: Pi-hole (DNS for 34 LAN clients), Traefik (~30 services), Authelia, **cloudflared — the only public ingress and the Linear webhook** — plus Prometheus, Alertmanager, Loki, blackbox and ntfy | **Declare a 15-30 min window.** You are blind and unalertable for its duration, because the entire monitoring stack is on the host being rebooted. HA risk: `ct:101` has `max_restart 3, max_relocate 1`; a reboot is the most likely trigger of the first relocate in 60 days, restoring from a ≤15-min-old replica. |
| **4 — C** | `pct reboot 167`: Coder + Postgres | **Minutes.** Cheap *now* — `docker ps -a` on 167 is empty and the CLI is signed out, so no workspace exists to disrupt. Expensive after FE4-S01 creates one. |

### 5.3 Verification

**From the LAN** (run on `ct-dev-homelab`, 192.168.50.156):

```bash
# C1 — the fix. AAAA must be NOERROR with ANSWER: 0, NOT NXDOMAIN.
dig @192.168.50.194 A    forge.bi-services.be              # expect NOERROR, aa, 192.168.50.167
dig @192.168.50.194 AAAA forge.bi-services.be              # expect NOERROR, ANSWER: 0
dig @192.168.50.194 A    judge-probe.forge.bi-services.be  # expect 192.168.50.167  (wildcard still works)
dig @192.168.50.194 AAAA judge-probe.forge.bi-services.be  # expect NOERROR, ANSWER: 0

# C3 — the five missing names
for n in gemma forge ct-forge-01 ct-saply-ai ct-crypto-quant; do
  printf '%-16s %s\n' "$n" "$(dig +short @192.168.50.194 $n.bi-services.be)"
done

# REGRESSION GUARD — must still answer 192.168.50.194. If this is empty, the
# public ingress and the Linear webhook are broken. Stop and roll back.
dig +short @192.168.50.194 hermes.bi-services.be

# Step 3 guard — after removing --accept-routes
ssh root@192.168.50.194 'docker exec tailscale tailscale debug prefs | grep -i routeall'   # expect false
```

**From the laptop** (off-LAN, hosts-file entry for forge **removed**, cache flushed):

```powershell
ipconfig /flushdns

# THE DECIDING PROBE — a random wildcard label no hosts file can cover.
Resolve-DnsName judge-probe.forge.bi-services.be -Server 100.100.100.100

# The A/AAAA split that explains the Windows symptom
Resolve-DnsName forge.bi-services.be -Type A    -Server 192.168.50.194
Resolve-DnsName forge.bi-services.be -Type AAAA -Server 192.168.50.194

# What the OS resolver actually does end to end
nslookup forge.bi-services.be
Test-NetConnection forge.bi-services.be -Port 443
```

**Reading the probe:**

- **Answers `192.168.50.167`** → the subnet-route DNS path works end to end. The case is closed by Step 1. A, B and D are unnecessary; C becomes optional defence in depth.
- **Times out** → the return leg is the real defect. A becomes correct — and only safe because Step 3 already removed `--accept-routes`.
- **Answers, but `forge.bi-services.be` still fails in the browser while `judge-probe` resolves** → a client-side agent or a multi-homed resolution race, not an infrastructure defect. Capture on the laptop before touching the estate.

### 5.4 Rollback one-liners

```bash
# Step 1 — F  (additive drop-in; no restart; safest revert in the set)
git revert --no-edit <sha> && ansible-playbook -i inventories/homelab/hosts.ini playbooks/forge-dns.yml

# Step 3 — G  (recreates the tailscale container only)
ssh root@192.168.50.194 'cd /opt/homelab-apps && git checkout HEAD~1 -- stacks/networking-tailscale/docker-compose.yml && docker compose -f stacks/networking-tailscale/docker-compose.yml up -d'

# Step 4 — A  (immediate blackhole relief BEFORE reverting the tun grant; pct exec is the only path if the LAN is gone)
pct exec 101 -- tailscale set --accept-routes=false

# Step 4 — C
ssh ct-forge-01 'tailscale logout' && cd /home/developer/workspace/homelab/homelab-infra/ansible && git revert --no-edit <sha>
```

---

## 6. What this means for the Forge audit

### R0-P1-S4-004 — severity proposal

The finding's **stated root cause is factually wrong**, in the same class as the fabricated ADR-010 citation that ADR-005 already corrected. Under `plan.md` §4 a fixer may not lower severity, so this is a **constructive refutation routed back to verification** (§5, revision S1), not a unilateral re-rating. Proposed disposition:

| Sub-finding | Proposed severity | Rationale against `plan.md` §4 |
|---|---|---|
| **Withdraw** the transport claim ("netstack cannot proxy UDP to Pi-hole on its own host address") | **n/a — COULD_NOT_REPRODUCE** | Actively falsified: 2035/2038 correlation, 30.000 s pairing, `SO_MARK` probe. The `Relay:` and "never logged" sub-claims are likewise measurement artefacts. Leaving it standing would send a fixer to reboot the estate's resolver for a defect that does not exist. |
| **R0-P1-S4-004a** — forge names answer NXDOMAIN to AAAA | **Medium** | "Wrong behaviour with a workaround" — the workaround is a hosts-file entry, which is exactly what the operator was already doing. Confirmed live, one-file IaC fix, zero restarts. |
| **R0-P1-S4-004b** — `roles/forge-dns` verify is A-only, so 004a passes green | **Medium** | "Missing idempotency"-class: a verification that cannot fail on the defect it exists to catch. This is the finding that makes 004a recur. |
| **R0-P1-S4-004c** — five names missing from live `custom.list`; `local=/bi-services.be/` black-holes the public half of the zone | **Medium** | Wrong behaviour, LAN-wide, with a workaround (bare IP). Includes the zero-byte `02-homelab.conf` shadowed by a read-only bind — one compose regeneration changes the whole zone silently. |
| **R0-P1-S4-004d** — CT 167 has no tailnet identity; Forge's entire remote path depends on one container on one node | **Medium** | Not High: no documented workflow *fails* today, and the LAN path is unaffected. Escalates to **High** the moment the probe in §5 times out, because gate (a) then has no working path at all. |
| **New, separate, NOT a Forge finding** — any tailnet node reaches every LAN service unauthenticated on raw IP:port | **High** | "Documented workflow fails" in the sense that Authelia's `default_policy: deny` does not hold on a path that is trivially reachable. Out of Forge scope; needs its own finding ID and workstream. Options A and B make it worse. |
| **Note for P2** — 43 public unproxied A records publishing the complete internal `192.168.50.0/24` host plan | **Medium (information disclosure)** | Contradicts `tailscale-policy.md:39` ("Public DNS has no A-record"), which is now factually dead. Doc debt at minimum. |

**Net effect on the audit's original rating:** the HIGH was earned by the transport claim. With that withdrawn, no single sub-finding is High and **R0-P1-S4-004 downgrades to Medium** — which still blocks exit while OPEN, so this is not a get-out. It becomes closable inside one PR rather than one maintenance window.

### Should Phase 0b wait for the fix?

**No.** Three reasons:

1. **The Phase 0b gate is unrelated.** `plan.md` states it plainly: *"Gate for Phase 0b: operator GitHub OAuth consent (FE4 in scope) — the evidence bundle is captured only after it."* Nothing about the network path gates it.
2. **The confirmed defect is a one-file Ansible change with zero restarts.** It lands in parallel with Phase 0b, not ahead of it. There is no infrastructure change to sequence around, because the premise that demanded one is falsified.
3. **The probe is a 30-second operator action, not an engineering task.** It can be run today, from the laptop, with zero blast radius.

**One thing does wait: acceptance gate (a).** `tests/acceptance.md:119-120` requires the certificate to verify *"from a tailnet client **not on the LAN**"*, and `architecture.md:209` names the subnet router as *"how the operator's tailnet client reaches CT 167 in every gate."* That is precisely the return leg the probe measures. **Gate (a) sign-off is blocked on the probe result, not on the fix.** If the probe answers, gate (a) can be exercised as soon as Step 1 lands. If it times out, gate (a) is blocked on Step 4-A and the window it needs.

**Also document, in the same PR:** the tailnet **Split DNS route** `bi-services.be -> 192.168.50.194` — the mechanism every off-LAN lookup depends on — appears in **zero wiki pages and zero ADRs**. It is admin-console-only state, the same unversioned class `tailscale-policy.md` already flags the ACL as. That governance gap is why this incident took a full day to diagnose.

---

## 7. Open unknowns

**Blocking a decision:**

1. **Does the DNS reply reach an off-LAN peer?** The only unknown that changes the recommendation. Not answerable from inside the LAN — every remaining tailnet node reaches `.194` over `eth0`. Settled by the §5 probe.
2. **The exact dnsmasq directive that yields NODATA for a wildcard domain on this image.** Pi-hole here is **v5.25.2** (`pihole/pihole:2024.07.0`) — there is no `pihole.toml`; the config surface is `setupVars.conf` + `/etc/dnsmasq.d/*.conf`. FTL's embedded dnsmasq answers AAAA with NXDOMAIN despite an `address=` match, which is not what upstream documents. **Measure on the image before committing.** Getting it wrong by supplying an IPv6 address hands browsers a dead AAAA to attempt, which is strictly worse than NXDOMAIN.
3. **Does Windows really collapse the A+AAAA pair into "Non-existent domain"?** The strongest available explanation, but inference. Testable from the laptop with `-Type A` vs `-Type AAAA` — **after** the hosts-file entry is removed, or it masks the result.

**Operationally live, not blocking:**

4. **Auth-key expiry.** Both vault entries (`vault_tailscale_authkey`, `vault_tailscale_authkey_control`) are plain expiring `tskey-auth-*` keys, not the OAuth client secrets the role's own defaults recommend. Nodes created 2026-07-27/28 + Tailscale's 90-day default ⇒ **~2026-10-25 (inference)**. Not readable from the CLI or vault; needs the admin console. `remote-access-verify.yml` checks key shape and scope but **never expiry**. The phone's node key expires **2026-10-22** — six weeks out.
5. **The live tailnet ACL.** No committed artifact, no drift check. The running policy may already differ from the doc snippet.
6. **Does netstack deliver self-addressed tailnet traffic to loopback?** Decides whether option D's variant works at all. One `tcpdump -i lo port 53` on CT 101 while a peer queries `@100.74.151.44`.
7. **DHCP option 6/15 from the ASUS at 192.168.50.1.** Not readable read-only — no DHCP client exists on the estate. Proven: the router *forwards* to Pi-hole and both resolver paths are in live use. Settled by one look at the router UI.
8. **CT 101's node placement.** Both wiki pages hard-code pve1; `ha-manager status` agrees today, but pve1 has rebooted five times in 21 days (Aug 20/26/27/28, Sep 3) vs 14.9 days uptime on pve2 and pve3.

**Latent, unrelated to this incident but capable of producing an identical-looking "the tailnet broke" report:**

9. `/var/log/pihole/pihole.log` is **5.97 GB, unrotated**, inside a 256 MB-limited container.
10. **The monitoring stack cannot report its own host's outage** — Prometheus, Alertmanager, Loki, blackbox and ntfy are all among the 32 containers on CT 101. The `blackbox-dns` job probes `192.168.50.194:53` *from* `192.168.50.194`, so it never traverses the subnet route and could not have fired for this failure. No alert exists for route health, primary-route ownership, direct-vs-relay, backend state or key expiry. Five pve1 reboots produced no operator signal.
11. `ct-media-01` has `/dev/net/tun` but is not in `lxc_tun_ctids` and runs no Tailscale — unexplained.
12. A second Cloudflare Tunnel, `zeroclaw.bi-services.be`, points at a host with **no LXC config anywhere on the cluster**.
13. An unmanaged `homeassistant → 192.168.50.10` A record round-robins against the Terraform-managed `→ .86`; Pi-hole knows only `.86`, so internal and external answers disagree half the time.

---

## 8. Adversarial critic — corrections that MUST be applied before executing §4/§5 (added 2026-09-10 ~12:50)

**CRITICAL-1 — Step 3 "G" does not disarm `--accept-routes` as written.** `tailscale set` mutates only the prefs named on the
command line; *deleting* `--accept-routes=true` stops re-asserting it but leaves the persisted `RouteAll: true` in the state file.
Step 4-A (kernel mode on CT 101) is premised on it being off; executing A after the written G would have kernel mode install
`192.168.50.0/24` via `tailscale0` on CT 101 — the LAN blackhole `roles/remote-access/defaults/main.yml:32-42` warns about, on the host
running Pi-hole, Traefik, Authelia and the only public ingress. **Fix:** the authenticated path must run `--accept-routes=false`
explicitly; removing it from the first-join `up` line is fine (fresh join defaults false). Verify with `tailscale debug prefs | grep RouteAll`.

**CRITICAL-2 — `pct reboot 101` is a data-loss path under this audit's own plan.** `ct:101` is HA-managed (`max_restart 3, max_relocate 1`,
replicated every 15 min). A `pct reboot` is the most likely trigger of a relocation onto a peer from a ≤15-min-old replica — losing
Pi-hole, Prometheus, Loki, n8n and Authelia state. Plan §7 mandates the Ansible `reboot` module (in-guest, HA-neutral) and §8 forbids HA
writes; §5 of this review contained no HA maintenance step. **Fix:** any CT 101 restart goes through the Ansible reboot module after an
explicit operator decision, with HA state confirmed `started` and replication current, in a declared window.

**CRITICAL-3 — the transport evidence does not distinguish netstack-to-self from netstack-UDP-in-general.** Every §2 transport probe was a
host-native socket; none traversed `forwardUDP`. The 2035/2038 correlation cannot attribute queries to netstack because — per F2 — proxied
and host-originated queries log identically; F1 and F2 cannot both stand, and the reviewers' own `dig`s from CT 101 are a confound.
**Resolution:** a query that provably traverses the tunnel into the gateway's netstack (from a kernel-mode peer with a transient /32 route
over `tailscale0` to a non-self LAN host AND to Pi-hole), plus the off-LAN laptop probe. Executed 2026-09-10 ~12:50 — see §9.

What the critic would defend: C1 (AAAA NXDOMAIN, `aa`-flag fingerprint), C3, C4, C5, the ordering "F first", and the refusal to reboot
CT 101 without a probe result.

## 9. Transport probe from a kernel-mode LAN peer (2026-09-10 ~12:55) — INCONCLUSIVE, recorded as such

Method: on ct-dev-homelab (kernel-mode Tailscale, tagged node, RouteAll=false; netmap AllowedIPs for homelab-gateway include
192.168.50.0/24), transient `/32` routes via `tailscale0` for 192.168.50.1 (non-self LAN host) and 192.168.50.194 (Pi-hole, the router's own
host), then `dig` A and AAAA for forge names against each; routes removed immediately (verified restored to eth0).
Result: all four queries timed out; the gateway log shows **no** netstack/forward lines in the window; Pi-hole has **no** entry for the
unique probe label. The packets therefore never entered the gateway's netstack — dropped before or at the tunnel, not inside forwardUDP.
Two confounds, unresolved: (a) with RouteAll=false the local wgengine may not carry non-accepted subnet routes on the data path;
(b) the source is a `tag:container` node and the tailnet ACL may not grant it 192.168.50.0/24 (it grants the operator's user). Either
explains a silent drop. **Conclusion: this probe cannot discriminate netstack-to-self from netstack-UDP-in-general; the off-LAN laptop
probe (random `*.forge` label via 100.100.100.100, hosts file cleared, AFTER the C1 fix) remains the deciding measurement.**

## 10. Step G pre-flight (2026-09-10 ~13:35 UTC, read-only) — four corrections to §4 Step 3 / §5.4

Full plan with live measurements: `g-plan-2026-09-10.md` (same directory). Corrections that supersede this report's text:

1. **`fix/tailscale-authkey-argv` is already merged upstream.** `git ls-remote origin` → `refs/heads/main = dd96ed4` = the branch tip; the live compose on CT 101 is byte-identical to it. Only the local `main` is stale (`4b778f8`). §4 Step 3's "merge" collapses to a fast-forward.
2. **"Commit what is live" on CT 101 is unsafe as written.** The clone sits on `main @ fafe4a8` (2026-04-16, five months behind). Of the 45 dirty entries: 22 byte-identical to `origin/main`, 8 duplicate Traefik labels upstream already has, 8 `.bak` junk, **one plaintext secret** (`stacks/observability/config/alertmanager/ntfy-password`, untracked) and **one five-month regression** (media-downloads WireGuard → OpenVPN, dropping `qbt-port-sync`/`unpackerr`). Committing the set would leak a secret and regress a stack. Only **two artifacts are live-only**: three `custom.list` records (incl. `hermes`) and `stacks/infra-core/config/dynamic/homeassistant.yml`. They are authored in the local repo (G2), never committed from CT 101.
3. **The cloudflared/hermes work is not live-only.** It is on the local, unpushed branch `feat/hermes-linear-webhook` (`e268da1`); `hermes-saply.yml` is byte-identical to live and `TUNNEL_TOKEN` is a `${...}` reference.
4. **§5.4's Step 3 rollback is defective.** `git checkout HEAD~1 --` on CT 101 restores `a8902ec`, which carries `--authkey=${TS_AUTHKEY}` in argv — the exact leak `dd96ed4` fixed. Use `git checkout dd96ed4 -- stacks/networking-tailscale/docker-compose.yml`.

Confirmed live: `RouteAll: true` persisted (§8 CRITICAL-1 stands); `AdvertiseRoutes` and `PrimaryRoutes` both `192.168.50.0/24` (route approved); no `tailscale0` on CT 101 (flag inert today); compose project has exactly one service (scoped `up -d` cannot reach Pi-hole/Traefik); node-key expiry disabled, state file current. Two items need the operator: `deploy-applications.yml` uses `git: force: false` and **fails on the dirty tree**, so the Ansible change is dead code until G4 reconciles the clone; and no ACL artifact/API credential exists anywhere, so the ACL export is a manual admin-console step. Ten decisions are tabulated in `g-plan-2026-09-10.md §6`.

## 11. Step F — APPLIED 2026-09-11 11:49 UTC (CT 101), verified live

**Design (measured on `pihole/pihole:2024.07.0` = production image, 5 adversarial rounds, 18 agents):** not the `server=/…/#` forwarding I had in mind (15 s black hole when upstream is down) but a bare `address=/forge.bi-services.be/` beside the IPv4 line — dnsmasq then answers every non-A qtype for the subtree NODATA *locally* (`config … is NODATA-IPv6` in FTL's log, no forward). The five exact names ride an `addn-hosts` file at `dnsmasq.d/forge/05-forge.hosts` — the subdirectory is load-bearing: the live `conf-dir=/etc/dnsmasq.d` has no `,*.conf` filter and a hosts file placed directly there is a full DNS outage (measured). The `addn-hosts=` declaration lives in `00-forge-hosts.conf` so `custom.list` is read first and the PTR for .194 stays `alertmanager` (declaring it from `05-` flipped it to `gemma`).

**Role changes (`homelab-infra/ansible/roles/forge-dns`, 9 files, uncommitted at time of writing):** pre-existence recorded by `stat` *before* rendering and pre-change copies kept in `/opt/appdata/dns-pihole/forge-dns-prev/` (a round-3 verifier proved the `template`-register rollback deleted live files on a mode-only drift); `pihole-FTL dnsmasq-test` gate before any signal; A **and AAAA rcode** asserted for apex, per-wildcard probe label and every exact name; hermes guard asserts A + AAAA and is fatal; `tasks/main.yml` split into `reload.yml` / `verify.yml` / `rollback.yml` (< 500 lines each).

**Live result:** `--check` plan `05-forge.conf → restore, 00-forge-hosts.conf + forge/05-forge.hosts → remove`; apply `ok=29 changed=6 rescued=0`; re-apply `changed=0`; FTL pid 253388 → 327686, one re-exec (~1.1 s). From this workbench (LAN) and via `100.100.100.100`: forge apex and a random `*.forge` label → A 192.168.50.167 / AAAA NOERROR ans=0 / HTTPS NOERROR ans=0; gemma .194, ct-forge-01 .167, ct-saply-ai .164, ct-crypto-quant .165 (A + NODATA); hermes .194 + NODATA unchanged; `x.gemma` NXDOMAIN; PTR .194 = alertmanager, .167 = forge. `custom.list` md5/line count unchanged. Evidence: `evidence/fix-F/`.

**Dispositions:** C1 FIXED, C3 FIXED, C5 FIXED. C4 (`local=/bi-services.be/` black-holes the public half of the zone) OPEN — untouched by design. **The return-leg question (§1 UNPROVEN) is still open: this workbench reaches Pi-hole over eth0, so its `100.100.100.100` answers do not measure the subnet-router path. The laptop probe decides it.** Note for operators: `gemma.bi-services.be` now resolves to Traefik and returns 404 until the `gemma` router (branch `feat/gemma-traefik-route`) is deployed.

**Correction 2026-09-11 (operator evidence):** the laptop's hosts file carries NO `forge.bi-services.be` entry (only the Tailscale MagicDNS section). The `192.168.50.167 / TTL 0` answer `Resolve-DnsName` returned on 2026-09-10 therefore came through DNS — OS resolver → NRPT split-DNS rule → `100.100.100.100` → subnet router → Pi-hole — not from a hosts workaround as R0-P1-S4-004 assumed. The return leg has thus worked at least once from the off-LAN peer; the `nslookup … 100.100.100.100` timeout remains an unexplained transient. The post-F laptop probe is still the deciding measurement, but the prior is now "transport OK".

## 12. Return leg — PROVEN OK 2026-09-11 (operator measurement)

After F, the operator's laptop (`tom-note-asus`, off-LAN tailnet peer, no hosts entry) loaded the Coder login page at `https://forge.bi-services.be` over the tailnet: name resolved via `100.100.100.100` → split DNS → userspace subnet router → Pi-hole and the reply returned; HTTPS then traversed the same subnet route. **§1's UNPROVEN item is closed as working. Step 4-A (kernel mode on CT 101) is DROPPED; the D-variant is moot; C (Tailscale on CT 167) stays optional defence in depth.** The whole incident was DNS answer content (C1), as §2 concluded. Acceptance gate (a) — certificate verified from a tailnet client not on the LAN — is no longer blocked. Onboarding of further users needs no per-device work: tailnet membership + default client settings (subnets, Tailscale DNS) + a Coder user; the per-user one-time step is each user's own GitHub external-auth consent inside Coder.

## 13. Step G — EXECUTED 2026-09-11 11:53–12:16 UTC (G0–G3), verified; G4 pending PR merge

- **G1 (live, zero blip):** `tailscale set --accept-routes=false` on homelab-gateway → `RouteAll: false`, `AdvertiseRoutes`/`PrimaryRoutes` still `192.168.50.0/24` (route approved, owned); no `tailscale0`; routes/containers/DNS byte-identical to the G0 baseline. Independent verifier: PASS (whole-prefs diff = exactly one leaf key).
- **G2 (code):** local `homelab-apps` main fast-forwarded to `dd96ed4` (the argv fix was already upstream — §10 correction 1). Branch `fix/tailscale-disarm-accept-routes` @ `714b737`: compose `--accept-routes=false` on the authenticated path, bare flag removed from first-join; `.gitignore` (`*.bak-*`, `*.bak_*`, `ntfy-password`); the three live-only `custom.list` records incl. `hermes`; `homeassistant.yml` (md5-identical to live). **PR #1 https://github.com/tomamourette/homelab-apps/pull/1 — OPEN, operator merges.** `feat/hermes-linear-webhook` (`e268da1`, secret-scan clean) pushed and merged as PR #2 → `origin/main = 7438e74`. `homelab-infra` `451bd84` (audit/forge-baseline, not pushed): `networking-tailscale` block in `deploy-applications.yml`, syntax-checked, explicitly dead code until G4.
- **G3 (CT 101, surgical):** `git fetch` + path-scoped checkout of the one compose file from the PR branch (md5 `5fe30efc…` == branch blob); `docker compose -f docker-compose.yml -p networking-tailscale up -d` → 10 s recreate, warm state (`already authenticated from persisted state; reasserting routes`), `TS_AUTHKEY` never read, same node identity/IP, `RouteAll` false persisted, 31/32 other containers untouched, Pi-hole/hermes/forge answers unchanged, direct path from CT 250 (`via 192.168.50.194:41641 in 1ms`). Dirty-entry count 45 → 45. Independent verifier: PASS.
- **Corrections to the plan found in execution:** §G3's "exactly one `accept-routes` hit" is wrong once the rationale comment exists — gate is *one non-comment hit, value `=false`, zero `=true`*; container count is 32 not 33 (baseline drift, not G); the `networking-tailscale.env.j2` template was inlined into the Ansible block because the phase could commit one file only.
- **New pre-existing finding (out of G scope, catalogued):** `stacks/smtp-relay/docker-compose.yml` on `origin/main` carries a **literal 16-character `RELAYHOST_PASSWORD`** (not a `${…}` reference) — committed history; owed rotation + a history-rewrite decision; it is what the repo's own red "Security Checks" CI job trips on. `homelab-apps` CI is red on every branch for pre-existing reasons (workflow lints itself).
- **Still owed:** operator merges PR #1 → **G4** (full reconcile of CT 101's clone: tarball exists at `~/g-backup-20260911T115353Z/`, per-path blob compare against `origin/main`, reset only verified-identical paths; the `.bak`/secret files stay untracked) → then `deploy-applications.yml --tags networking-tailscale --check`. The backup dir holds UNREDACTED node private keys (700/600) — shred after G4 closes. Off-LAN post-recreate confirmation: any laptop page load after 12:10 UTC counts.
