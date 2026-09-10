---
type: story
epic: FE1
id: FE1-S04
title: "Ansible inventory entry, host_vars project_name, and dev-host-setup.yml run for ct-forge-01"
size: S
priority: MUST
owner: dev
blocking: false
fr_refs: [FR-SUB-006]
nfr_refs: []
adr_refs: []
risk_refs: []
status: done
date: 2026-09-09
---

# FE1-S04: Ansible inventory entry, host_vars project_name, and dev-host-setup.yml run for ct-forge-01

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
>    **any** browser-trusted certificate — the homelab has no inbound `:80`/`:443`, so HTTP-01 is
>    impossible, not merely inconvenient. Wildcard scope is optional; the token is not.
>    **REVERSED 2026-09-09 — a wildcard IS required.** The token sentence still holds and the
>    token needs no re-scoping; only the "wildcard scope is optional" clause is dead. See the
>    amendment at the top of [ADR-005](../adrs/ADR-005-dns-01-wildcard-over-public-ingress.md).

## User Story

As **tomamourette**, I want **`ct-forge-01` added to the Ansible inventory with a `host_vars/ct-forge-01/main.yml` containing `project_name`, then `dev-host-setup.yml` run against it**, so that **the `developer` user, SSH keys, Docker CE, Node 20 LTS, the Claude Code CLI wrapper, ruflo, and pyenv are all provisioned the same way every other project container gets them — without the playbook aborting mid-run for a missing required variable**.

## Background and Context

Evidence **E7** and runbook §6/§Pitfalls-3 identify a specific, previously-observed failure mode: `project_name` is **required** by `dev-host/tasks/main.yml:205` (the BMAD install task). Without a `host_vars/ct-forge-01/main.yml` file defining it, the playbook bails with `'project_name' is undefined` — **after** the `developer` user has already been created, but **before** SSH keys are seeded at `dev-host/tasks/main.yml:511`. That specific ordering matters operationally: a partial failure here leaves a host where `id developer` succeeds but `~developer/.ssh/authorized_keys` does not exist, which looks like an SSH configuration problem rather than what it actually is (a missing inventory variable).

This story is valuable independent of the rest of FE1's IaC work because `dev-host` already installs most of the Forge host toolchain for free — Docker CE, Node 20 LTS, the Claude Code CLI wrapper, ruflo, and pyenv with Python 3.11.11 all arrive here, before `forge-coder-host` (FE2-S01) needs to add anything Forge-specific on top.

## Acceptance Criteria

**AC1 — Inventory entry added.**
- **Given** CT 167 is reachable at `192.168.50.167` (FE1-S02 done),
- **When** the dev appends to `homelab-infra/ansible/inventories/homelab/hosts.ini`'s `[dev_hosts]` group: `ct-forge-01 ansible_host=192.168.50.167 ansible_user=root ansible_ssh_private_key_file=~/.ssh/homelab_ed25519`,
- **Then** `ansible -i homelab-infra/ansible/inventories/homelab/hosts.ini ct-forge-01 -m ping` returns `SUCCESS`.

**AC2 — `host_vars/ct-forge-01/main.yml` created with `project_name`.**
- **Given** AC1's inventory entry,
- **When** the dev creates `homelab-infra/ansible/inventories/homelab/host_vars/ct-forge-01/main.yml` containing `project_name: forge` and `project_repos: []`,
- **Then** the file exists and `ansible-inventory -i homelab-infra/ansible/inventories/homelab/hosts.ini --host ct-forge-01 | grep project_name` shows the value.

**AC3 — SSH key gap check before Ansible (runbook §5).**
- **Given** `var.ssh_keys` in `terraform.tfvars` ships the `homelab-infra` fleet key,
- **When** the dev compares `ssh-keygen -lf ~/.ssh/homelab_ed25519.pub` against the fingerprint already injected into CT 167 at create time,
- **Then** either they match (no action needed) or, if they differ, the operator's workstation key is injected into `/root/.ssh/authorized_keys` on CT 167 before proceeding, per the runbook's step 5 procedure.

**AC4 — `dev-host-setup.yml` completes successfully.**
- **Given** AC1–AC3 have passed,
- **When** the dev runs `ansible-playbook -i homelab-infra/ansible/inventories/homelab/hosts.ini homelab-infra/ansible/dev-host-setup.yml --limit ct-forge-01`,
- **Then** the play recap shows `unreachable=0 failed=0`, matching the runbook's documented expected shape (`ok=50 changed=24 unreachable=0 failed=0 skipped=5 rescued=0 ignored=1`, with the single `ignored=1` being the known Claude Code MCP registration task that fails under non-interactive `become` and is re-run manually per runbook §7).

**AC5 — Toolchain present post-provisioning.**
- **Given** AC4's successful run,
- **When** the dev runs `ssh developer@192.168.50.167 "docker --version && node --version && python3 --version"` (via the fallback SSH path, since Tailscale onboarding is a separate, later step not covered by this story),
- **Then** Docker CE, Node 20 LTS, and Python 3.11.11 (via pyenv) are all present and report version strings.

## Implementation Notes

Reference runbook §5 (SSH key gap), §6 (inventory + host_vars), §7 (dev-host-setup run and its expected recap), and Pitfall §3 (`project_name` requirement, exact failure point at `dev-host/tasks/main.yml:205`, SSH key seeding at `:511`). Reference the toolchain list this playbook installs (`dev-host/tasks/main.yml` full task list) as the source of truth for what AC5 checks.

```ini
# homelab-infra/ansible/inventories/homelab/hosts.ini — append to [dev_hosts]
ct-forge-01 ansible_host=192.168.50.167 ansible_user=root \
  ansible_ssh_private_key_file=~/.ssh/homelab_ed25519
```

```yaml
# homelab-infra/ansible/inventories/homelab/host_vars/ct-forge-01/main.yml
---
project_name: forge

project_repos: []
```

```bash
# AC1 — connectivity check
ansible -i homelab-infra/ansible/inventories/homelab/hosts.ini ct-forge-01 -m ping

# AC3 — SSH key fingerprint check
ssh-keygen -lf ~/.ssh/homelab_ed25519.pub

# AC4 — provisioning run
cd homelab-infra
ansible-playbook -i ansible/inventories/homelab/hosts.ini \
  ansible/dev-host-setup.yml --limit ct-forge-01

# If the ignored MCP registration task needs a manual re-run:
ssh developer@192.168.50.167 "cd ~/workspace/forge && claude mcp add ruflo -- ruflo mcp start"

# AC5 — toolchain verification
ssh developer@192.168.50.167 "docker --version && node --version && python3 --version"
```

## Test Plan

**Pre-state:** CT 167 reachable at `192.168.50.167`; no inventory entry, no `host_vars/ct-forge-01/`, no `developer` user.

**Action sequence:**
1. Add the inventory entry (AC1), confirm `ansible ping`.
2. Create `host_vars/ct-forge-01/main.yml` with `project_name` (AC2).
3. Check SSH key fingerprint parity, inject workstation key if needed (AC3).
4. Run `dev-host-setup.yml --limit ct-forge-01` (AC4).
5. Verify toolchain via SSH (AC5).

**Post-state checks:**
- `ansible-inventory --host ct-forge-01` shows `project_name: forge`.
- Play recap shows `failed=0 unreachable=0`.
- `developer` user exists with populated `~/.ssh/authorized_keys`.
- Docker, Node, and pyenv/Python all report expected versions.

**Rollback:** Remove the inventory line and delete `host_vars/ct-forge-01/`; the playbook's changes to CT 167 itself are not automatically reverted by this (no `dev-host-teardown.yml` exists) — a full rollback of the CT's software state requires destroying and recreating the CT (FE1-S02's rollback), which is acceptable given CT 167 is disposable per NFR-DISP-001.

## Dependencies

- **Blocked by:** FE1-S02 (CT must exist and be reachable), FE0-S01, FE0-S02 (§5.4).
- **Blocks:** FE2-S01 (`forge-coder-host` role assumes `dev-host`'s toolchain is already present), FE3-S06 (image build needs Docker CE present on the host).

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| `host_vars/ct-forge-01/main.yml` forgotten, playbook aborts mid-run leaving `developer` user without SSH keys | Medium (documented as the most common pitfall for new project CTs) | Medium — confusing symptom (password prompt despite user existing), but the runbook documents the fix and the playbook is idempotent | AC2 makes file creation an explicit, separately-verified AC before AC4 runs; runbook Pitfall §3 cited directly |
| SSH key fingerprint mismatch blocks Ansible from reaching the host at all | Medium (has hit 3 prior project CTs per the runbook) | Medium — playbook run fails at the connectivity stage | AC3 makes the fingerprint check and, if needed, key injection an explicit pre-flight step before AC4 |
| The single `ignored=1` MCP registration task is mistaken for a real failure | Low | Low — cosmetic confusion only | AC4 explicitly names this as the expected, known-benign outcome per the runbook, with the manual follow-up command given |

## Definition of Done

- [ ] AC1–AC5 all green and evidenced.
- [ ] `ct-forge-01` present in inventory and `host_vars`, with `project_name: forge`.
- [ ] `dev-host-setup.yml --limit ct-forge-01` completed with `failed=0 unreachable=0`.
- [ ] Docker CE, Node 20 LTS, and pyenv/Python 3.11.11 confirmed present via SSH.
- [ ] Story status updated from `draft` to `done` in this file's frontmatter.
