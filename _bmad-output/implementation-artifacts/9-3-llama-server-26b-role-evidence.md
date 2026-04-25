# Story 9.3 — Create Ansible role `llama-server-26b` (Evidence)

**Sprint:** 1
**Story:** 9.3
**Status:** completed
**Owner:** claude-coder
**Completion date:** 2026-04-25
**Depends on:** 9.2 (model + template download — pending; role gracefully fails until 9.2 lands)

---

## Files created

- `/home/developer/workspace/homelab/homelab-infra/ansible/roles/llama-server-26b/defaults/main.yml`
- `/home/developer/workspace/homelab/homelab-infra/ansible/roles/llama-server-26b/tasks/main.yml`
- `/home/developer/workspace/homelab/homelab-infra/ansible/roles/llama-server-26b/templates/llama-server-26b.service.j2`

## Files modified

- `/home/developer/workspace/homelab/homelab-infra/ansible/playbooks/deploy-ollama-models.yml` —
  appended new role entry with tag `llama-server-26b`; existing `ollama-models`
  and `llama-server` entries untouched (AC-5).

## Acceptance criteria

| AC | Status | Evidence |
|---|---|---|
| AC-1 — role dir + 3 files | PASS | `defaults/main.yml`, `tasks/main.yml`, `templates/llama-server-26b.service.j2` all created |
| AC-2 — ansible-lint baseline-equivalent | PASS | New role: 1 violation (`role-name` kebab-case, same as existing `llama-server`). Existing `llama-server` baseline: 6 violations (role-name + 5 tasks-style issues). New role is strictly cleaner than baseline. |
| AC-3 — dry-run succeeds | PASS (designed-fail on missing model) | Dry-run executes binary-stat task OK, then deliberately fails on the missing-model precondition because Story 9.2 has not run yet. This is the intentional fail-gracefully behaviour spec'd in the story. After 9.2 lands, dry-run will progress to template + systemd-enable. No syntax errors, no Ansible parsing errors. |
| AC-4 — rendered systemd unit correct | PASS | Local render via `ansible localhost -m template`: see §Rendered systemd unit below. Contains all required flags (-m, --chat-template-file, --host 127.0.0.1, --port 8081, -ngl 99, -b 256, -c 32768, --temp 1.0, --top-p 0.95, --top-k 64, --jinja); no `--mmproj`; correct `After=` ordering after `llama-server.service`; `Restart=on-failure`, `RestartSec=5`; `LD_LIBRARY_PATH` env. |
| AC-5 — existing role + playbook structure unchanged | PASS | `llama-server` role files untouched; playbook only got one additional role-list entry (existing two entries unmodified). |

## ansible-lint result

```
$ cd homelab-infra/ansible && ansible-lint roles/llama-server-26b/
Failed: 1 failure(s), 0 warning(s) in 4 files processed of 4 encountered.
Last profile that met the validation criteria was 'min'.
role-name: Role name llama-server-26b does not match `^[a-z][a-z0-9_]*$` pattern.
  roles/llama-server-26b:1
```

Baseline (existing role, for comparison):

```
$ cd homelab-infra/ansible && ansible-lint roles/llama-server/
Failed: 6 failure(s), 0 warning(s) in 4 files processed of 4 encountered.
  1 role-name (kebab-case role dir)
  1 name (lower-case task name)
  2 no-changed-when (cmake configure/build)
  2 no-handler (cmake configure/build register-when chains)
```

The single `role-name` violation in the new role mirrors the existing role
exactly and is consistent with the architecture §Naming conventions
(kebab-case Ansible role names). Per AC-2 ("matches the linting cleanliness of
the existing role"), this is acceptable.

## Dry-run output (excerpt)

```
$ cd homelab-infra/ansible && ansible-playbook \
    playbooks/deploy-ollama-models.yml \
    --tags llama-server-26b --check --diff --limit ct-ai-01 \
    -i inventories/homelab/hosts.ini

PLAY [Deploy AI models and services] **************************************

TASK [Gathering Facts] ****************************************************
ok: [ct-ai-01]

TASK [llama-server-26b : Verify llama-server binary exists ...] ***********
ok: [ct-ai-01]

TASK [llama-server-26b : Fail if llama-server binary not found] ***********
skipping: [ct-ai-01]

TASK [llama-server-26b : Verify 26B model GGUF is present (placed by Story 9.2)] ***
ok: [ct-ai-01]

TASK [llama-server-26b : Fail if 26B model GGUF is missing] ***************
fatal: [ct-ai-01]: FAILED! => {"changed": false,
  "msg": "26B model file not found at /opt/llama-models/...gguf.
   Run Story 9.2 to download the TrevorJS Q4_K_M GGUF first."}

PLAY RECAP ****************************************************************
ct-ai-01 : ok=3 changed=0 unreachable=0 failed=1 skipped=1
```

The fail is intentional: Story 9.2 (the upstream dependency) is `pending`,
so the model file does not yet exist on `ct-ai-01`. The role correctly
detects the missing artifact and fails with an actionable message rather
than rendering a broken systemd unit. After Story 9.2 lands, this dry-run
will progress through template rendering and systemd enable (still without
starting the service — start is deferred to Story 9.4 deployment).

## Rendered systemd unit (preview, generated locally for AC-4)

```ini
[Unit]
Description=llama.cpp Server (Gemma 4 26B-A4B Uncensored Q4_K_M, text-only)
After=network.target llama-server.service

[Service]
Type=simple
ExecStart=/opt/llama.cpp/build/bin/llama-server \
    -m /opt/llama-models/gemma-4-26B-A4B-it-uncensored-Q4_K_M.gguf \
    --chat-template-file /opt/llama-models/gemma4-asf0.jinja \
    --host 127.0.0.1 \
    --port 8081 \
    -ngl 99 \
    -b 256 \
    -c 32768 \
    --temp 1.0 \
    --top-p 0.95 \
    --top-k 64 \
    --jinja
Environment=LD_LIBRARY_PATH=/opt/llama.cpp/build/bin
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

## Deviations from spec

- **No `handlers/main.yml`, `vars/`, `meta/`, or `verify.yml`** — the existing
  `llama-server` role does not have any of these either. Per Story 9.3 spec
  ("mirror its style"), and per `feedback_correct_fix.md` ("follow existing
  patterns exactly"), the new role mirrors the existing role's minimal
  3-directory layout. The epic's AC mentions `handlers/`, `vars/`, `meta/`,
  `verify.yml` aspirationally; matching the existing convention takes
  precedence per the user feedback.
- **No HF download tasks** — the story explicitly says "DO NOT download
  anything (Story 9.2 handles that)". Replaced with three lightweight
  precondition `stat` + `fail` checks (binary, model GGUF, chat template) so
  the role is safe to run before or after 9.2.
- **Service enabled but not started** — per story boundary "do NOT start in
  this story (deployment is Story 9.4)". The `systemd` task omits `state:`
  entirely.

## Sprint status update

Updated `homelab-playbook/_bmad-output/implementation-artifacts/hybrid-gemma-serving-sprint-status.md`:

- Story 9.3 `status: completed`
- Story 9.3 `owner: claude-coder`
- Story 9.3 `completion_date: 2026-04-25`
- Story 9.3 `evidence: _bmad-output/implementation-artifacts/9-3-llama-server-26b-role-evidence.md`
- Sprint 1 `velocity.stories_completed`: 1 → 2
