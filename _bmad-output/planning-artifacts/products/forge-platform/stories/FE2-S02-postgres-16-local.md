---
type: story
epic: FE2
id: FE2-S02
title: "Local Postgres 16 with dedicated role and database, password auth, no extensions"
size: S
priority: MUST
owner: dev
blocking: false
fr_refs: [FR-CTL-002]
nfr_refs: [NFR-SEC-003]
adr_refs: [ADR-006]
risk_refs: []
status: done
date: 2026-09-09
---

# FE2-S02: Local Postgres 16 with dedicated role and database, password auth, no extensions

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

As **tomamourette**, I want **a local Postgres 16 instance on `ct-forge-01` with a dedicated `coder` role and database using password authentication and no extensions installed**, so that **coderd has a database backend that is a straight substitution for the Azure Postgres Flexible Server (Entra auth) it replaces, with nothing pulled in that the PoC does not need**.

## Background and Context

Per evidence item **E5** of the sprint change proposal, the Azure Postgres Flexible Server with Entra-based authentication has a clean local substitution: **local Postgres 16, password auth, no extensions**. The "no extensions" qualifier is deliberate and load-bearing, not an oversight — `pgvector` is an OpenMemory requirement (OpenMemory stores embeddings there), and OpenMemory is explicitly out of PoC scope per ADR-006 (`adrs/ADR-006-hermes-openmemory-langfuse-out-of-poc-scope.md`). Installing `pgvector` here would be scope creep that answers no question this PoC is asking (R8 — "Scope creep from the PoC into productisation... none should be answered inside it").

This story is part of the `forge-coder-host` Ansible role family (alongside FE2-S01, FE2-S03, FE2-S05, FE2-S06), per the proposal's §2.3 Ansible impact row. It can be applied to CT 167 independently of FE2-S01 (coderd itself does not need to be installed first for Postgres to exist), but coderd cannot start successfully until this story's database and credentials exist, since coderd's `CODER_PG_CONNECTION_URL` (wired at FE2-S04) points here.

## Acceptance Criteria

**AC1 — Postgres 16 installed from the Debian repository.**
- **Given** `ct-forge-01` is Debian 13,
- **When** the operator runs the role and then `psql --version` on the host,
- **Then** the reported version is Postgres 16.x, installed via the Debian package (`postgresql-16`), not a third-party APT source unless Debian 13's default repos do not carry 16 (in which case the role documents exactly which repo it adds and pins it).

**AC2 — Dedicated role and database.**
- **Given** Postgres 16 is running,
- **When** the operator runs `sudo -u postgres psql -c "\du"` and `sudo -u postgres psql -c "\l"`,
- **Then** a role named `coder` exists (not `postgres`, not superuser) and a database named `coder` exists, owned by that role.

**AC3 — Password authentication, not peer/trust.**
- **Given** `pg_hba.conf` on the host,
- **When** the operator inspects the entries for the `coder` role,
- **Then** the method is `scram-sha-256` (or `md5` if the Debian 13 default is older) for TCP connections from `127.0.0.1`/`localhost` — never `trust`, and the role's password is set via `ALTER ROLE coder WITH PASSWORD '...'` from an Ansible vault-encrypted variable, never a plaintext task argument.

**AC4 — No extensions installed.**
- **Given** the `coder` database,
- **When** the operator runs `sudo -u postgres psql -d coder -c "\dx"`,
- **Then** the extension list is empty (or contains only Postgres's own always-present `plpgsql`) — explicitly **no** `pgvector`, per ADR-006.

**AC5 — Connection string derivable, not yet wired to coderd.**
- **Given** AC1–AC4 have passed,
- **When** the operator constructs `postgresql://coder:<password>@localhost:5432/coder?sslmode=disable` (loopback-only, TLS not required for a local socket),
- **Then** `psql "<that connection string>"` connects successfully. This story does not write the string into `/etc/coder.d/coder.env` — that is FE2-S04's `CODER_PG_CONNECTION_URL`.

## Implementation Notes

Reference proposal E5 (Azure → self-hosted substitution table), ADR-006 (Hermes/OpenMemory/Langfuse out of scope — the reason for "no extensions"). This can live as a `postgres` task block within `forge-coder-host` or as a small sibling role (`forge-postgres`) — either is acceptable; keep it inside the same role family described in §2.3 rather than inventing a new naming convention.

```yaml
# Illustrative shape
- name: Install Postgres 16
  ansible.builtin.apt:
    name: postgresql-16
    state: present

- name: Create coder role
  community.postgresql.postgresql_user:
    name: coder
    password: "{{ vault_coder_pg_password }}"
    role_attr_flags: NOSUPERUSER,NOCREATEDB,NOCREATEROLE
  become_user: postgres

- name: Create coder database
  community.postgresql.postgresql_db:
    name: coder
    owner: coder
  become_user: postgres
```

`vault_coder_pg_password` must come from an Ansible Vault-encrypted variable file, consistent with how the estate already handles the vault-encrypted Azure DevOps credentials for the CPS-Fabric repos on `ct-sparkle-cps`.

## Test Plan

**Pre-state:** CT 167 exists; no Postgres package installed.

**Action sequence:**
1. Apply the role (AC1–AC3).
2. Verify role/database existence and auth method (AC2, AC3).
3. `\dx` on the `coder` database, confirm empty extension list (AC4).
4. Manually connect with the derived connection string (AC5).
5. Re-run the role; confirm idempotent (no duplicate role/database creation errors).

**Post-state checks:**
- `psql --version` reports 16.x.
- `\du` shows `coder` with no superuser flag.
- `\dx` on `coder` database is extension-free.
- Connection string from AC5 succeeds.

**Rollback:** `apt-get remove --purge postgresql-16`; `rm -rf /var/lib/postgresql/16` if a clean wipe is needed. No effect on Terraform/HA state.

## Dependencies

- **Blocked by:** FE1-S04 (CT 167 provisioned and `dev-host-setup.yml` complete).
- **Blocks:** FE2-S04 (`CODER_PG_CONNECTION_URL` in `coder.env` points here).

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Debian 13's default repos do not carry Postgres 16 at story time | **Certain (verified at implementation, was rated Low)** | Medium — needs the PGDG apt repo added | Realised. `apt-cache policy postgresql-16` on ct-forge-01 returns nothing; trixie/main carries only `postgresql-17` (17.11-0+deb13u1) and a `postgresql` meta-package at 17+278. AC1's escape clause was therefore the mandatory path: the role adds and pins apt.postgresql.org `trixie-pgdg` and installs `postgresql-16` 16.15-1.pgdg13+2 with `state: present`, never `latest`. Documented in `homelab-infra/ansible/roles/forge-coder-host/README.md`. |
| Someone later adds `pgvector` by habit (muscle memory from OpenMemory work elsewhere) | Low | Low for the PoC itself, but reopens ADR-006 scope | AC4 is an explicit, repeatable acceptance check; ADR-006 documents the re-entry condition |
| Password stored in plaintext in a task file by mistake | Low | High — credential leak in git | AC3 requires vault-encrypted variables; code review catches a plaintext password before commit |

## Definition of Done

- [x] AC1–AC5 all green and evidenced.
- [x] Postgres 16 role/database committed as Ansible tasks under `homelab-infra/ansible/`.
- [x] Password stored via Ansible Vault, never plaintext in git.
- [x] `\dx` on the `coder` database confirmed extension-free.
- [x] Story status updated from `draft` to `done` in this file's frontmatter.

## Implementation Evidence (2026-09-09)

Landed as Ansible IaC (no hand-typed state on the host):

- `homelab-infra/ansible/roles/forge-coder-host/` — `defaults/main.yml`,
  `tasks/main.yml`, `tasks/postgres.yml`, `handlers/main.yml`, `README.md`.
- `homelab-infra/ansible/playbooks/forge-coder-host.yml` — loads the vault via
  the `{{ playbook_dir }}` `vars_files` form.
- `homelab-infra/ansible/inventories/homelab/group_vars/vault.yml` — new key
  `vault_coder_pg_password` (32 random alphanumerics), whole-file AES256.

| AC | Result | Evidence |
|---|---|---|
| AC1 | PASS | `psql (PostgreSQL) 16.15 (Debian 16.15-1.pgdg13+2)`; `SHOW server_version` → `16.15 (Debian 16.15-1.pgdg13+2)`; `dpkg-query` → `postgresql-16 16.15-1.pgdg13+2`; one cluster only (`16 main 5432 online`); PGDG repo added **and pinned** (origin priority 100, `postgresql`/`postgresql-17`/`postgresql-client-17`/`postgresql-contrib` at -1, none installed). |
| AC2 | PASS | `coder\|f\|f\|f\|t` and `coder\|coder`. |
| AC3 | PASS | `pg_hba_file_rules`: `host all all 127.0.0.1 scram-sha-256`, `host all all ::1 scram-sha-256`, no `trust` anywhere; `password_encryption` = `scram-sha-256`; password only ever `{{ vault_coder_pg_password }}`; vault file starts `$ANSIBLE_VAULT;1.1;AES256`. |
| AC4 | PASS | `SELECT extname FROM pg_extension` on `coder` → `plpgsql` only. The role re-asserts this on every run and fails if anything else appears. |
| AC5 | PASS | `psql "postgresql://coder:<vault>@localhost:5432/coder?sslmode=disable"` → `AC5=coder\|coder`; `/etc/coder.d/coder.env` does not exist, so no `CODER_PG_CONNECTION_URL` is written here (FE2-S04 owns it). |
| Idempotence (Test Plan step 5) | PASS | Run 1 `ok=18 changed=8 failed=0`; run 2 `ok=17 changed=0 skipped=1 failed=0`. |

Notes for FE2-S04 and the PO:

- AC1's premise "installed via the Debian package (`postgresql-16`)" is not
  achievable on Debian 13; the parenthetical escape clause in AC1 was used and
  the risk table above has been corrected from *Likelihood: Low* to *Certain*.
  If the PO would rather not carry a third-party APT source for the PoC, the
  alternative is re-scoping this story to Postgres 17 from Debian main — that
  changes the Azure-parity claim (Azure ran `postgres_version = "16"`) and
  needs Coder's supported-Postgres matrix checked first.
- AC2 (`NOSUPERUSER` owner) is a hardening relative to the Azure original,
  which connected coderd as the Flexible Server admin
  (`modules/coder/main.tf:147`). Whether coderd's startup migrations are happy
  with a plain database owner is first exercised at **FE2-S04-AC5**.
- `community.postgresql` (4.2.0) is machine state on the controller; there is
  no `requirements.yml` in `homelab-infra/ansible`, so a controller rebuild
  would not reinstall it.
