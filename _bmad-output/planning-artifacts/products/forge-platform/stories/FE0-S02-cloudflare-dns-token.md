---
type: story
epic: FE0
id: FE0-S02
title: "Mint the Cloudflare DNS-edit token scoped to bi-services.be"
size: S
priority: MUST
owner: operator
blocking: true
fr_refs: [FR-PRE-002]
nfr_refs: [NFR-SEC-001, NFR-SEC-003]
adr_refs: [ADR-005]
risk_refs: [R7]
gate_refs: [a]
status: done
date: 2026-09-09
---

# FE0-S02: Mint the Cloudflare DNS-edit token scoped to bi-services.be

> **OPERATOR TASK — BLOCKING. Cannot be delegated.**

## User Story

As **tomamourette**, I want **a Cloudflare API token with DNS-edit scope on zone `bi-services.be`**, so that **Caddy can obtain a browser-trusted certificate for `forge.bi-services.be` via DNS-01, since the homelab has no inbound `:80`/`:443` and HTTP-01 is not merely inconvenient but impossible**.

## Background and Context

This is the second of the two hard blockers named in §5.4: nothing in FE1–FE4 begins before both operator prerequisites exist. Evidence item **E6.2** established why this credential is mandatory even for a single hostname: DNS-01 challenges require **no inbound connection at all**, which is the only ACME method compatible with the homelab's Tailscale-first, no-public-ingress posture. ~~The wildcard scope (e.g. `*.forge.bi-services.be`) is genuinely **optional** — `coder_app "code_server"` sets `subdomain = false`, so code-server is path-proxied through the single `forge.bi-services.be` name and exercises no wildcard SAN. Only `forge-preview-url` would ever need a wildcard, and that is out of PoC scope.~~ The **token itself is not optional** under any reading.

> **REVERSED 2026-09-09 — see the AC3 note below, which this paragraph must be read with.** The
> struck sentences were the premise AC3 was written from, and they are wrong on one point:
> `forge-preview-url` is **not** out of PoC scope. `agentic-ai/scripts/forge-preview-url` builds
> per-workspace, per-port hostnames under `*.forge.bi-services.be`, and
> `CODER_WILDCARD_ACCESS_URL=*.forge.bi-services.be` is live in `/etc/coder.d/coder.env` on CT 167.
> The PoC therefore **does** serve a wildcard. Retained here, struck, as the record of the position
> this story was written from. **The unstruck sentence still stands, and so does AC3's operative
> claim: the token needs no re-scoping, re-issue, or touch.** See
> [ADR-005](../adrs/ADR-005-dns-01-wildcard-over-public-ingress.md)'s amendment.

**Citation correction (HARD RULE 1, R7):** the originally-cited justification for this policy, "ADR-010's no-public-ingress rule," does not exist in this estate — a `grep -rn "ADR-010"` across all tracked repos returns exactly one hit, `products/context-stack/adrs/ADR-010-decommission-as-single-pr.md`, an unrelated decommissioning document. The real, applicable policy is `homelab-playbook/wiki/architecture/tailscale-policy.md:20-31` ("Public DNS / port-forward and SSH-key distribution both stay fallback-or-disabled unless Tailscale is genuinely insufficient") and `wiki/architecture/remote-access-topology.md:15-40`. This story, and every downstream artifact that touches ingress, cites those two pages — never "ADR-010."

The token feeds FE2-S05 (`caddy-dns/cloudflare` DNS-01 provider) as a 0600 root-owned systemd `EnvironmentFile`, and NFR-SEC-003 requires it never be committed to any repo.

## Acceptance Criteria

**AC1 — Token minted with least-privilege scope.**
- **Given** the operator has Cloudflare account access to the zone `bi-services.be`,
- **When** the operator creates a new API token (Cloudflare dashboard → My Profile → API Tokens → Create Token → Custom Token) with permission `Zone / DNS / Edit`, resource scope restricted to `Zone: bi-services.be` only,
- **Then** the token is created and the Cloudflare UI confirms the scope is limited to that single zone (not "All zones").

**AC2 — Token verified functional and correctly scoped.**
- **Given** AC1 has passed,
- **When** the operator runs `curl -s -X GET "https://api.cloudflare.com/client/v4/zones" -H "Authorization: Bearer <token>" -H "Content-Type: application/json"`,
- **Then** the response's `"success":true` field is `true` and the `result` array contains exactly the `bi-services.be` zone (proving the token authenticates and is not scoped to unrelated zones).

**AC3 — Wildcard scope explicitly not required.**
- **Given** `coder_app "code_server"` in `coder/templates/forge/main.tf` sets `subdomain = false` (verified fact, canon),
- **When** the operator reviews the token's DNS record permissions,
- **Then** the token does **not** need "Zone / DNS / Edit" extended to a wildcard record explicitly — a single `Zone.DNS Edit` grant on `bi-services.be` covers both the apex-style `forge.bi-services.be` A/CNAME record and any future `TXT _acme-challenge.forge.bi-services.be` record DNS-01 creates. Recorded as a note in this story, not a Terraform change.

> **DECISION REVERSED 2026-09-09 — a wildcard IS served. AC3's title is now misleading; its
> *conclusion about the token* is still correct. Original text retained above, unchanged.**
>
> **What was reversed.** AC3's premise was that no wildcard is needed at all, because
> `coder_app "code_server"` sets `subdomain = false`. That is true of code-server and **not** true of
> the PoC as a whole: **Coder's preview URLs are subdomain-based.**
> `agentic-ai/scripts/forge-preview-url` builds per-workspace, per-port hostnames under
> `*.forge.bi-services.be`, and `CODER_WILDCARD_ACCESS_URL=*.forge.bi-services.be` is set in
> `/etc/coder.d/coder.env` on CT 167. So the PoC **does** serve `*.forge.bi-services.be`:
> - **Both `forge.bi-services.be` and `*.forge.bi-services.be` present a browser-trusted
>   certificate.** (~~the single-SAN certificate issued on 2026-09-09 gets reissued with both~~ —
>   **corrected 2026-09-09 17:23 UTC:** Caddy issues one certificate **per name**, so the apex
>   certificate was never reissued and a second, wildcard certificate was issued alongside it. Both
>   verify with no `-k`. Either way this changes nothing for **this** story: one `Zone.DNS Edit`
>   grant covers the `_acme-challenge` TXT records for both names.)
> - **DNS records on both sides:** a public Cloudflare wildcard record for `*.forge.bi-services.be`,
>   and a Pi-hole wildcard answer internally (delivered as an additive dnsmasq
>   `address=/forge.bi-services.be/192.168.50.167` drop-in, which covers apex and all subdomains).
>
> **What did NOT change, and why this story needs no re-work.** AC3's operative claim — that a single
> `Zone.DNS Edit` grant on `bi-services.be` is sufficient, with no wildcard-specific permission — is
> **still exactly right**, and the reversal is the case it was written to cover: that one grant already
> permits creating the `*.forge` record and every `TXT _acme-challenge.*` the DNS-01 challenge needs.
> **The minted token does not need to be re-scoped, re-issued, or touched.** Read AC3 as "no
> wildcard-specific *token permission* is required", which is what it verifies; read its title, "Wildcard
> scope explicitly not required", as superseded.
>
> **Also superseded:** (a) **the Background paragraph above** — its "the wildcard scope is genuinely
> optional / `forge-preview-url` is out of PoC scope" sentences, now struck in place with a pointer
> back to this note; and (b) the Implementation Notes paragraph below, which reads "Any wildcard need is a
> Cloudflare-side concern only, and is out of scope here (code-server needs none)." A wildcard need now
> exists. Its first half survives intact: a wildcard still must **never** enter
> `homelab-infra/terraform/envs/homelab/outputs.tf`'s `fqdn_dns_records` — dnsmasq rejects `*` in that
> hosts-format map, so a `*` there produces a broken file, not a wildcard answer. See ADR-005's
> 2026-09-09 amendment and FE2-S05's AC5 note.

**AC4 — Token recorded and staged for FE2-S05, not yet deployed.**
- **Given** AC1–AC2 have passed,
- **When** the operator records the token value in the operator's credential store,
- **Then** the token is retrievable but not yet written to `/etc/caddy/cloudflare.env` or any systemd `EnvironmentFile` — that deployment step belongs to FE2-S05, once CT 167 and Caddy exist. No repo, tracked or untracked, contains the token value.

**AC5 — "ADR-010" appears only as the fabricated citation this file explicitly rejects.**
- **Given** HARD RULE 1 of the forge-platform canon, and that this file's own correction note in Background and Context necessarily names the fabricated citation in order to reject it,
- **When** the operator runs `grep -n "ADR-010" stories/FE0-S02-cloudflare-dns-token.md | grep -viE "does not exist|fabricated|rejected"`,
- **Then** the command produces **no output** — every remaining line that mentions "ADR-010" in this file does so only to name it as that fabricated, rejected citation (never as a live justification for the no-public-ingress posture), and the operative citations used everywhere else are `wiki/architecture/tailscale-policy.md:20-31` and `wiki/architecture/remote-access-topology.md:15-40`.

## Implementation Notes

Reference proposal §5.4(2), evidence **E6.2**, ADR-005 (dns-01-wildcard-over-public-ingress). Reference `wiki/architecture/tailscale-policy.md:20-31` and `wiki/architecture/remote-access-topology.md:15-40` for the ingress posture this token supports. This story creates **no** Terraform or Ansible state — the token is consumed as an `EnvironmentFile` by FE2-S05's Caddy role.

```bash
# AC2 — verify token scope and function
curl -s -X GET "https://api.cloudflare.com/client/v4/zones" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" | jq '.result[].name'
# Expected output: "bi-services.be" and nothing else

# AC5 — confirm every "ADR-010" mention remaining in this file is the fabricated, rejected
# citation named in the correction note, never a new justification
grep -n "ADR-010" stories/FE0-S02-cloudflare-dns-token.md | grep -viE "does not exist|fabricated|rejected"
# expect: no output
```

Do not enter a wildcard hostname into `homelab-infra/terraform/envs/homelab/outputs.tf`'s `locals.project_container_host_map` or `fqdn_dns_records` — per the canon, that map renders hosts-format lines and dnsmasq rejects `*` entries. Any wildcard need is a Cloudflare-side concern only, and is out of scope here (code-server needs none).

## Test Plan

**Pre-state:** No Cloudflare API token exists for this purpose.

**Action sequence:**
1. Create the scoped token in the Cloudflare dashboard (AC1).
2. Verify it via the `curl` zones call (AC2).
3. Confirm no wildcard scope was added (AC3).
4. Record the token in the credential store (AC4).
5. Run AC5's grep-and-filter check and confirm no output — every remaining "ADR-010" mention is the fabricated, rejected citation, not a new justification (AC5).

**Post-state checks:**
- `curl` zones call returns exactly `bi-services.be`.
- Token retrievable from the credential store by the operator.
- No repo contains the token value.

**Rollback:** Revoke the token from the Cloudflare dashboard (My Profile → API Tokens → Roll/Delete). No infrastructure state is touched by this story.

## Dependencies

- **Blocked by:** Nothing.
- **Blocks:** FE1-S01 through FE4-S02 per §5.4. Directly consumed by FE2-S05 (Caddy DNS-01).

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Token scoped too broadly ("All zones" instead of `bi-services.be` only) | Low | Medium — unnecessary blast radius if the token later leaks | AC1 requires the operator select the single-zone custom scope explicitly, verified in AC2 |
| Token committed accidentally to a repo | Low | High — credential leak, would need immediate revocation | AC4 requires a credential-store-only record; NFR-SEC-003 restates this at the artifact-set level |
| A new, non-corrective "ADR-010" citation is introduced downstream despite this story's rejected/fabricated framing | Medium | Low individually, but propagates (R7) | AC5's grep-and-filter check flags any new, non-corrective mention immediately; every downstream artifact referencing ingress must cite tailscale-policy.md / remote-access-topology.md instead |

## Definition of Done

- [ ] AC1–AC5 all green and evidenced.
- [ ] Cloudflare API token created, scoped to `Zone.DNS Edit` on `bi-services.be` only.
- [ ] Token verified functional via the `curl` zones call.
- [ ] Token recorded in the operator's credential store, confirmed absent from all git working trees.
- [ ] Story status updated from `draft` to `done` in this file's frontmatter.
