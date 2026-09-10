---
adr: 005
title: "DNS-01 certificate via Cloudflare over public ingress; wildcard scope REQUIRED (amended 2026-09-09, was: kept optional)"
status: accepted
date: 2026-09-09
authors: tomamourette (with BMad assist)
evidence_ref: E6
---

# ADR-005: DNS-01 certificate via Cloudflare over public ingress; wildcard scope REQUIRED

*(Title amended 2026-09-09. It read "…; wildcard scope kept optional" until the reversal below. The
frontmatter `title:` was amended with it, so anything that indexes frontmatter rather than prose
reads the current decision.)*

> ## AMENDMENT — DECISION REVERSED 2026-09-09: the wildcard IS required
>
> **Scope of the reversal: the wildcard clause only.** Everything else in this ADR — DNS-01 over
> public ingress, the Cloudflare token as a 0600 root-owned `EnvironmentFile`, the static site block
> replacing `on_demand_tls` and the `:9111` ask-server, the fabricated-citation correction (R7), and the
> rule that a wildcard must never enter `fqdn_dns_records` — **stands unchanged and is not reopened.**
> The original text below is left intact as the record of what was decided and why; the paragraphs it
> reverses are flagged in place.
>
> **What was decided (original):** "Wildcard scope is optional, not required," on the grounds that
> `coder_app "code_server"` sets `subdomain = false` and is path-proxied, so nothing in PoC scope
> exercises a wildcard SAN.
>
> **What is decided now:** **`*.forge.bi-services.be` is served.** The original reasoning was correct
> about code-server and wrong about the PoC's surface: **Coder's preview URLs are subdomain-based.**
> `agentic-ai/scripts/forge-preview-url` constructs a per-workspace, per-port hostname under
> `*.forge.bi-services.be`, and `CODER_WILDCARD_ACCESS_URL=*.forge.bi-services.be` is already set in
> `/etc/coder.d/coder.env` on CT 167. The ADR treated `forge-preview-url` as "not exercised by anything
> in the PoC's scope"; it is the operator-facing way a running workspace is opened, so it is in scope.
>
> **Consequences of the reversal:**
> 1. **Both `forge.bi-services.be` and `*.forge.bi-services.be` must present a browser-trusted
>    certificate.** ~~The single-SAN certificate genuinely issued via DNS-01 on 2026-09-09 must be
>    **reissued** with both names.~~ **Corrected 2026-09-09 17:23 UTC, measured:** that describes work
>    that never happened and was never needed. Caddy issues **one certificate per name** for a
>    two-name site block, so CT 167 now serves two separate Let's Encrypt certificates
>    (`CN=forge.bi-services.be`, issued 13:54 UTC, untouched; `CN=*.forge.bi-services.be`, issued
>    16:09 UTC), each with a single SAN, both verifying with no `-k`. **This consequence is about
>    coverage, not about SAN cardinality** — any acceptance check written as "the certificate carries
>    two SANs" fails the correct deployment. See `tests/acceptance.md` §2 gate (a).
> 2. **DNS on both sides.** A **public** Cloudflare wildcard record for `*.forge.bi-services.be`
>    alongside `cloudflare_record.homelab["forge"]`; and a **Pi-hole wildcard** answer for the internal
>    and tailnet views, delivered as an additive dnsmasq `address=/forge.bi-services.be/192.168.50.167`
>    drop-in (that form covers apex and all subdomains in one line). See FE2-S05's AC4 Part A note.
> 3. ~~**`forge_caddy_wildcard: false` in `forge-coder-host/defaults/main.yml` is now stale**, along with
>    its "OPERATOR DECISION OUTSTANDING" comment. The decision is made.~~ **DONE 2026-09-09 — this
>    consequence is discharged, not owed.** That default now reads `forge_caddy_wildcard: true`
>    (`homelab-infra/ansible/roles/forge-coder-host/defaults/main.yml:655`), and its comment block was
>    rewritten to state why it is true, what flipping it changes (two-name site address in
>    `Caddyfile.j2`; AC1 asserted against that form; an `openssl` SAN probe for both SNI names in
>    `tasks/caddy.yml`) and what it does not change (AC5). `grep -rn 'OPERATOR DECISION OUTSTANDING'
>    roles/` returns **no output**. See FE2-S05's reversal note, item 2.
> 4. **"A wildcard must never enter `fqdn_dns_records`" is UNAFFECTED and still binding.** That rule is
>    about which map may hold a `*`, not about whether a wildcard exists. dnsmasq rejects `*` in the
>    hosts-format map that output renders; the wildcard lives in the Cloudflare-facing map and in the
>    dnsmasq `address=` drop-in, never there.
> 5. **The Cloudflare token needs no change.** A single `Zone.DNS Edit` grant on `bi-services.be`
>    already permits issuing a wildcard — which is exactly what the original text said when it noted
>    the scope "technically permits issuing a wildcard later if needed." That later is now.
>
> **Cost of the reversal:** the negative the ADR listed for requesting a wildcard — widening the
> token's *practical* usage without a PoC-scope consumer — no longer applies, because a PoC-scope
> consumer was found. What remains is that a wildcard certificate covers every name under
> `forge.bi-services.be`, so a future service accidentally published on that subdomain inherits a valid
> certificate it did not ask for. Accepted for a single-operator PoC on a host with no public inbound.
>
> **Reversal trigger for THIS amendment:** if preview URLs are dropped from the operator's workflow,
> or Coder moves them to a path-proxied form, drop back to the apex alone — it is a
> `forge_caddy_wildcard` flip, after which Caddy simply stops renewing the wildcard certificate.
> Nothing structural, and no reissue of the apex certificate is involved either way.

## Context

Gate (a) of the PoC's acceptance criteria requires Coder's web UI and code-server to open over a
**browser-trusted certificate with no warning**, verified from a **tailnet client not on the LAN**. The
homelab has no public inbound `:80`/`:443` — this is a deliberate, existing posture, not a PoC-specific
constraint. A certificate strategy has to work within that posture rather than around it.

## Decision

Issue a **DNS-01** certificate for `forge.bi-services.be` via a **Cloudflare API token scoped to
DNS-edit on the `bi-services.be` zone**, served from a **static** Caddy site block using
`caddy-dns/cloudflare`. The token is supplied as a **0600 root-owned systemd `EnvironmentFile`**.

### Basis

**E6.2.** DNS-01 needs **no inbound connection** — it proves domain control by publishing a TXT record,
not by answering an HTTP challenge on a listening port. This is exactly what makes it compatible with
the homelab's Tailscale-first, no-public-ingress posture. The token is **mandatory even for a
single-name certificate**: the homelab has no inbound `:80`/`:443` at all, so **HTTP-01 is impossible,
not merely inconvenient** — there is no fallback path that avoids needing DNS-01 here.

**Wildcard scope is optional, not required.** *(REVERSED 2026-09-09 — see the amendment at the top of
this file. Retained verbatim as the record of the original decision.)* `coder_app "code_server"` sets `subdomain = false`, so
code-server is **path-proxied** and exercises no wildcard SAN at all. A wildcard certificate is only
relevant to `forge-preview-url`, which is not exercised by anything in the PoC's scope. The DNS-edit
token scope technically permits issuing a wildcard later if needed; nothing in this decision requires
requesting one now.

Caddy's `on_demand_tls`, along with the undocumented ask-server on `:9111`, is **dropped**. That
mechanism exists specifically to let Caddy serve certificates for arbitrary, not-known-in-advance
per-SNI hostnames — the shape Azure's multi-tenant ingress needs. CT 167 serves exactly one fixed
hostname; a static site block covers it with less moving state and no listening ask-server at all.

**A wildcard must never enter `fqdn_dns_records`.** That Terraform output map renders hosts-format lines
consumed by dnsmasq/Pi-hole, and dnsmasq rejects `*` entries outright. Wildcard names, if ever needed,
go into the Cloudflare-facing map only, never into the DNS-record map that feeds the LAN resolver.

**CRITICAL — correcting a fabricated citation (R7).** The no-public-ingress rule that justifies this
whole approach has, in earlier discussion, been attributed to **"ADR-010."** **No such ADR exists** in
this estate as a no-public-ingress policy. A search for "ADR-010" across the tracked repos returns
exactly one hit: `products/context-stack/adrs/ADR-010-decommission-as-single-pr.md`, which is about
decommissioning a product as a single pull request and is **unrelated** to ingress policy. The actual,
real policy this decision follows lives in
`homelab-playbook/wiki/architecture/tailscale-policy.md:20-31` ("Public DNS / port-forward and SSH-key
distribution both stay fallback-or-disabled unless Tailscale is genuinely insufficient") and
`homelab-playbook/wiki/architecture/remote-access-topology.md:15-40`. **Every citation of the
no-public-ingress rule in this artifact set, and in any future one, should point at those two wiki
pages — never at "ADR-010."** This ADR states that correction explicitly so the fabricated citation does
not propagate further.

## Consequences

### Positive

- **Zero new public inbound surface.** Certificate issuance and renewal happen over an outbound API
  call to Cloudflare; nothing new listens on the internet-facing side.
- Consistent with, and directly traceable to, the actual documented policy
  (`wiki/architecture/tailscale-policy.md:20-31`, `wiki/architecture/remote-access-topology.md`) rather
  than a document that doesn't exist.
- The Cloudflare token's scope is narrow — DNS-edit on one zone only — a least-privilege credential.
- A static site block is simpler and has strictly less attack surface than `on_demand_tls` plus a
  listening ask-server on `:9111`, neither of which this single-hostname deployment needs.
- ~~Keeping wildcard scope optional means the PoC's actual certificate need (one fixed hostname,
  path-proxied code-server) is met without requesting broader issuance rights than are currently
  used.~~
  **REVERSED 2026-09-09 — measured on CT 167; this bullet's premise is false and it is no longer a
  positive consequence.** The PoC's actual certificate need is **two names, not one**:
  `forge.bi-services.be` *and* `*.forge.bi-services.be`. `coder_app "code_server"` is indeed
  `subdomain = false`, but Coder's preview URLs are subdomain-based and
  `CODER_WILDCARD_ACCESS_URL=*.forge.bi-services.be` is live in `/etc/coder.d/coder.env` on CT 167.
  **Both names are served and both verify with no `-k`** — as **two separate single-SAN Let's Encrypt
  certificates** (apex `notBefore Sep 9 13:54:39 2026 GMT`, never reissued; wildcard `notBefore
  Sep 9 16:09:35 2026 GMT`), because Caddy/CertMagic manages **one certificate per subject**; a single
  dual-SAN *managed* certificate is not obtainable for a two-name site block. The half of this bullet
  that survives is the issuance-rights half: **no broader rights were requested** — the same single
  `Zone.DNS Edit` grant on `bi-services.be` covers the `_acme-challenge` TXT records for both names.
  Original text retained above, struck rather than deleted, as the record of what was decided. See the
  amendment at the top of this file.

### Negative

- The Cloudflare API token is a new secret that must be stored and rotated (0600 root-owned
  `EnvironmentFile`, per NFR-SEC-003) — one more credential in the estate, even though narrowly scoped.
- Certificate issuance and renewal now depend on Cloudflare's API being reachable outbound from CT 167.
  This is a new (small) external dependency where Azure's IMDS-based auth previously had none in this
  exact position — traded deliberately, since HTTP-01 was never a viable alternative here.
- DNS propagation timing can add latency at first issuance or in renewal edge cases, compared to
  HTTP-01's near-instant challenge/response — moot in practice since HTTP-01 was never available.

### Neutral

- ~~`forge-preview-url`'s wildcard need is deferred, not designed away. Nothing in the PoC exercises it,
  so the decision of whether to request wildcard SAN is a token-scope and Caddy-config decision to make
  later, not an architectural one to solve now.~~ **REVERSED 2026-09-09: the PoC does exercise it.**
  `forge-preview-url` is how a running workspace's ports are opened, and `CODER_WILDCARD_ACCESS_URL` is
  already configured on CT 167. The "later" this bullet deferred to arrived inside the PoC itself. See
  the amendment at the top of this file.

- **Alternatives entry #5 below is likewise reversed (2026-09-09).** "Request wildcard SAN now" is no
  longer the rejected alternative; it is the decision. Its second half — that a wildcard "would need to
  be kept carefully out of `fqdn_dns_records` regardless" — was right, and that discipline is now live
  rather than deferred.

## Alternatives Considered

1. **HTTP-01 challenge** — rejected outright. The homelab has no inbound `:80`/`:443`; this is not a
   matter of preference or convenience, it is structurally impossible.
2. **Public ingress** (port-forwarding `:443` to CT 167) — rejected. Directly contradicts the documented
   policy at `wiki/architecture/tailscale-policy.md:20-31`: Tailscale is not "genuinely insufficient"
   here, so the fallback of public DNS/port-forward does not apply.
3. **Self-signed or internal-CA certificate** — rejected. Gate (a) explicitly requires a
   **browser-trusted** certificate with **no warning**, verified from a tailnet client. A self-signed
   certificate fails this without extra, out-of-scope trust-store provisioning on every client.
4. **`on_demand_tls` with the ask-server on `:9111`** — rejected. That mechanism exists to serve
   arbitrary per-SNI hostnames, the pattern Azure's multi-tenant ingress needed. CT 167 serves one fixed
   hostname; a static site block achieves the same outcome with a smaller, simpler, and more auditable
   configuration, with no ask-server listening at all.
5. **Request wildcard SAN now "to be safe"** — *(REVERSED 2026-09-09; this is now the decision, not a
   rejected alternative. Text retained verbatim below as the record of the original reasoning — it
   overlooked that Coder's preview URLs are subdomain-based. See the amendment at the top.)* rejected
   for the PoC. `coder_app "code_server"` is
   `subdomain = false` and exercises no wildcard; requesting one now would widen the token's practical
   usage without any PoC-scope consumer, and would need to be kept carefully out of `fqdn_dns_records`
   regardless (a discipline better deferred until it is actually needed).

## Validation / Exit Ramp

- **Validation:** FE2-S05 configures the static Caddy site block and DNS-01 issuance via
  `caddy-dns/cloudflare`. Gate (a) is verified from a tailnet client **not on the LAN**, confirming no
  browser warning appears for either the Coder web UI or code-server. **Amended 2026-09-09:** gate (a)
  must now also be checked against a **preview URL** under `*.forge.bi-services.be`, not the apex
  alone — a two-SAN certificate that is never exercised on a subdomain has not been validated.
- **Exit ramp:** the Cloudflare token can be revoked and rotated independently of the Caddy
  configuration — only the `EnvironmentFile` value changes, requiring a service restart, not a
  redeploy. Moving to a different DNS-01 provider or ACME CA is a Caddy directive change, not a
  re-architecture, because the underlying pattern (DNS-01, static site block, no public ingress) is
  provider-agnostic.
- **Reversal trigger:** if DNS management for `bi-services.be` ever moves off Cloudflare, or if a future
  productisation phase genuinely needs per-tenant wildcard subdomains for `forge-preview-url` at scale,
  revisit the token scope and reconsider `on_demand_tls` at that point — explicitly **not before
  FE4-S05** (see [ADR-006](ADR-006-hermes-openmemory-langfuse-out-of-poc-scope.md) and R8 on why
  productisation questions are deferred).

## References

- Sprint change proposal, `sprint-change-proposal-2026-09-09.md` — E6 (specifically E6.2), R7.
- `homelab-playbook/wiki/architecture/tailscale-policy.md:20-31`
- `homelab-playbook/wiki/architecture/remote-access-topology.md:15-40`
- `products/context-stack/adrs/ADR-010-decommission-as-single-pr.md` (the only ADR-010 in the estate;
  unrelated to ingress policy — cited here only to close off the fabricated-citation error)
- PoC acceptance gate (a) — `sprint-change-proposal-2026-09-09.md` §5.3
- [ADR-006](ADR-006-hermes-openmemory-langfuse-out-of-poc-scope.md)
