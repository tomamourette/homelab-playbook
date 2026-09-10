---
type: story
epic: FE2
id: FE2-S05
title: "Caddy static site block for forge.bi-services.be with DNS-01 via caddy-dns/cloudflare"
size: M
priority: MUST
owner: dev
blocking: false
fr_refs: [FR-CTL-005]
nfr_refs: [NFR-SEC-001, NFR-SEC-003]
adr_refs: [ADR-005]
risk_refs: [R7]
gate_refs: [a]
status: in-progress
date: 2026-09-09
---

# FE2-S05: Caddy static site block for forge.bi-services.be with DNS-01 via caddy-dns/cloudflare

> **~~BLOCKED — do not start.~~ BLOCKER LIFTED 2026-09-09 — banner retained for the record.**
> Both §5.4 prerequisites now exist and were verified on the facts, not waived:
> `vault_forge_github_client_id` (20 chars) and `vault_forge_github_client_secret` (40) satisfy
> FE0-S01, and `vault_cloudflare_api_token` (53) + `vault_cloudflare_zone_id` satisfy FE0-S02 —
> all four present in `ansible/inventories/homelab/group_vars/vault.yml`. Lengths are of the
> **unquoted** values; no secret value was read or printed. See FE2-S06's banner for the full
> verification note. The original banner text follows unchanged:
>
> **BLOCKED — do not start.** Per §5.4 of the approved proposal, nothing in FE1–FE4 begins
> before **both** operator prerequisites exist:
> 1. **GitHub OAuth App** → `CODER_EXTERNAL_AUTH_0_ID/TYPE/CLIENT_ID/CLIENT_SECRET` (FE0-S01).
>    The only non-optional external credential in the whole PoC. Without it the workspace build
>    **fails** — `data "coder_external_auth" "github"` (`coder/templates/forge/main.tf:25-27`) has
>    no `optional = true` — and even if it did not, `forge-sync.sh` sources its token from
>    `coder external-auth access-token github` and **silently skips its entire clone block**, so
>    agentic-ai never lands and gates (b)–(e) are untestable.
> 2. **Cloudflare API token**, DNS-edit scope, zone `bi-services.be` (FE0-S02). Required for
>    **any** browser-trusted certificate — the homelab has no inbound :80/:443, so HTTP-01 is
>    impossible, not merely inconvenient. Wildcard scope is optional; the token is not.
>    **REVERSED 2026-09-09 — a wildcard IS required.** The token sentence still holds and the
>    token needs no re-scoping; only the "wildcard scope is optional" clause is dead. See the
>    amendment at the top of [ADR-005](../adrs/ADR-005-dns-01-wildcard-over-public-ingress.md).

## User Story

As **tomamourette**, I want **Caddy on `ct-forge-01` serving `forge.bi-services.be` from a static site block that reverse-proxies to coderd, obtaining its certificate via DNS-01 through the `caddy-dns/cloudflare` plugin, with the Cloudflare API token stored as a 0600 root-owned systemd `EnvironmentFile`**, so that **coder's web UI and code-server open over a browser-trusted certificate for a tailnet client with no public inbound port ever opened, and I never carry the Azure `on_demand_tls` machinery that this deployment doesn't need**.

## Background and Context

The Azure deployment's Caddy configuration uses `on_demand_tls` plus an "undocumented ask-server on `:9111`" (per §2.3's technical impact table) because it needs to serve **arbitrary per-SNI names** — that VM fronts more than one hostname pattern. `ct-forge-01` serves exactly one fixed hostname, `forge.bi-services.be`. Per evidence item **E5**, the correct substitution is a **static** Caddy site block: on-demand TLS and the ask-server exist to solve a problem this single-host PoC does not have, and carrying them forward would be complexity with no purpose (and, per ADR-005, `on_demand_tls` combined with a public-facing ask endpoint is itself a mild attack-surface increase that a static config avoids entirely).

DNS-01 is not optional here, and the reason is structural, not a preference: the homelab has **no inbound :80/:443** at all (canon E6.2), so HTTP-01 challenge validation is categorically impossible, not merely harder. DNS-01 validates ownership via a DNS TXT record instead, which needs only an **outbound** API call to Cloudflare — consistent with the homelab's Tailscale-first, no-public-ingress posture. The correct citation for that posture is **`homelab-playbook/wiki/architecture/tailscale-policy.md:20-31`** ("Public DNS / port-forward and SSH-key distribution both stay fallback-or-disabled unless Tailscale is genuinely insufficient") and **`wiki/architecture/remote-access-topology.md:15-40`**. Per HARD RULE 1 and risk **R7**, this story must **never** cite "ADR-010" for this policy — no such ADR exists in this estate; the only ADR-010 in the tree is `products/context-stack/adrs/ADR-010-decommission-as-single-pr.md`, an unrelated decommission document, and citing it here would be a fabricated reference that propagates into every downstream artifact that copies this story.

Wildcard SAN is explicitly **not** required: `coder_app "code_server"` in the workspace template sets `subdomain = false` (canon, verified fact table), meaning code-server is path-proxied under the same hostname rather than served from a per-workspace subdomain. This story therefore requests a certificate for `forge.bi-services.be` alone — a wildcard (`*.forge.bi-services.be`) is optional future scope for `forge-preview-url`, not a requirement here, and per the Terraform DNS rule, **a wildcard must never enter `fqdn_dns_records`** (dnsmasq/Pi-hole rejects `*` entries in that hosts-format map) — any wildcard scope belongs only in the Cloudflare DNS-01 challenge itself, never in the Terraform-managed local DNS output.

> **DECISION REVERSED 2026-09-09 — a wildcard IS required. The paragraph above is left intact as the
> record of the position this story was written from; it no longer governs.**
>
> **What changed.** The paragraph's reasoning is sound but its premise was too narrow. `coder_app
> "code_server"` really does set `subdomain = false`, so *code-server* needs no wildcard — but
> code-server is not the only thing that opens a URL. **Coder's preview URLs are subdomain-based**:
> `agentic-ai/scripts/forge-preview-url` builds a per-workspace, per-port hostname under
> `*.forge.bi-services.be`, and `CODER_WILDCARD_ACCESS_URL=*.forge.bi-services.be` is already set in
> `/etc/coder.d/coder.env` (FE2-S04). Serving only the apex means every preview URL the operator opens
> fails the TLS handshake. **The PoC must serve `*.forge.bi-services.be`.**
>
> **What that means concretely:**
> 1. ~~**Certificate SANs = two, not one:** `forge.bi-services.be` **and** `*.forge.bi-services.be`.
>    The single-SAN certificate issued on 2026-09-09 (genuine Let's Encrypt, DNS-01, journal shows
>    `challenge_type dns-01`) must be **reissued** with both names. AC1 and AC4 below are read against
>    the two-SAN expectation from this date forward.~~
>
>    **CORRECTED 2026-09-09 17:23 UTC — measured, and the "reissue with two SANs" plan was never the
>    mechanism.** Caddy does not merge a `forge.bi-services.be, *.forge.bi-services.be { }` site block
>    into one two-SAN certificate; it issues **one certificate per name**. Both are now live on CT 167
>    and both verify with no `-k`:
>
>    ```
>    SNI forge.bi-services.be     -> CN=forge.bi-services.be     SAN: DNS:forge.bi-services.be     (LE YE2)
>    SNI zz.forge.bi-services.be  -> CN=*.forge.bi-services.be   SAN: DNS:*.forge.bi-services.be   (LE YE1)
>    Verification: OK / Verify return code: 0 (ok)  for each
>    /var/lib/caddy/caddy/certificates/.../forge.bi-services.be/forge.bi-services.be.crt
>    /var/lib/caddy/caddy/certificates/.../wildcard_.forge.bi-services.be/wildcard_.forge.bi-services.be.crt
>    ```
>
>    The apex certificate was **never reissued** and did not need to be: `notBefore` is still
>    `Sep 9 13:54:39 2026 GMT`, while the wildcard certificate is a separate, later issuance
>    (`Sep 9 16:09:35 2026 GMT`). **Read AC1 and AC4 as "both names present a browser-trusted
>    certificate", never as a SAN count** — counting SANs on the apex returns `1` on a fully correct
>    deployment, so a SAN-count check fails the working system. `tests/acceptance.md` §2 gate (a)
>    carries the same correction and the full command output.
> 2. ~~**`forge_caddy_wildcard` flips to `true`** in `forge-coder-host/defaults/main.yml`. That default
>    carries a comment marking this an "OPERATOR DECISION OUTSTANDING" and implementing the story's
>    position; **the decision is now made and the comment is stale**.~~
>
>    **DONE 2026-09-09 — this rider is discharged; it describes work that has already landed.**
>    `homelab-infra/ansible/roles/forge-coder-host/defaults/main.yml:655` reads
>    `forge_caddy_wildcard: true`, and the comment block above it was **rewritten, not left to rot**:
>    it now records *why* the flag is true (with it false the control plane advertised
>    `CODER_WILDCARD_ACCESS_URL=*.forge.bi-services.be` subdomain URLs the front end had no
>    certificate and no site block for), *what flipping it changes* (`templates/Caddyfile.j2` emits
>    `forge.bi-services.be, *.forge.bi-services.be` as the site address; `tasks/caddy.yml` asserts AC1
>    against that two-name form and gained an explicit `openssl` SAN probe for **both** SNI names,
>    because one trusted `curl` no longer proves the wildcard half), and *what does not change* (AC5 —
>    the wildcard still never enters `local.fqdn_dns_records`; the public record comes from the
>    separate `local.wildcard_dns_records`, and internal resolution from the additive dnsmasq
>    `address=` drop-in). The string "OPERATOR DECISION OUTSTANDING" no longer appears anywhere under
>    `roles/` — `grep -rn 'OPERATOR DECISION OUTSTANDING' roles/` returns **no output**. **Nothing is
>    owed here; do not re-open it.**
> 3. **DNS on both sides:** a **public** Cloudflare wildcard record for `*.forge.bi-services.be`
>    alongside the existing `cloudflare_record.homelab["forge"]` A record, and a **Pi-hole wildcard**
>    answer for the internal/tailnet view.
> 4. **AC5 still stands, unchanged and for the original reason** — see the note under AC5.
>
> The one thing this reversal does **not** change is the Cloudflare token: a single `Zone.DNS Edit`
> grant on `bi-services.be` already covers issuing a wildcard, so FE0-S02 needs no new credential.

## Acceptance Criteria

**AC1 — Static site block, no on-demand TLS.**
- **Given** Caddy's config on `ct-forge-01`,
- **When** the operator inspects the `Caddyfile` (or JSON config) for the `forge.bi-services.be` block,
- **Then** it is a single static `site` block naming `forge.bi-services.be` explicitly, and `grep -c on_demand_tls Caddyfile` and `grep -c ':9111'` both return `0`.

**AC2 — DNS-01 via caddy-dns/cloudflare.**
- **Given** the site block's `tls` directive,
- **When** the operator inspects it,
- **Then** it specifies `tls { dns cloudflare {env.CLOUDFLARE_API_TOKEN} }` (or the equivalent JSON ACME-DNS challenge config), not the default HTTP-01/TLS-ALPN challenge.

**AC3 — Token supplied via a 0600 root-owned systemd EnvironmentFile.**
- **Given** the Caddy systemd unit,
- **When** the operator runs `systemctl cat caddy | grep EnvironmentFile` and then `stat -c '%a %U' <that path>`,
- **Then** the unit references an `EnvironmentFile=` pointing at a file containing `CLOUDFLARE_API_TOKEN=...`, and that file is mode `600`, owned by `root`.

**AC4 — Certificate issues and is browser-trusted.**
- **Given** AC1–AC3 have passed and DNS for `forge.bi-services.be` resolves to `ct-forge-01` (via the auto-derived `project_container_host_map`, FE1-S01),
- **When** the operator runs `systemctl restart caddy` and then, from a tailnet client, `curl -v https://forge.bi-services.be`,
- **Then** the TLS handshake succeeds with a certificate chain that a real browser trusts (issued by Let's Encrypt via the DNS-01 challenge), with no `-k`/`--insecure` flag needed.

> **AC4 Part A — how internal DNS was actually resolved (2026-09-09), and a caveat on the assertion
> that claims to prove it.**
>
> **The blocker AC4 hit.** AC4's "Given" assumes the name resolves. It did not, internally. Pi-hole on
> ct-docker-01 (192.168.50.194) ships `local=/bi-services.be/` in its container's
> `/etc/dnsmasq.d/02-homelab.conf`, which makes it **authoritative** for the whole zone: any
> `bi-services.be` name it does not know gets an authoritative **NXDOMAIN** and is never forwarded
> upstream. `forge.bi-services.be` was not in its `custom.list`, so it returned NXDOMAIN — and because
> the tailnet pushes a Split DNS route sending `bi-services.be` to that same Pi-hole, an **off-LAN
> tailnet client on the default `--accept-dns=true` sees the same NXDOMAIN**. The public Cloudflare A
> record existed and was correct; that alone could not satisfy AC4.
>
> **Why the obvious fix was rejected.** The Terraform-generated
> `terraform/envs/homelab/generated/pihole-custom.list` already contains `forge`, so landing it looks
> like the fix. It is not: the live `custom.list` also carries a hand-added line,
> `192.168.50.194 hermes.bi-services.be`, backing a **live** Traefik router for the Linear → Hermes
> webhook, which was never entered into Terraform. Landing the generated file **deletes that line** and
> breaks a running integration. (The live file is bind-mounted from the on-host clone at
> `/opt/homelab-apps/stacks/dns-pihole/config/`, whose working tree is dirty — 45 files — so the
> divergence is not confined to this one line either.)
>
> **The mechanism actually used — additive, not replacing.** An Ansible-managed **extra dnsmasq
> drop-in** (`05-forge.conf`) is delivered into the Pi-hole container carrying
> `address=/forge.bi-services.be/192.168.50.167`, and Pi-hole is then reloaded so it reads it.
> IaC: `ansible/roles/forge-dns` + `ansible/playbooks/forge-dns.yml` in `homelab-infra`. Three
> properties made this the right shape:
> - `address=` covers the **apex and every subdomain** from one line, so it satisfies the wildcard
>   reversal above at the same time as the apex — no second entry, no `*` anywhere.
> - It is **purely additive**: `custom.list` is **not touched**, so the `hermes` line and the other 44
>   dirty files are left exactly as they are. Nothing is deleted or reconciled as a side effect.
> - It is IaC (an Ansible task), not a hand-edit, so it survives a container recreate the way the
>   hand-added `hermes` line does not.
>
> **VERIFICATION — the state of this slice as of 2026-09-09 17:16 UTC, and the check that catches
> the failure it hit earlier the same day.**
>
> **Delivering the file is not the same as landing the record, and this slice proved it.** An earlier
> review of this note at **17:06 UTC** found the drop-in present on disk (`05-forge.conf`,
> mtime 16:44 UTC) while `dig forge.bi-services.be @192.168.50.194` still returned
> **`status: NXDOMAIN`** — because `pihole-FTL` had not restarted since **six days before** the file
> was written. The file was correct and the name did not resolve. The sentence above, as first
> written, asserted the reload as if delivery implied it; it did not, and this paragraph exists so
> that claim is never read that way again.
>
> **The check that distinguishes the two states — use it, not the file's existence:**
>
> ```
> docker exec pihole stat -c %y /etc/dnsmasq.d/05-forge.conf   # when the config was written
> docker exec pihole sh -c 'stat -c %y /proc/$(pidof pihole-FTL)'  # when the resolver last started
> ```
>
> If FTL started **before** the file was written, the reload never took effect no matter how green the
> playbook looked. `dnsmasq` re-reads hosts files on `SIGHUP` but **never** re-reads its config files,
> and `address=` lives in a config file — so nothing short of an FTL restart applies this drop-in.
>
> **Measured now, and it passes.** Run from the Ansible control host (192.168.50.156):
>
> ```
> conf mtime  2026-09-09 19:09:18 +0200
> FTL start   2026-09-09 19:09:19 +0200      # 1.2 s AFTER the config was written - the reload took
>
> dig +short forge.bi-services.be     @192.168.50.194  -> 192.168.50.167
> dig +short zz.forge.bi-services.be  @192.168.50.194  -> 192.168.50.167   (wildcard: any subdomain)
> dig +short hermes.bi-services.be    @192.168.50.194  -> 192.168.50.194   (untouched, still live)
> dig        forge.bi-services.be     @192.168.50.194  -> status: NOERROR, flags: qr aa  (was NXDOMAIN)
> ```
>
> **Idempotent, twice, at 2026-09-09 17:16 UTC:** two consecutive
> `ansible-playbook playbooks/forge-dns.yml` runs both reported
> `ok=6 changed=0 unreachable=0 failed=0 skipped=4 rescued=0 ignored=0`, with the conf mtime and the
> FTL start time identical before and after — i.e. the converged host re-asserts the invariant without
> restarting DNS. The role only reloads when its own probe (`dig` against the running FTL, not the
> file on disk) shows a record missing, which is why a re-run does not churn the resolver.
>
> **Scope of what this proves.** Internal resolution for the apex and every subdomain, from a LAN
> client, against the authoritative resolver. It does **not**, on its own, prove the certificate side:
> a name that resolves and a certificate that matches it are two different gates.
>
> **That second gate is CLOSED as of 2026-09-09 16:09 UTC — the wildcard slice is not open.** Caddy on
> CT 167 serves `forge.bi-services.be` **and** `*.forge.bi-services.be`, as **two separate single-SAN
> Let's Encrypt certificates**: the apex (`notBefore Sep 9 13:54:39 2026 GMT`, never reissued) and the
> wildcard (`notBefore Sep 9 16:09:35 2026 GMT`, a later, independent issuance). Each verifies with
> **no `-k`** (`Verify return code: 0 (ok)`) under its own SNI. This is the mechanism, not a shortfall:
> **Caddy/CertMagic manages one certificate per subject**, so a single dual-SAN *managed* certificate
> is not obtainable for a two-name site block at all — it would require dropping to statically
> supplied certs. **Read AC1 and AC4 as "every SNI name presents a browser-trusted certificate
> covering that name", never as a SAN count**: counting SANs on the apex returns `1` on a fully
> correct deployment, so a SAN-count check fails the working system. Item 1 of the reversal note above
> and `tests/acceptance.md` §2 gate (a) carry the same correction and the full command output.
>
> **Explicitly deferred:** reconciling `hermes.bi-services.be` into Terraform. It is real, live, and
> untracked, and it should be brought under IaC — but **not** as a side effect of this story. Recorded
> in `follow-ups.md`.
>
> **CAVEAT on the role's own assertion.** The `forge-coder-host` role has a task literally named
> **"Assert AC4 Part A — the name reaches this host over a trusted chain"**
> (`ansible/roles/forge-coder-host/tasks/caddy.yml`). **That name overstates what the task proves.**
> The task builds its `curl` argv conditionally: when the host's own resolver cannot see the name
> (`getent ahostsv4` fails — which was the case for the entire period this gap was open) it falls back
> to `--resolve forge.bi-services.be:443:192.168.50.167`. `--resolve` **bypasses DNS entirely**. So on
> that path the assertion proves the certificate, the chain, the reverse-proxy upstream and that this
> host answers — but it does **not** prove that the name resolves, which is the one thing "Part A"
> was added to prove. The role is honest about this in its `success_msg` (it appends "via `--resolve`
> …; the host resolver is a split horizon with no record") and its separate public-resolver `dig`
> gate is a genuine check of the public view; it is the **task name** that is wrong, not the logic.
> **The CT 167 agent may or may not rename it. If you are reading a green "Assert AC4 Part A" in a
> log, check which branch it took before treating it as proof of resolution.**

**AC5 — No wildcard in the Terraform-managed DNS map.**
- **Given** `homelab-infra/terraform/envs/homelab/outputs.tf`,
- **When** the operator runs `grep -n '\*' outputs.tf | grep -i fqdn`,
- **Then** no wildcard pattern appears in `fqdn_dns_records` — any wildcard scope the operator chose to include on the Cloudflare token (FE0-S02) is irrelevant to this file and must never be added to it.

> **AC5 SURVIVES THE 2026-09-09 WILDCARD REVERSAL — do not "fix" it. This AC is not about whether a
> wildcard exists; it is about which map a wildcard is allowed to live in.** `fqdn_dns_records`
> renders **hosts-format** lines (`<ip> <name>`) for Pi-hole's `custom.list`, and dnsmasq rejects a
> `*` in that format outright — a wildcard entered there does not produce a wildcard answer, it
> produces a broken file. So the grep must still return nothing, exactly as written.
>
> The wildcard the reversal requires is served from two places that are **not** this map:
> - **Internally**, by an additive dnsmasq drop-in on Pi-hole carrying
>   `address=/forge.bi-services.be/192.168.50.167` — the `address=` form covers the apex **and every
>   subdomain** in one line, which is precisely why it is used instead of `custom.list`. See the AC4
>   Part A note below for the full mechanism and why `custom.list` is not touched.
> - **Publicly**, by a Cloudflare wildcard record for `*.forge.bi-services.be`, which lives in the
>   Cloudflare-facing map, never in `fqdn_dns_records`.
>
> A reviewer flipping AC5 because "we decided to do wildcards now" would break Pi-hole's config file
> and would not gain a wildcard answer. **Leave it.**

**AC6 — "ADR-010" appears only as the fabricated citation this story rejects.**
- **Given** this story's own text (whose Background and Context necessarily names the fabricated citation in order to reject it) and any code comments it introduces,
- **When** the operator runs `grep -rn 'ADR-010' <this story file and any new Caddy config/comments> | grep -viE 'does not exist|fabricated|rejected'`,
- **Then** the command produces **no output** — every remaining mention of "ADR-010" names only the fabricated, rejected reference this story explicitly repudiates, never a live justification. The citation used for the no-public-ingress rationale is `wiki/architecture/tailscale-policy.md:20-31` and `wiki/architecture/remote-access-topology.md`.

## Implementation Notes

Reference E5, E6.2, ADR-005, HARD RULE 1, R7. This task set belongs in the `forge-coder-host` role family alongside FE2-S01/S02/S03/S06.

```
# Caddyfile — illustrative shape
forge.bi-services.be {
	reverse_proxy localhost:3000
	tls {
		dns cloudflare {env.CLOUDFLARE_API_TOKEN}
	}
}
```

```ini
# /etc/caddy/cloudflare.env — mode 600, root:root
CLOUDFLARE_API_TOKEN=<the FE0-S02 token>
```

```ini
# systemd drop-in or unit override
[Service]
EnvironmentFile=/etc/caddy/cloudflare.env
```

```bash
# AC verification
grep -c on_demand_tls /etc/caddy/Caddyfile   # expect 0
grep -c ':9111' /etc/caddy/Caddyfile         # expect 0
systemctl cat caddy | grep EnvironmentFile
stat -c '%a %U' /etc/caddy/cloudflare.env    # expect "600 root"
curl -v https://forge.bi-services.be         # from a tailnet client, no -k
grep -n '\*' homelab-infra/terraform/envs/homelab/outputs.tf | grep -i fqdn   # expect nothing
```

Caddy on Debian needs the `caddy-dns/cloudflare` plugin built into the binary (xcaddy build, or the official Caddy APT repo's plugin-enabled package if available) — verify which build path Debian 13's Caddy package supports before assuming a plain `apt install caddy` includes it; if not, document the xcaddy build step in the role.

## Test Plan

**Pre-state:** Coderd running (FE2-S04), Cloudflare DNS-edit token exists (FE0-S02), `forge.bi-services.be` DNS not yet issuing certificates.

**Action sequence:**
1. Confirm Caddy build includes `caddy-dns/cloudflare` (or build it).
2. Write the Caddyfile, `cloudflare.env`, and systemd `EnvironmentFile` wiring (AC1–AC3).
3. `systemctl restart caddy`; watch `journalctl -u caddy -f` for the ACME DNS-01 challenge and certificate issuance.
4. From a tailnet client (not the LAN), `curl -v https://forge.bi-services.be` (AC4).
5. Grep `outputs.tf` for wildcard entries (AC5).
6. Run AC6's grep-and-filter check across this story and any new config/comments; confirm no output — every remaining "ADR-010" mention is the fabricated, rejected reference (AC6).

**Post-state checks:**
- Certificate chain trusted by curl/browser with no `-k`.
- No `on_demand_tls`/`:9111` in the Caddy config.
- Token file 600 root-owned.
- Zero wildcard entries in `fqdn_dns_records`.

**Rollback:** `systemctl stop caddy`; remove the site block; the coderd service remains reachable over plain HTTP on localhost for further debugging without exposing it externally.

## Dependencies

- **Blocked by:** FE0-S02 (Cloudflare token), FE2-S04 (coderd running to proxy to), FE1-S01 (DNS auto-derivation registers `ct-forge-01`'s A record).
- **Blocks:** FE4-S01 (first workspace create needs a reachable, trusted UI), gate (a) in FE4-S02.

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Debian 13's packaged Caddy lacks the `caddy-dns/cloudflare` plugin | Medium | Medium — needs an xcaddy custom build | Verify the build path before relying on `apt install caddy`; document whichever path is actually used |
| Cloudflare token scoped too narrowly (e.g., missing zone read alongside DNS-edit) | Low | Medium — DNS-01 challenge fails with an API error | FE0-S02's AC should already cover token scope; this story's AC4 catches it in practice via the actual challenge attempt |
| A future edit reintroduces `on_demand_tls` "to be safe" without re-deriving why it was removed | Low | Low functionally, but reopens the attack-surface question ADR-005 settled | ADR-005 documents the rationale; AC1 is a repeatable grep-based regression check |
| Someone cites "ADR-010" out of habit, without the fabricated/rejected framing this story requires (a genuine, unrelated ADR-010 exists once elsewhere in the estate) | Low | Low individually, but R7 says it's expensive to unpick once it propagates | AC6's grep-and-filter check is explicit and mechanical, not left to memory |

## Definition of Done

- [ ] AC1–AC6 all green and evidenced.
- [ ] Caddyfile, `cloudflare.env`, and systemd EnvironmentFile wiring committed as Ansible tasks/templates.
- [ ] `https://forge.bi-services.be` verified browser-trusted from a tailnet client.
- [ ] Zero wildcard entries in `fqdn_dns_records`; every "ADR-010" mention anywhere this story touched is the fabricated, rejected reference, never a new citation.
- [ ] Story status updated from `draft` to `done` in this file's frontmatter.
