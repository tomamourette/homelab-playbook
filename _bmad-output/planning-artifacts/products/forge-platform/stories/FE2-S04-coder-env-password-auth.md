---
type: story
epic: FE2
id: FE2-S04
title: "/etc/coder.d/coder.env with OIDC and ADO blocks dropped, password auth enabled"
size: S
priority: MUST
owner: dev
blocking: false
fr_refs: [FR-CTL-004, FR-CTL-007]
nfr_refs: [NFR-SEC-003]
adr_refs: []
risk_refs: []
gate_refs: [b]
status: done
date: 2026-09-09
---

# FE2-S04: /etc/coder.d/coder.env with OIDC and ADO blocks dropped, password auth enabled

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

As **tomamourette**, I want **`/etc/coder.d/coder.env` on `ct-forge-01` written with the Entra OIDC and Azure DevOps external-auth blocks dropped, `CODER_DISABLE_PASSWORD_AUTH=false`, and `CODER_EXTERNAL_AUTH_0_*` populated from the GitHub OAuth App**, so that **coderd starts using its own built-in password authentication instead of a nonexistent Entra tenant, and the one external-auth provider this PoC actually needs is correctly wired**.

## Background and Context

Per evidence item **E5**, Entra OIDC sign-in has a clean local substitution: Coder's built-in password authentication, which the Azure deployment's own `cloud-init.yaml:91` already permits (`CODER_DISABLE_PASSWORD_AUTH=false` is set there too, alongside — not instead of — the OIDC block). The homelab version drops the OIDC block entirely rather than leaving it half-configured against credentials that do not exist: `docs/coder/setup.md:1-33` documents the full Entra app registration (`appId 43f17a5d-a461-4a4f-9634-eac3a533678c`, redirect URI `https://coder.dev.saply.ai/api/v2/users/oidc/callback`) that has no homelab equivalent and should not be half-ported.

The Azure DevOps external-auth block (`cloud-init.yaml:96-103`, `CODER_EXTERNAL_AUTH_1_*`) is dropped for the same reason it is out of scope everywhere else in this PoC: ADO repos are Saply-specific and the PoC's only mandatory external-auth provider is GitHub (E6.1). Dropping the ADO block is not itself an acceptance gate, but leaving stale `CODER_EXTERNAL_AUTH_1_*` variables pointing at Saply's Azure AD tenant would be confusing dead configuration in a file meant to demonstrate a de-Azured control plane.

`CODER_EXTERNAL_AUTH_0_*` is the one block this story must get right: `CODER_EXTERNAL_AUTH_0_ID=github`, `CODER_EXTERNAL_AUTH_0_TYPE=github`, `CODER_EXTERNAL_AUTH_0_CLIENT_ID` and `CODER_EXTERNAL_AUTH_0_CLIENT_SECRET` sourced from the values FE0-S01 recorded (FR-CTL-007). This is the credential the workspace template's `data "coder_external_auth" "github"` (`coder/templates/forge/main.tf:25-27`) depends on absolutely — without it correctly wired here, no downstream story can reach gate (b).

Per §Evidence, the setup.md file also notes a caution worth carrying forward operationally (not a PoC requirement, but a documented gotcha): "this whole External Auth config was drift before this change: it existed only in the live server's `/etc/coder.d/coder.env`, not in this repo" (`docs/coder/setup.md:130-131`). This story avoids repeating that mistake by having `coder.env`'s *generation* (the Ansible task/template that writes it) tracked in `homelab-infra`, even though the file's contents necessarily include secrets and the rendered file itself is never committed.

## Acceptance Criteria

**AC1 — File exists, correct permissions.**
- **Given** the role has run,
- **When** the operator runs `stat -c '%a %U' /etc/coder.d/coder.env`,
- **Then** the mode is `600`, owned by root (or the coderd service account, matching FE2-S01's choice).

**AC2 — OIDC block absent.**
- **Given** `coder.env`,
- **When** the operator runs `grep -c CODER_OIDC /etc/coder.d/coder.env`,
- **Then** the count is `0` — no `CODER_OIDC_ISSUER_URL`, `CODER_OIDC_CLIENT_ID`, `CODER_OIDC_CLIENT_SECRET`, `CODER_OIDC_SCOPES`, or any other `CODER_OIDC_*` key.

**AC3 — Password auth enabled.**
- **Given** `coder.env`,
- **When** the operator runs `grep CODER_DISABLE_PASSWORD_AUTH /etc/coder.d/coder.env`,
- **Then** the line reads `CODER_DISABLE_PASSWORD_AUTH=false`, and after `systemctl restart coder`, the Coder web UI's sign-in page shows a username/password form rather than (or in addition to, if left enabled) an OIDC redirect button.

**AC4 — Exactly one external-auth provider, GitHub, correctly populated.**
- **Given** `coder.env`,
- **When** the operator runs `grep CODER_EXTERNAL_AUTH_0 /etc/coder.d/coder.env` and `grep CODER_EXTERNAL_AUTH_1 /etc/coder.d/coder.env`,
- **Then** the `_0_` block is present with `ID=github`, `TYPE=github`, and non-empty `CLIENT_ID`/`CLIENT_SECRET` matching the values FE0-S01 recorded, and the `_1_` grep returns nothing (no ADO block).

**AC5 — coderd starts and reaches the database.**
- **Given** FE2-S01 (coderd binary) and FE2-S02 (Postgres 16 + `coder` database) are both complete,
- **When** the operator adds `CODER_PG_CONNECTION_URL` to this same file and runs `systemctl restart coder`,
- **Then** `systemctl status coder` shows `active (running)` and `journalctl -u coder -n 50` shows no repeated connection-refused or migration-failure errors.

## Implementation Notes

Reference E5, E6.1, FR-CTL-004, FR-CTL-007, `docs/coder/setup.md:1-33` (what NOT to port), `docs/coder/setup.md:130-131` (the drift lesson — track the *template*, not the rendered secrets file). Generate `coder.env` via an Ansible `template` task from a Jinja2 source that lives in `homelab-infra/ansible/roles/forge-coder-host/templates/coder.env.j2`, with the actual secret values supplied via Ansible Vault variables — never commit the rendered file.

```jinja2
{# roles/forge-coder-host/templates/coder.env.j2 — illustrative shape #}
CODER_ACCESS_URL=https://forge.bi-services.be
CODER_DISABLE_PASSWORD_AUTH=false
CODER_PG_CONNECTION_URL=postgresql://coder:{{ vault_coder_pg_password }}@localhost:5432/coder?sslmode=disable
CODER_EXTERNAL_AUTH_0_ID=github
CODER_EXTERNAL_AUTH_0_TYPE=github
CODER_EXTERNAL_AUTH_0_CLIENT_ID={{ vault_github_oauth_client_id }}
CODER_EXTERNAL_AUTH_0_CLIENT_SECRET={{ vault_github_oauth_client_secret }}
```

```bash
# AC verification
grep -c CODER_OIDC /etc/coder.d/coder.env        # expect 0
grep CODER_DISABLE_PASSWORD_AUTH /etc/coder.d/coder.env
grep CODER_EXTERNAL_AUTH_0 /etc/coder.d/coder.env
grep -c CODER_EXTERNAL_AUTH_1 /etc/coder.d/coder.env   # expect 0
systemctl restart coder && systemctl status coder --no-pager
```

## Test Plan

**Pre-state:** `coderd` binary installed (FE2-S01), Postgres 16 + `coder` database exist (FE2-S02), `/etc/coder.d/coder.env` does not exist or contains only the package default.

**Action sequence:**
1. Populate Ansible Vault with `vault_coder_pg_password`, `vault_github_oauth_client_id`, `vault_github_oauth_client_secret` (from FE0-S01 and FE2-S02).
2. Render `coder.env` via the role's template task (AC1–AC4).
3. Restart `coder.service`; confirm active (AC5).
4. Open the Coder web UI (via `curl -k` at this point since Caddy/TLS is FE2-S05) and confirm the sign-in form shows a password option.

**Post-state checks:**
- `coder.env` mode 600, no OIDC keys, no `_1_` block, `_0_` block matches FE0-S01's recorded values.
- `systemctl status coder` active.
- No connection errors in `journalctl -u coder`.

**Rollback:** `systemctl stop coder`; remove `/etc/coder.d/coder.env`; re-render from a known-good backup if this story's change broke a previously working config. Restarting the unit with the old file restores prior behaviour.

## Dependencies

- **Blocked by:** FE0-S01 (GitHub OAuth App values), FE2-S01 (coderd installed), FE2-S02 (Postgres database).
- **Blocks:** FE2-S05 (Caddy fronts a running coderd), FE4-S01 (first workspace create needs a working control plane and the GitHub external-auth provider).

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| `coder.env` rendered with a stale or mistyped GitHub client secret | Low | High — external-auth silently fails, same symptom as FE0-S01 not existing at all | AC4 explicitly greps the rendered file and compares against the recorded FE0-S01 values before marking done |
| coder.env drifts from its Ansible template via a manual edit on the live host (the exact failure `docs/coder/setup.md:130-131` documents happened on Azure) | Medium over time, low in this initial pass | Medium — reproducibility lost | Track the Jinja2 *template* in git; re-render (don't hand-edit) whenever a value changes; document this explicitly in the role |
| Postgres connection string embedded in `coder.env` leaks via a misconfigured backup or log | Low | High — credential exposure | File stays mode 600 root-owned; NFR-SEC-003 applies; PBS backup (FE4-S03) backs up the whole CT, which is expected and already covered by the existing backup posture |

## Definition of Done

- [ ] AC1–AC5 all green and evidenced.
- [ ] `coder.env.j2` template committed under `homelab-infra/ansible/roles/forge-coder-host/templates/`.
- [ ] Vault-encrypted variables hold all secret values; rendered file never committed.
- [ ] `systemctl status coder` shows `active (running)`.
- [ ] Story status updated from `draft` to `done` in this file's frontmatter.
