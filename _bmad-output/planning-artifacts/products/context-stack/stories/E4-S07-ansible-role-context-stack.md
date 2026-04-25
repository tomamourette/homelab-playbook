---
type: story
epic: E4
id: E4-S07
title: "Author ai-dev-context-stack Ansible role for ct-dev-homelab deploy"
size: 1.5d
priority: MUST
fr_refs: [FR-DEP-001, FR-DEP-008, FR-DEP-005]
adr_refs: [ADR-006, ADR-008, ADR-011]
status: draft
date: 2026-04-25
---

# E4-S07: Author ai-dev-context-stack Ansible role for ct-dev-homelab deploy

## User Story

As **tomamourette** (homelab operator), I want **a single idempotent Ansible role `ai-dev-context-stack` (under `homelab-playbook/roles/`, plus a `deploy-ai-dev-context-stack.yml` playbook in `homelab-infra/ansible/playbooks/` matching the existing `deploy-ai-dev-container.yml` composition pattern) that wraps E2's GitNexus install, E3's Graphiti compose stack, E4-S04's cost-cap.sh + cron + admin key, E4-S05's Phase-4 .env template (or its deferral), and E4-S03's wiki-query skill into one deploy unit targeted at `ct-dev-homelab` (192.168.50.150)**, so that **E4-S08 can run a single `ansible-playbook` invocation, prove end-to-end deploy + rollback, and the role becomes the canonical onboarding artifact for any future Context Stack target — with zero secrets in the repo (FR-DEP-008 / ADR-006 vault pattern)**.

## Background and Context

E2 and E3 ship per-tier installs (workstation script for GitNexus; Compose unit + cron for Graphiti on `ct-ai-01`). FR-DEP-001 requires the Phase-1 decommission to be Ansible-driven (already done in E1-S03/S05). FR-DEP-005 names Phase-3 wiki rollout as part of the deploy. FR-DEP-008 mandates no secrets in repo.

This story consolidates all of that into ONE Ansible role per the role-composition pattern in `homelab-infra/ansible/playbooks/deploy-ai-dev-container.yml` (the existing pattern used by `ai-dev-mempalace` / `ai-dev-omega-memory` / `ai-dev-tmux` / `ai-dev-hermes`). The new role replaces the deleted `ai-dev-mempalace` and `ai-dev-omega-memory` slots — but is structurally different (it composes work across both workstation and ct-dev-homelab, not just one host).

Per `feedback_test_container.md`, the **first** deploy target is `ct-dev-homelab` (192.168.50.150) — the standing per-story validation container. E4-S08 actually runs the deploy; this story authors the role.

## Acceptance Criteria

### AC1: Role directory structure conforms to existing homelab-playbook conventions

- **Given** the homelab-playbook repo has roles under `homelab-playbook/roles/` (NOTE: actual repo path; the existing `ai-dev-*` roles live in `homelab-infra/ansible/roles/` per the project's two-repo split — this story creates the role at the correct location matching the existing pattern)
- **When** I run `tree -L 2 homelab-infra/ansible/roles/ai-dev-context-stack/`
- **Then** output shows: `defaults/main.yml`, `tasks/main.yml`, `tasks/<sub-task-files>.yml`, `templates/*.j2`, `handlers/main.yml`, `vars/main.yml`, `meta/main.yml`, `README.md` (operator-facing)

### AC2: `defaults/main.yml` exposes overridable knobs

- **Given** AC1 holds
- **When** I read `defaults/main.yml`
- **Then** it defines (with sane defaults): `context_stack_target: ct-dev-homelab`, `context_stack_target_ip: 192.168.50.150`, `gitnexus_version: '1.6.3'`, `graphiti_mcp_image: 'zepai/graphiti-mcp:v1.0.2'`, `falkordb_image: 'falkordb/falkordb:<pinned-sha>'`, `graphiti_compose_dir: /srv/graphiti`, `graphiti_data_dir: /srv/graphiti/data`, `graphiti_semaphore_limit: 5`, `daily_cap_usd: '1.00'`, `ntfy_url: 'http://ct101.tail-scale.ts.net/graphiti-alerts'`, `wiki_dir: '{{ playbook_dir }}/../../homelab-playbook/wiki'`, `enable_phase_4_bridge: false` (default OFF; flips ON if E4-S06 gate PASSED)

### AC3: `tasks/main.yml` is decomposed into named sub-task files

- **Given** AC1 holds
- **When** I read `tasks/main.yml`
- **Then** it includes (in order): `install-prereqs.yml` (Docker, docker-compose, curl, jq, bc, yq), `install-graphiti.yml` (compose unit + .env from vault), `install-cost-cap.yml` (cost-cap.sh + cron + admin key from vault), `install-graphiti-backup.yml` (ADR-007 cron entries — references E3-S07 outputs), `install-litellm-bridge.yml` (Phase-4 .env template; only runs if `enable_phase_4_bridge: true`), `install-gitnexus-workstation.yml` (delegate to localhost — workstation install, optional based on `context_stack_install_gitnexus`), `install-wiki-skill.yml` (copies `~/.claude/skills/wiki-query/` to target), `register-mcp.yml` (runs `claude mcp add --transport http graphiti http://...:8000/mcp/` on the target), `verify.yml` (post-install smoke; described in AC10)

### AC4: All secrets sourced from vault, never plaintext in role

- **Given** AC1 holds
- **When** I run `git grep -nE 'sk-(real|admin|proj|live)' homelab-infra/ansible/roles/ai-dev-context-stack/`
- **Then** zero matches; AND every Jinja template that interpolates a secret references a `lookup('community.general.passwordstore', ...)` or an `ansible-vault`-encrypted variable in `vars/secrets.yml` (which is ansible-vault encrypted — verified via `ansible-vault view homelab-infra/ansible/roles/ai-dev-context-stack/vars/secrets.yml` succeeding with the operator's vault password); AND `secrets.yml` has the `$ANSIBLE_VAULT;1.1;AES256` header

### AC5: `templates/graphiti.env.j2` produces correct .env for both phase modes

- **Given** AC4 holds
- **When** the role runs with `enable_phase_4_bridge: false`, the rendered `/srv/graphiti/.env` matches the Phase 1-3 layout (with `MODEL_NAME=gpt-4o-mini`, no `OPENAI_BASE_URL`)
- **And when** the role runs with `enable_phase_4_bridge: true`, the rendered `.env` matches the Phase 4 layout (with `OPENAI_BASE_URL=http://hybrid-gemma-litellm.tail-scale.ts.net:4000/v1`, `MODEL_NAME=gemma-reasoner`, `OPENAI_API_KEY=sk-litellm-anything` placeholder, embeddings still on OpenAI)
- **In both cases** mode is 600, owner is the deploy user, and a `.env.phase-3-backup` is preserved when flipping to Phase 4

### AC6: `templates/cost-cap.sh.j2` (or non-templated copy) installs E4-S04 verbatim

- **Given** AC1 holds
- **When** the role runs `install-cost-cap.yml`
- **Then** `/srv/graphiti/scripts/cost-cap.sh` on the target matches E4-S04's reference script byte-for-byte (or with templated `DAILY_CAP`/`NTFY_URL`/`COMPOSE_DIR` defaults rendered); mode 755; cron entry `*/30 * * * *` registered via the Ansible `cron` module; `OPENAI_ADMIN_KEY` env line is appended to `/srv/graphiti/.env` from the vaulted variable

### AC7: `tasks/install-wiki-skill.yml` deploys the wiki-query skill

- **Given** the source-of-truth lives at `homelab-playbook/skills/wiki-query/SKILL.md` (E4-S03 backup copy)
- **When** the role runs against `ct-dev-homelab`
- **Then** `~/.claude/skills/wiki-query/SKILL.md` exists on the target with mode 644; the wiki tree is rsync-mirrored from `homelab-playbook/wiki/` to `~/workspace/homelab/homelab-playbook/wiki/` on the target (preserving directory structure); the target user has Claude Code installed (skip with friendly message if not)

### AC8: `tasks/register-mcp.yml` registers Graphiti MCP on the target

- **Given** AC1-AC7 hold
- **When** the role runs against `ct-dev-homelab` and `claude` CLI is installed
- **Then** `claude mcp list` on the target shows `graphiti` registered with HTTP transport URL `http://ct-ai-01.tail-scale.ts.net:8000/mcp/`; the registration is idempotent (re-run doesn't create duplicates); a check-then-add pattern using `claude mcp list | grep -q graphiti` is used

### AC9: `tasks/verify.yml` exits 0 on a healthy deploy

- **Given** the full role has run on `ct-dev-homelab`
- **When** `tasks/verify.yml` is invoked at end of the role (or via `ansible-playbook deploy-ai-dev-context-stack.yml --tags verify`)
- **Then** it asserts: (a) `docker compose -f /srv/graphiti/docker-compose.yml ps` shows graphiti-mcp + graphiti-falkordb both Up; (b) `curl -fsS -m 5 http://127.0.0.1:8000/mcp/health` (or equivalent endpoint) returns 200; (c) `redis-cli -h 127.0.0.1 -p 6379 PING` returns PONG inside the falkordb container; (d) `crontab -l | grep -c cost-cap.sh` is 1; (e) `test -f /srv/graphiti/.env` mode 600; (f) `test -d ~/workspace/homelab/homelab-playbook/wiki` exists with index.md inside; (g) `test -f ~/.claude/skills/wiki-query/SKILL.md`. ANY failed assertion → role exits non-zero with a descriptive message

### AC10: Playbook `deploy-ai-dev-context-stack.yml` follows the deploy-ai-dev-container.yml pattern

- **Given** the role exists
- **When** I look at `homelab-infra/ansible/playbooks/deploy-ai-dev-context-stack.yml`
- **Then** the playbook: (a) targets the `ct_dev_homelab` host group from existing inventory; (b) imports `roles/ai-dev-context-stack`; (c) optionally also delegates the workstation-side install to `localhost` for GitNexus + skill; (d) follows the same role-composition + `gather_facts: yes` + `become: yes` pattern as `deploy-ai-dev-container.yml`; (e) is annotated with comments mapping each role-task to the originating story (S03/S04/S05 etc.) for trace-back

### AC11: Idempotency — second run is a no-op

- **Given** AC9 reports 0 changes after a fresh deploy
- **When** I run `ansible-playbook deploy-ai-dev-context-stack.yml` a second time without modifying any input
- **Then** `--check --diff` reports `changed=0` and the run wall-time is < 60 s; if any task reports `changed=1` on a no-input second run, that task has a non-idempotent bug to fix before this story closes

### AC12: Role README documents the deploy + rollback procedure

- **Given** AC1 holds
- **When** I read `homelab-infra/ansible/roles/ai-dev-context-stack/README.md`
- **Then** it includes: (a) one-paragraph role purpose; (b) the prerequisite checklist (target reachable; Tailscale up; vault password available); (c) the deploy command (`ansible-playbook -i inventory deploy-ai-dev-context-stack.yml --ask-vault-pass`); (d) the rollback command (the inverse — see E4-S08 for the actual exercise); (e) a table of `defaults/main.yml` knobs and their effects; (f) FR / ADR cross-references

## Implementation Notes

### Repo location confirmation

The existing `ai-dev-*` roles live at `/home/developer/workspace/homelab/homelab-infra/ansible/roles/`. The companion playbook lives at `homelab-infra/ansible/playbooks/deploy-ai-dev-container.yml`. This story creates:

- `homelab-infra/ansible/roles/ai-dev-context-stack/` — new role
- `homelab-infra/ansible/playbooks/deploy-ai-dev-context-stack.yml` — new playbook
- (E2-S01's GitNexus workstation install can ALSO live as `homelab-infra/ansible/roles/dev-workstation-gitnexus/` if the operator prefers role-decomposition; this story can either compose both or just call out to a delegate-to-localhost task. Recommended: keep workstation install as a dedicated role to maintain single-responsibility, and reference it from the context-stack role's `meta/main.yml` `dependencies:` list — but only if the existing pattern uses dependencies; otherwise just delegate.)

### Role structure (sketch)

```
homelab-infra/ansible/roles/ai-dev-context-stack/
├── defaults/main.yml            # AC2 knobs
├── tasks/
│   ├── main.yml                 # AC3 includes
│   ├── install-prereqs.yml
│   ├── install-graphiti.yml
│   ├── install-cost-cap.yml
│   ├── install-graphiti-backup.yml
│   ├── install-litellm-bridge.yml
│   ├── install-gitnexus-workstation.yml
│   ├── install-wiki-skill.yml
│   ├── register-mcp.yml
│   └── verify.yml
├── templates/
│   ├── graphiti.env.j2          # AC5 — phase-aware .env
│   ├── docker-compose.yml.j2    # Compose unit (pinned tags from defaults)
│   ├── cost-cap.sh.j2           # AC6
│   ├── graphiti-backup.sh.j2    # E3-S07 reference
│   └── cypher-export.sh.j2
├── handlers/
│   └── main.yml                 # restart graphiti-mcp; restart cron
├── vars/
│   ├── main.yml                 # non-secret static vars
│   └── secrets.yml              # ansible-vault encrypted (AC4)
├── meta/main.yml                # role metadata, dependencies if any
└── README.md                    # AC12
```

### `defaults/main.yml` template

```yaml
---
# ai-dev-context-stack — Phase 4 deploy role for Context Stack
# FR-DEP-001, FR-DEP-005, FR-DEP-008

context_stack_target: ct-dev-homelab
context_stack_target_ip: 192.168.50.150

# Tier 2 — GitNexus (workstation; delegate-to-localhost)
gitnexus_version: '1.6.3'
context_stack_install_gitnexus: true   # set false to skip workstation install

# Tier 3 — Graphiti
graphiti_compose_dir: /srv/graphiti
graphiti_data_dir: /srv/graphiti/data
graphiti_mcp_image: 'zepai/graphiti-mcp:v1.0.2'
falkordb_image: 'falkordb/falkordb:edge'   # pin actual SHA at deploy time
graphiti_semaphore_limit: 5
graphiti_telemetry_enabled: false
graphiti_default_group_id: 'tom-personal'

# Cost cap (E4-S04)
daily_cap_usd: '1.00'
ntfy_url: 'http://ct101.tail-scale.ts.net/graphiti-alerts'

# Phase 4 LiteLLM bridge (E4-S05/S06)
enable_phase_4_bridge: false
litellm_base_url: 'http://hybrid-gemma-litellm.tail-scale.ts.net:4000/v1'
litellm_model_name: 'gemma-reasoner'

# Tier 1 — Wiki
wiki_source_dir: '{{ playbook_dir }}/../../homelab-playbook/wiki'
wiki_target_dir: '~/workspace/homelab/homelab-playbook/wiki'
wiki_skill_source: '{{ playbook_dir }}/../../homelab-playbook/skills/wiki-query'
wiki_skill_target: '~/.claude/skills/wiki-query'
```

### `vars/secrets.yml` template (ansible-vault encrypted)

Plaintext (before encryption):
```yaml
---
openai_api_key: 'sk-real-...'
openai_admin_key: 'sk-admin-...'   # E4-S04 cost-cap.sh
falkordb_password: '<generated>'
```

Encrypt with `ansible-vault encrypt vars/secrets.yml`. The vault password lives in the operator's password store, not in repo.

### `templates/graphiti.env.j2`

```jinja2
# Rendered by ai-dev-context-stack role (NEVER commit this file).
OPENAI_API_KEY={{ openai_api_key if not enable_phase_4_bridge else 'sk-litellm-anything' }}
{% if enable_phase_4_bridge %}
OPENAI_BASE_URL={{ litellm_base_url }}
EMBEDDER_OPENAI_API_KEY={{ openai_api_key }}
EMBEDDER_OPENAI_BASE_URL=https://api.openai.com/v1
MODEL_NAME={{ litellm_model_name }}
SMALL_MODEL_NAME={{ litellm_model_name }}
{% else %}
MODEL_NAME=gpt-4o-mini
{% endif %}
EMBEDDER_MODEL_NAME=text-embedding-3-small
SEMAPHORE_LIMIT={{ graphiti_semaphore_limit }}
GRAPHITI_TELEMETRY_ENABLED={{ graphiti_telemetry_enabled | lower }}
OPENAI_ADMIN_KEY={{ openai_admin_key }}
DEFAULT_GROUP_ID={{ graphiti_default_group_id }}
```

### Composing with E2-S01 / E3-S01 outputs

The new role does NOT redefine the GitNexus install nor the Graphiti compose unit from scratch. It either (a) imports the prior roles via `meta/main.yml` dependencies (if E2/E3 produced standalone roles), or (b) inlines the task content if E2/E3 didn't produce a separate role. The decision depends on what E2-S01 and E3-S01 actually committed; this story makes a final call at implementation time but biases toward **role composition** (less duplication, easier maintenance) — list both sub-roles as `dependencies` in `meta/main.yml`:

```yaml
# meta/main.yml
---
dependencies:
  - role: ai-dev-graphiti          # owns Graphiti Compose unit; E3-S01 created
  - role: dev-workstation-gitnexus # owns GitNexus install; E2-S01 created (delegate to localhost)
```

If those roles don't exist as standalones at story start, this story creates lightweight wrappers in their established locations (`homelab-infra/ansible/roles/ai-dev-graphiti/`, etc.) that source the install scripts E2/E3 committed.

### Inventory entry

The `ct_dev_homelab` host group is expected to exist in inventory. If absent, this story adds it to `homelab-infra/ansible/inventory/hosts.yml`:
```yaml
ct_dev_homelab:
  hosts:
    ct-dev-homelab.tail-scale.ts.net:
      ansible_user: developer
      context_stack_target_ip: 192.168.50.150
```

### What this story does NOT do

- Does NOT actually deploy to `ct-dev-homelab` — that's E4-S08.
- Does NOT exercise rollback — E4-S08 owns the rollback drill.
- Does NOT run the FR-LLM-005 validation (E4-S06 done before; this role just templates the post-validated `.env`).
- Does NOT ship to any production-class container — `ct-dev-homelab` only.

## Test Plan

**Pre-flight:**
```bash
ls homelab-infra/ansible/roles/ | grep -E 'ai-dev-(graphiti|hermes|tmux)'   # confirm pattern
cat homelab-infra/ansible/playbooks/deploy-ai-dev-container.yml | head -30  # study role-composition
ansible --version    # ≥ 2.14 expected
ansible-vault --help # available
```

**Author the role and playbook (Edit/Write — many files):** see Implementation Notes for full structure.

**Lint:**
```bash
ansible-lint homelab-infra/ansible/roles/ai-dev-context-stack/   # 0 errors
yamllint homelab-infra/ansible/roles/ai-dev-context-stack/       # 0 errors
ansible-playbook --syntax-check homelab-infra/ansible/playbooks/deploy-ai-dev-context-stack.yml
```

**Dry-run (does NOT actually deploy):**
```bash
ansible-playbook -i homelab-infra/ansible/inventory/hosts.yml \
  homelab-infra/ansible/playbooks/deploy-ai-dev-context-stack.yml \
  --check --diff --ask-vault-pass --limit ct-dev-homelab.tail-scale.ts.net
```

**AC verification (post-author, dry-run only — actual deploy is E4-S08):**
```bash
# AC1
tree -L 2 homelab-infra/ansible/roles/ai-dev-context-stack/
# AC2
yq '.context_stack_target, .gitnexus_version, .graphiti_mcp_image, .daily_cap_usd, .enable_phase_4_bridge' \
  homelab-infra/ansible/roles/ai-dev-context-stack/defaults/main.yml
# AC3
yq '.[].include_tasks // .[].import_tasks' homelab-infra/ansible/roles/ai-dev-context-stack/tasks/main.yml
# AC4
git grep -nE 'sk-(real|admin|proj|live)' homelab-infra/ansible/roles/ai-dev-context-stack/   # 0 matches
ansible-vault view homelab-infra/ansible/roles/ai-dev-context-stack/vars/secrets.yml --ask-vault-pass | head -3
# AC5 (template render dry-run via ansible debug)
ansible localhost -m template -a "src=templates/graphiti.env.j2 dest=/tmp/test-env.phase3.txt" \
  -e enable_phase_4_bridge=false  -e openai_api_key=test -e openai_admin_key=test
ansible localhost -m template -a "src=templates/graphiti.env.j2 dest=/tmp/test-env.phase4.txt" \
  -e enable_phase_4_bridge=true   -e openai_api_key=test -e openai_admin_key=test \
  -e litellm_base_url=http://test:4000/v1 -e litellm_model_name=gemma-reasoner
diff /tmp/test-env.phase3.txt /tmp/test-env.phase4.txt    # confirm phase delta
# AC6 (template content match)
diff <(ansible localhost -m template -a "src=templates/cost-cap.sh.j2 dest=/tmp/test-cap.sh" \
        -e daily_cap_usd=1.00 -e ntfy_url=http://test/ -e graphiti_compose_dir=/srv/graphiti) \
     homelab-playbook/scripts/cost-cap.sh    # E4-S04 reference
# AC10
yq '.hosts, .roles' homelab-infra/ansible/playbooks/deploy-ai-dev-context-stack.yml
diff <(yq '.[0] | keys' homelab-infra/ansible/playbooks/deploy-ai-dev-container.yml) \
     <(yq '.[0] | keys' homelab-infra/ansible/playbooks/deploy-ai-dev-context-stack.yml)   # similar key set
# AC12
test -f homelab-infra/ansible/roles/ai-dev-context-stack/README.md && wc -l !$
```

**Rollback (story-level — undo the role authoring):**
```bash
git rm -r homelab-infra/ansible/roles/ai-dev-context-stack/
git rm homelab-infra/ansible/playbooks/deploy-ai-dev-context-stack.yml
```

## Dependencies

- **Blocks:** E4-S08 (the actual ct-dev-homelab deploy) and indirectly E4-S11 (KPI scorecard depends on a deploy having happened)
- **Blocked by:** E2-S01 (GitNexus install captured), E3-S01 (Graphiti compose unit captured), E3-S07 (Graphiti backup scripts captured), E4-S04 (cost-cap.sh + cron content), E4-S05 (Phase-4 .env template — including the deferred-state variant), E4-S03 (skill backup copy at `homelab-playbook/skills/wiki-query/`)

## Risks and Mitigations

| Risk | Source | Mitigation |
|---|---|---|
| Composing E2/E3 roles introduces version drift if their internals change | Role composition | `meta/main.yml` deps + each sub-role pinned to its repo SHA via `requirements.yml` if the operator wants belt-and-suspenders; keep dependency surface small and unit-tested per role |
| Vault password rotation breaks deploys | Operator workflow | Document `--ask-vault-pass` is the default; alternative `--vault-password-file` for CI; rotation runbook is a wiki page (post-this-story backlog) |
| Inventory entry for `ct-dev-homelab` doesn't exist or has stale credentials | Pre-existing infra | Implementation Notes specify adding it if absent; PR review confirms at deploy time |
| Idempotency bug in a sub-task → repeated runs report changed when nothing actually changed | Ansible patterns | AC11 hard requirement; CI-style check with `--check --diff` on second run |
| Role embeds `ct-ai-01.tail-scale.ts.net` for the MCP URL — but `ct-dev-homelab`'s Graphiti instance is the deploy target itself | Naming confusion | The deploy *runs* on `ct-dev-homelab` and registers MCP pointing to `ct-ai-01` (where Graphiti actually lives). The role does NOT install Graphiti on `ct-dev-homelab` — `ct-dev-homelab` is just a *Claude Code client* of the existing Graphiti on `ct-ai-01`. This is captured in `register-mcp.yml`. Document explicitly in README. |

### Critical clarification: target topology

`ct-dev-homelab` is a **client** of the Context Stack, not a host of Graphiti. The deploy installs:
- On `ct-dev-homelab`: Claude Code skill (wiki-query), wiki tree, MCP registration pointing to ct-ai-01
- On the workstation (delegate-to-localhost): GitNexus + skill mirror
- On `ct-ai-01` (already deployed in E3): no changes from this role unless `enable_phase_4_bridge` flips, in which case `.env` is updated

This is a deliberate decoupling. The architecture diagram (§3 of architecture.md) shows it: Graphiti runs on `ct-ai-01`, every other Claude Code client (including `ct-dev-homelab`) reaches it via Tailscale. **The role validates the *client surface* on `ct-dev-homelab` — it does not duplicate Graphiti.**

## Definition of Done

- [ ] All ACs pass (AC1–AC12) under dry-run
- [ ] `homelab-infra/ansible/roles/ai-dev-context-stack/` committed with full structure (AC1)
- [ ] `homelab-infra/ansible/playbooks/deploy-ai-dev-context-stack.yml` committed
- [ ] `vars/secrets.yml` is ansible-vault-encrypted; vault password documented in operator's password store
- [ ] `ansible-lint` and `yamllint` exit 0 on the new role
- [ ] `--syntax-check` passes on the playbook
- [ ] AC11 idempotency check passes on second `--check --diff` run (NOTE: full idempotency proof requires actual deploy in E4-S08 — this story dry-runs)
- [ ] README.md committed with deploy + rollback recipes
- [ ] No regression in existing roles (`ai-dev-tmux`, `ai-dev-hermes`) — verified by re-running their playbooks `--check`
- [ ] Cross-reference task added: `AT-FR-DEP-001a`, `AT-FR-DEP-008a` (Phase 5a will populate)
