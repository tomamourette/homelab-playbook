# E4-S07 — Reusable compose-app Ansible role + context-stack invocation

| | |
|--|--|
| Date          | 2026-04-27 |
| Story         | E4-S07 (Sprint 4, Context Stack product) |
| Branches      | `feature/context-stack-e3-graphiti` (both `homelab-infra` and `homelab-playbook`) |
| Status        | READY for E4-S08 |

## Summary

Authored a generic, parametric Ansible role (`compose-app`) for compose-stack deployments and a context-stack invocation playbook (`deploy-context-stack.yml`) that uses it for graphiti + gitnexus. Validated locally via `ansible-lint`, `ansible-playbook --syntax-check`, `ansible-playbook --check`, and a self-contained guard regression test. No deploy executed (E4-S08 scope).

Per operator instruction (2026-04-27): the role is deliberately reusable — naming and parameter design treat the context-stack as the first caller, not the only one. Future stacks (e.g. authelia, productivity-obsidian) can reuse the role unchanged.

## Role design

**Path:** `homelab-infra/ansible/roles/compose-app/`

**Parametric surface (defaults):**

| Var | Default | Notes |
|-----|---------|-------|
| `compose_app_stack_name`  | (required) | matches `homelab-apps/stacks/<name>` |
| `compose_app_source_dir`  | (required) | absolute controller path |
| `compose_app_target_dir`            | `/srv/<name>` | host path |
| `compose_app_data_dir`              | `<target>/data` | snapshotted on destructive down |
| `compose_app_owner` / `_group` / `_dir_mode` | root / root / 0750 | target dir ownership |
| `compose_app_env_template`          | `""` | Jinja template path on controller |
| `compose_app_env_vars`              | `{}` | extra non-secret vars in template scope |
| `compose_app_post_deploy_check`     | `""` | host-side script |
| `compose_app_health_retries` / `_delay` | 12 / 5 | health check backoff |
| `compose_app_pull_images`           | `true` | `docker compose pull` before up |
| `compose_app_recreate`              | `false` | force-recreate on up |
| `compose_app_force_data_loss`       | `false` | **safety**: must be true to permit `down -v` |
| `compose_app_backup_before_destructive` | `true` | cp -a before destructive down |

**Tasks layout:**

- `tasks/main.yml` — deploy path: validate → mkdir → rsync source → render env → pull → up -d → health.
- `tasks/down.yml` — non-destructive `down` by default; destructive `down -v` ONLY when both `down_destructive=true` AND `compose_app_force_data_loss=true`. Takes `cp -a` snapshot first when `compose_app_backup_before_destructive=true` (default).
- `tasks/restore.yml` — restore data dir from latest `cp -a` snapshot.
- `meta/argument_specs.yml` — typed surface (Ansible 2.11+).
- `tests/test-down-guard.yml` — 3-scenario guard regression test.
- `README.md` — invocation patterns + safety semantics.

**Context-stack invocation:** `homelab-infra/ansible/playbooks/deploy-context-stack.yml` includes the role twice (gitnexus, graphiti) against `ct-dev-homelab` (already in `[dev_hosts]` at 192.168.50.156). Env-template at `playbooks/templates/graphiti.env.j2` pulls `vault_litellm_master_key` from the host's vault.

**Inventory:** ct-dev-homelab is already defined in `homelab-infra/ansible/inventories/homelab/hosts.ini` (line 22) under `[dev_hosts]`. No inventory changes required for E4-S07. Per-host vars + vault file already exist at `inventories/homelab/host_vars/ct-dev-homelab/`. **Caveat for E4-S08:** the host_vars/vault on ct-dev-homelab does not yet carry `vault_litellm_master_key` (currently only on ct-ai-01). That secret needs to be re-exported into ct-dev-homelab's vault as part of E4-S08 prep, OR the playbook needs to lift the vault_files list to also load ct-ai-01's vault. Tracked as an E4-S08 gap.

## Validation outcomes

### ansible-lint

```bash
LC_ALL=C.UTF-8 LANG=C.UTF-8 ansible-lint roles/compose-app/ playbooks/deploy-context-stack.yml
```

Result: **1 finding** — `role-name: Role name compose-app does not match ^[a-z][a-z0-9_]*$ pattern`. This is the same finding that already trips on every existing kebab-case role in the estate (litellm-gateway, gemma-hybrid-proxy, ai-dev-hermes, pve-host-pve3-storage, etc.); the project house-style is kebab-case role names, not the strict snake_case the lint rule enforces. Accepted as project-wide convention violation. All other rules clean across 11 files.

### syntax-check

```bash
ansible-playbook -i inventories/homelab/hosts.ini playbooks/deploy-context-stack.yml --syntax-check
# → playbook: playbooks/deploy-context-stack.yml

ansible-playbook -i 'localhost,' roles/compose-app/tests/test-down-guard.yml --syntax-check
# → playbook: roles/compose-app/tests/test-down-guard.yml
```

Both pass.

### dry-run (--check) against ct-dev-homelab

```bash
ansible-playbook -i inventories/homelab/hosts.ini --limit ct-dev-homelab \
    playbooks/deploy-context-stack.yml --check
```

Result: `ok=20 changed=7 unreachable=0 failed=0 skipped=7`. The play reaches ct-dev-homelab (192.168.50.156), validates parameters, plans the directory creates and the rsync of both compose stacks, renders the graphiti env template, and correctly skips the `docker compose pull / up -d` tasks under `not ansible_check_mode` guards (since dry-run can't sensibly model a docker pull). E4-S08 will remove the `--check` flag and observe the actual deploy.

### down-guard regression test

```bash
ansible-playbook -i 'localhost,' --connection=local \
    roles/compose-app/tests/test-down-guard.yml --check
```

Result: `ok=13 changed=0 failed=0 skipped=7 rescued=1`. The single `rescued=1` is the load-bearing signal — scenario 1 (destructive=true + force=false) is wrapped in a `block:/rescue:` and the rescue caught the assert-failure. If the guard were broken the rescue would never fire and the play would fail with an explicit "GUARD IS BROKEN" message. Three scenarios verified:

| Scenario | down_destructive | force_data_loss | Expected | Outcome |
|----------|------------------|-----------------|----------|---------|
| 1 | `true`  | `false` | guard MUST trip | guard fired, rescue caught (PASS) |
| 2 | `true`  | `true`  | guard MUST allow | success_msg emitted, command path skipped under check_mode (PASS) |
| 3 | `false` | `false` | non-destructive branch | plain `down` task selected (PASS) |

## ADR-007 sub-amendment

Added "Amendment 2026-04-27b (deployment-side `down -v` guard)" to `_bmad-output/planning-artifacts/products/context-stack/adrs/ADR-007-graphiti-backup-strategy.md` directly under the title heading, above the existing 2026-04-27 per-group amendment. Records:

- Why the guard lives in the deployment layer (cron AOF/RDB don't help if Ansible nukes the volume that holds them).
- The two-flag interlock (`down_destructive` + `compose_app_force_data_loss`).
- The cp -a snapshot belt-and-braces.
- Where the regression test lives.
- Reversal trigger.

## Anything unexpected

1. **Branch reading at session start:** the session-start git status surfaced `decommission/context-stack-phase-1` as the active branch in homelab-playbook, but commits landed on `feature/context-stack-e3-graphiti` (matching the brief). Likely a stale snapshot in the session prelude — verified post-commit, all three repos are aligned on `feature/context-stack-e3-graphiti`. No action required.
2. **Vault gap for ct-dev-homelab:** the existing host_vars/vault for ct-dev-homelab doesn't carry `vault_litellm_master_key` (it's currently only on ct-ai-01's vault). E4-S08 needs to re-export that secret into ct-dev-homelab's vault, or the playbook needs to load ct-ai-01's vault explicitly. Recorded in the E4-S08 gap section below.
3. **ansible-lint locale issue:** invocation requires `LC_ALL=C.UTF-8 LANG=C.UTF-8` shell prefix (system locale is the default minimal one). Documented in evidence + suggested as a one-line shell wrapper for future authoring sessions if the friction surfaces again.
4. **Compose stack header comments still say "workstation only":** the existing `homelab-apps/stacks/{graphiti,gitnexus}/docker-compose.yml` header comments describe these stacks as workstation-only. They function fine on any Docker host (it's a comment, not behaviour), but for consistency with the new deployment story the comments should be tweaked when E4-S08 lands the actual deploy. Out of scope for E4-S07 (no homelab-apps changes per brief).

## Files added / modified

**homelab-infra (new):**
- `ansible/roles/compose-app/defaults/main.yml`
- `ansible/roles/compose-app/tasks/main.yml`
- `ansible/roles/compose-app/tasks/down.yml`
- `ansible/roles/compose-app/tasks/restore.yml`
- `ansible/roles/compose-app/handlers/main.yml`
- `ansible/roles/compose-app/meta/main.yml`
- `ansible/roles/compose-app/meta/argument_specs.yml`
- `ansible/roles/compose-app/tests/test-down-guard.yml`
- `ansible/roles/compose-app/README.md`
- `ansible/playbooks/deploy-context-stack.yml`
- `ansible/playbooks/templates/graphiti.env.j2`

**homelab-playbook (modified + new):**
- `_bmad-output/planning-artifacts/products/context-stack/adrs/ADR-007-graphiti-backup-strategy.md` — sub-amendment 2026-04-27b
- `docs/context-stack/sprint-4/e4-s07-evidence.md` — this doc

## E4-S08 readiness

**READY** for E4-S08 — deploy to ct-dev-homelab + run 5 smoke tests + rollback drill — when operator confirms ct-dev-homelab is ready and the vault gap below is closed.

**E4-S08 prep checklist:**

1. Re-export `vault_litellm_master_key` into `inventories/homelab/host_vars/ct-dev-homelab/vault.yml` (or load ct-ai-01's vault explicitly in `deploy-context-stack.yml`).
2. Verify ct-dev-homelab has Docker installed (`docker compose version`) — the role assumes docker-host (or equivalent) is already applied.
3. Decide whether ct-dev-homelab inherits the `homelab-apps` checkout from the operator-side workstation, or whether it needs its own clone (the role doesn't clone, so the controller side must have it).
4. Plan rollback drill: take a known-good cp -a snapshot manually before the first destructive test; exercise `tasks_from: down.yml` with both flags then `tasks_from: restore.yml`.
