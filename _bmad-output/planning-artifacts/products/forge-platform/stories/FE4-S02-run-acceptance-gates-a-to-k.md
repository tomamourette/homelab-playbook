---
type: story
epic: FE4
id: FE4-S02
title: "Run acceptance gates (a)-(k) from a tailnet client not on the LAN; record every result including failures"
size: M
priority: MUST
owner: dev
blocking: false
fr_refs: [FR-KIT-002, FR-KIT-003]
nfr_refs: [NFR-CAP-001]
adr_refs: [ADR-003, ADR-005]
risk_refs: [R4, R5, R6]
gate_refs: [a, b, c, d, e, f, g, h, i, j, k]
status: draft
date: 2026-09-09
---

# FE4-S02: Run acceptance gates (a)-(k) from a tailnet client not on the LAN; record every result including failures

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

As **tomamourette**, I want **all eleven acceptance gates from §5.3 of the proposal executed from a
tailnet client that is not on the LAN, with every result recorded whether it passes or fails**, so
that **the FE4-S04 verdict is built on complete, honest evidence rather than a partial or
cherry-picked run**.

## Background and Context

§5.3 of the sprint change proposal defines eleven gates (a)–(k), all to be run "from a tailnet
client not on the LAN" — this is deliberate: it exercises the same path a real remote developer
would use, not a LAN shortcut that would hide a DNS-01 or Tailscale-routing problem. Gate (g)
(`docker run --rm hello-world` inside the workspace) is explicitly **non-gating** per ADR-003 and
E1 of the proposal — nested Docker has zero automated consumers in agentic-ai, and its failure
degrades the PoC rather than ending it — but ADR-003 still requires the result to be **recorded
either way**, not silently skipped. Gate (h) (`free -g` on pve3, swap-thrashing check) is the R4
sizing conflict measured rather than resolved; gate (k) (`ha-manager status` +
`/etc/pve/replication.cfg`) is the ct:151 lesson re-applied to CT 167 (R6). Per HARD RULE 1, gate
(a)'s certificate trust chain is never described as satisfying "ADR-010" — the real policy is
`homelab-playbook/wiki/architecture/tailscale-policy.md:20-31` and
`wiki/architecture/remote-access-topology.md`, cited via ADR-005.

This story does not judge the results — it only runs every gate and records what happened. The
judgment (PORTS / PORTS-WITH-CAVEATS / DOES-NOT-PORT) is FE4-S04's job alone.

## Acceptance Criteria

**AC1 — Gate (a): browser-trusted certificate, no wildcard SAN.**
- **Given** Caddy issues a DNS-01 certificate for `forge.bi-services.be` (FE2-S05),
- **When** the operator, from a tailnet client **not on the LAN**, opens `https://forge.bi-services.be`
  and the workspace's `coder_app "code_server"` URL in a browser and inspects the certificate,
- **Then** both load with no browser warning, the issuer is a real CA (not self-signed), and no
  wildcard SAN is present (`coder_app "code_server"` is `subdomain = false`).

> **AC1 AMENDED 2026-09-09 — the "no wildcard SAN" clause is REVERSED. Original text retained above;
> read AC1 with this note. As written, AC1 would FAIL the correct configuration.**
>
> The director decision of 2026-09-09 reverses the wildcard position held by FE2-S05, ADR-005 and
> FE0-S02 AC3: **Coder's preview URLs are subdomain-based**
> (`agentic-ai/scripts/forge-preview-url`), and `CODER_WILDCARD_ACCESS_URL=*.forge.bi-services.be` is
> already set in `/etc/coder.d/coder.env` on CT 167, so the PoC **must** serve
> `*.forge.bi-services.be`. See ADR-005's amendment.
>
> **Read AC1's "Then" as:**
> - both load with no browser warning, and the issuer is a real CA (not self-signed) — **unchanged**;
> - **both** `forge.bi-services.be` **and** a name under `*.forge.bi-services.be` present a
>   browser-trusted certificate. **Serving only the apex is a FAIL, not a pass.**
> - **and one check is added, because a wildcard that is never exercised on a subdomain has not been
>   validated:** open a **preview URL** under `*.forge.bi-services.be` from the same tailnet client
>   and confirm it too loads with no warning.
>
> **SECOND CORRECTION 2026-09-09 (17:23 UTC) — "exactly two SANs" is ALSO wrong, and would fail the
> working configuration for the opposite reason. Measured, not reasoned.**
>
> Caddy does **not** issue one certificate carrying two SANs for a `a.example, *.a.example { }` site
> block. It issues **one certificate per name**, and that is what is live on CT 167 right now:
>
> ```
> $ echo | openssl s_client -connect 192.168.50.167:443 -servername forge.bi-services.be \
>       | openssl x509 -noout -subject -issuer -ext subjectAltName
> subject=CN = forge.bi-services.be
> issuer=C = US, O = Let's Encrypt, CN = YE2
> X509v3 Subject Alternative Name:  DNS:forge.bi-services.be
>
> $ echo | openssl s_client -connect 192.168.50.167:443 -servername zz.forge.bi-services.be \
>       | openssl x509 -noout -subject -issuer -ext subjectAltName
> subject=CN = *.forge.bi-services.be
> issuer=C = US, O = Let's Encrypt, CN = YE1
> X509v3 Subject Alternative Name:  DNS:*.forge.bi-services.be
>
> # both chains verify with no -k:
> Verification: OK          Verify return code: 0 (ok)      (for each SNI)
>
> # on disk, two separate ACME certificates:
> /var/lib/caddy/caddy/certificates/acme-v02.api.letsencrypt.org-directory/forge.bi-services.be/forge.bi-services.be.crt
> /var/lib/caddy/caddy/certificates/acme-v02.api.letsencrypt.org-directory/wildcard_.forge.bi-services.be/wildcard_.forge.bi-services.be.crt
> ```
>
> **So "reissue the single-SAN certificate with two SANs" describes work that was never needed and
> never happened.** A `subjectAltName` count is the wrong instrument here: run it against the apex and
> you will read `1` on a fully correct deployment.
>
> **The requirement this gate actually encodes — express it this way, and check it this way:**
> *both* `forge.bi-services.be` *and* an arbitrary name under `*.forge.bi-services.be` present a
> browser-trusted certificate, from a tailnet client, with no `-k` and no warning. How many
> certificates that takes is Caddy's business.
>
> ```
> $ curl -sS -o /dev/null -w '%{http_code} ssl_verify=%{ssl_verify_result}\n' https://forge.bi-services.be/
> 200 ssl_verify=0
> $ curl -sS -o /dev/null -w '%{http_code} ssl_verify=%{ssl_verify_result}\n' https://zz.forge.bi-services.be/
> 400 ssl_verify=0
> ```
>
> `ssl_verify=0` on **both** is the pass condition. The `400` on the subdomain is **not** a TLS
> failure — the response carries `via: 1.1 Caddy` and `x-coder-build-version: v2.36.4+10fd510`, i.e.
> TLS terminated, Caddy proxied, and **coderd** rejected a preview hostname with no workspace behind
> it. Expected until `FE4-S01` creates one. When a workspace exists, re-run this against its real
> preview URL and expect a `200`; a non-TLS status code from coderd is not a gate (a) failure.
>
>
> The parenthetical "(`coder_app "code_server"` is `subdomain = false`)" is still a true statement
> about code-server; it was simply never the whole surface. Gate (a) in `tests/acceptance.md` carries
> the same amendment.

**AC2 — Gate (b): agentic-ai present, company-overlay not double-cloned.**
- **Given** FE4-S01 completed,
- **When** the operator runs `ls ~/workspace/repos/github/` and
  `test -d ~/workspace/repos/github/company-overlay; echo $?` inside the workspace,
- **Then** at least one repo is present via the GitHub token clone, and the second command returns
  `1` (absent).

**AC3 — Gate (c): forge toolchain lists tools, both API keys unset.**
- **When** the operator runs `cat ~/.forge-toolchain` inside the workspace,
- **Then** it lists `claude`, `codex`, `gh`, `terraform`, and reports both provider API keys as
  unset — the subscription-auth path is intact, not a fallback API-key path.

**AC4 — Gate (d): skill count and settings registrations.**
- **When** the operator runs `ls ~/.claude/skills | wc -l`, inspects `~/.claude/settings.json` for
  global MCP/hook registrations, and inspects the resolved project root's `.claude/settings.json`,
- **Then** the skill count is **≥ 200**, the home-level file has exactly **2** global registrations,
  and the project-root file has exactly **18** (restated per C1 — "18 in `$HOME`" is false; 18 is
  the project-root figure).

**AC5 — Gate (e): claude starts under subscription OAuth.**
- **When** the operator runs `claude` inside the workspace and issues one prompt,
- **Then** it answers without prompting for an API key — the actual product value the PoC exists to
  test.

**AC6 — Gate (f): empty-file-means-disabled contract, end to end.**
- **When** the operator runs `stat -c%s ~/.config/forge/openmemory.env ~/.config/forge/langfuse.env`,
  greps the workspace build log for two "skipped" lines, and runs `sudo -n true; echo $?`,
- **Then** both files are exactly 0 bytes, both "skipped" lines are present in the log, and
  `sudo -n true` exits `0`.

**AC7 — Gate (g), NON-GATING per ADR-003: nested Docker.**
- **When** the operator runs `docker run --rm hello-world` inside the workspace,
- **Then** the pass/fail result is recorded verbatim in this story's results log **regardless of
  outcome** — per ADR-003 and E1, a failure here does not block or downgrade the FE4-S04 verdict by
  itself.

**AC8 — Gate (h): pve3 capacity headroom with the workspace running (R4, measured not resolved).**
- **When** the operator runs `free -g` on pve3 while the FE4-S01 workspace is running, and inspects
  `swapon --show` / `vmstat 1 5` on CT 167,
- **Then** pve3's headroom is recorded verbatim, and CT 167's swap-thrashing state (thrashing /
  not thrashing) is stated explicitly — this AC measures the open R4 decision, it does not close it.

**AC9 — Gate (i): wall-clock create-to-reachable baseline.**
- **Given** FE4-S01-AC5 already recorded a `T1 − T0` baseline,
- **When** the operator copies that figure into this story's results log,
- **Then** the gate-(i) baseline is present here as the canonical acceptance-suite record.

**AC10 — Gate (j): terraform plan is clean apart from CT 167; no phantom recreation.**
- **When** the operator runs a narrowly `-target`ed `terraform plan` against the homelab root
  (`-target=module.ct_forge_01` plus the two `outputs.tf` locals), per NFR-IAC-002,
- **Then** the plan shows no changes beyond what FE1 already applied, and specifically shows **no**
  `module.ct_sparkle_vlabel` resource being created (the FE0-S05 phantom stays resolved).

**AC11 — Gate (k): HA state and both replication jobs present.**
- **When** the operator runs `ha-manager status | grep 'ct:167'` and inspects
  `/etc/pve/replication.cfg` for `167-0` and `167-1`,
- **Then** `ha-manager status` shows `ct:167` on `pve3` in the state the FE1-S03 operator decision
  recorded (`started` or `stopped`), and **both** `167-0` and `167-1` are present in
  `replication.cfg` — the ct:151 lesson, re-verified.

## Implementation Notes

Every command in this story runs **from a tailnet client not on the LAN** — this is the test
execution model itself, not an incidental detail; running any gate from the LAN invalidates that
gate's result. Cite `wiki/architecture/tailscale-policy.md:20-31` and
`wiki/architecture/remote-access-topology.md` for the ingress posture (never "ADR-010" — HARD RULE 1).
Gate (g)'s non-gating status is ADR-003; gates (h) and (k) are R4 and R6 respectively, both still
open operator decisions this story measures rather than resolves.

```bash
# Run all eleven gates from a tailnet client, e.g.:
ssh <tailnet-client> 'curl -vI https://forge.bi-services.be 2>&1 | grep -E "SSL|subject"'     # (a)
coder ssh ct167-first-workspace -- 'ls ~/workspace/repos/github/'                              # (b)
coder ssh ct167-first-workspace -- 'test -d ~/workspace/repos/github/company-overlay; echo $?'  # (b)
coder ssh ct167-first-workspace -- 'cat ~/.forge-toolchain'                                     # (c)
coder ssh ct167-first-workspace -- 'ls ~/.claude/skills | wc -l'                                # (d)
coder ssh ct167-first-workspace -- 'claude -p "say hello"'                                      # (e)
coder ssh ct167-first-workspace -- 'stat -c%s ~/.config/forge/openmemory.env ~/.config/forge/langfuse.env' # (f)
coder ssh ct167-first-workspace -- 'sudo -n true; echo $?'                                      # (f)
coder ssh ct167-first-workspace -- 'docker run --rm hello-world'                                # (g), non-gating
ssh pve3 'free -g'                                                                              # (h)
ssh pve3 'terraform -chdir=.../envs/homelab plan -target=module.ct_forge_01'                    # (j)
ssh pve3 'ha-manager status | grep ct:167; grep -A2 "^167-" /etc/pve/replication.cfg'           # (k)
```

## Test Plan

**Pre-state:** FE4-S01 complete; a running workspace exists; the operator has a tailnet client that
is genuinely off the LAN (verified via `ip route` / a non-LAN subnet check before starting).

**Action sequence:**
1. Run AC1–AC11's commands in gate order (a) through (k), from the tailnet client.
2. Record every result — pass, fail, or partial — in a results table appended to this story.
3. For gate (g), record the result regardless of pass/fail; do not omit or soften a failure.
4. For gates (h) and (k), record the raw command output, not just a pass/fail label, since FE4-S04
   needs the underlying numbers.

**Post-state checks:**
- All eleven gates have a recorded result in this story.
- Gate (g)'s result is present even if it failed.
- Gates (h) and (k) carry raw output, not just pass/fail.

**Rollback:** None required — this story is observation-only and changes no system state (the
`terraform plan` in AC10 is read-only by construction).

## Dependencies

- **Blocked by:** FE4-S01 (a running workspace must exist).
- **Blocks:** FE4-S03 (PBS backup is more representative once acceptance traffic has run), FE4-S04
  (the verdict story consumes this story's results table directly).

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| R4 — gate (h) shows swap-thrashing at default sizing | High | Medium | Recorded verbatim per AC8; FE4-S04 decides whether this forces a caveat or a DOES-NOT-PORT call |
| ~~R5 — nested-nested Docker on ZFS untested; gate (g) fails~~ **CLOSED 2026-09-09 — DISPROVEN by FE1-S05.** Double-nested Docker ran on CT 167 and the inner daemon's overlayfs came up **directly on the ZFS dataset** (no `vfs` fallback, no loopback image). Gate (g) is expected to pass. | ~~Medium~~ **n/a** | ~~Low (ADR-003 makes it non-gating)~~ **n/a** | AC7 still records the result regardless — a *measured* pass at FE4-S02 is what the acceptance run is for; FE1-S05 measured the substrate, not this workspace. Gate (g) stays non-gating per ADR-003. |
| R6 — HA `started` vs `stopped` ambiguity makes gate (k) hard to judge | Medium | Low | AC11 checks against whatever the FE1-S03 operator decision actually recorded, not an assumed default |
| Running a gate from the LAN by mistake, invalidating the result | Low | High — silently wrong evidence | Implementation Notes require a pre-check that the client is genuinely off-LAN before any gate runs |

## Definition of Done

- [ ] AC1–AC11 all executed and recorded with raw command output, including any failures.
- [ ] Gate (g)'s result recorded regardless of pass/fail (ADR-003).
- [ ] Gates (h) and (k) carry raw numbers, not just pass/fail labels.
- [ ] Results table appended to this story for FE4-S04 to consume.
- [ ] Story status updated from `draft` to `done` in this file's frontmatter.

## Deferred checks carried in from FE3 (added 2026-09-09)

Two FE3 verifier findings could not be settled without a live workspace and were explicitly
deferred here rather than waved through. Run both against the first workspace from FE4-S01.

**D1 — multi-line env var survives Coder agent → workspace shell (from FE3-S01).**
`FORGE_CODEX_EXTRA_CONTEXT` is a ~519-character, 10-line string carried through
`coder_agent.main.env`. It renders correctly in `terraform plan` (verified), but whether coderd
propagates embedded newlines intact into the workspace shell was untested. In the PoC it is
deliberately empty, so the PoC itself is not affected — but the Azure deployment (if revived)
depends on it carrying 8 facts. Check: `coder ssh <ws> -- printenv FORGE_CODEX_EXTRA_CONTEXT | wc -l`
against a non-empty test value; if flattened/truncated, deliver that context via a mounted file
instead of an env var.

**D2 — repo deny-list and org clone actually behave (from FE3-S02 AC4).**
FE3 verified `FORGE_SYNC_DENY` / `FORGE_GITHUB_ORG=tomamourette` only by an offline replay of
`forge-sync.sh`'s logic. Check on the live workspace: after first boot, `~/workspace/` contains
`agentic-ai`, `knowledge-base`, `company-overlay` (deny-listed → workspace root) and
`~/workspace/repos/github/forge-platform` (org loop), and nothing else; and `~/workspace/agentic-ai`
is checked out at tag `forge-poc-2026-09-09` (87ec24a) via `forge-agentic-runtime.sh`.
