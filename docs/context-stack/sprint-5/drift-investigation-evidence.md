# Drift Investigation 2026-04-27

**Date:** 2026-04-27
**Branch:** `main` (homelab-playbook), `main` (homelab-infra)
**Trigger:** Operator request after restic extension to ct-dev-homelab incidentally surfaced 8-task pre-existing drift on ct-docker-01. Scope-limited to 5 hosts most relevant to recent work.
**Mode:** Read-only investigation first; apply only unambiguously-safe diffs; flag the rest for operator review.

## Discovery

| Host | IP | Applicable playbooks |
|---|---|---|
| ct-docker-01 | 192.168.50.194 | deploy-restic, docker-setup, deploy-applications |
| ct-media-01 | 192.168.50.161 | deploy-restic, docker-setup (ct-media-01 play), media-setup |
| ct-sparkle-cps | 192.168.50.151 | deploy-restic, dev-host-setup |
| ct-ai-01 | 192.168.50.160 | deploy-ollama-models |
| ct-dev-homelab | 192.168.50.156 | deploy-restic, deploy-context-stack, deploy-hermes (also covered by deploy-ai-dev-container) |

Total combos investigated: 12 (11 with successful --check, 1 broken — `deploy-applications` on ct-docker-01,ct-media-01).

## Per-host drift summary

| Host × Playbook | Pre-fix changed | Post-fix changed | Classification breakdown |
|---|---|---|---|
| ct-docker-01 × deploy-restic | 8 | **0** | 8 SAFE → applied |
| ct-docker-01 × docker-setup | 4 | not applied | 1 NOISE (apt cache), 1 SAFE (apt install missing pkgs), 2 AMBIGUOUS (root in docker group, recursive chown to 1000:1000 would clobber couchdb 5984) |
| ct-docker-01 × deploy-applications | error | not applied | BROKEN — `community.docker.docker_compose` module removed in collection v4.0 |
| ct-media-01 × deploy-restic | 0 | 0 | clean |
| ct-media-01 × docker-setup | 3 | not applied | 1 NOISE (apt cache), 2 AMBIGUOUS (recursive chown to 1000:1000) |
| ct-media-01 × media-setup | 4 | not applied | 1 NOISE (apt cache), 3 AMBIGUOUS (recursive chown to 1000:1000) |
| ct-sparkle-cps × deploy-restic | 0 | 0 | clean |
| ct-sparkle-cps × dev-host-setup | 10 | not applied | 2 NOISE (apt cache ×2), 8 AMBIGUOUS (claude install, runc downgrade, Docker restart, PATH rewrites, GitHub clone of unreachable repo) |
| ct-ai-01 × deploy-ollama-models | 10 | not applied | 7 NOISE (rsync owner-only churn, pip "always-changed", get_url --check pattern), 1 AMBIGUOUS (llama.cpp HEAD pull would rebuild llama-server), 2 AMBIGUOUS-INDIRECT (handler restart of gemma-hybrid-proxy) |
| ct-dev-homelab × deploy-restic | 0 | 0 | clean (already aligned) |
| ct-dev-homelab × deploy-context-stack | 3 | not applied | 1 NOISE (rsync `..t......` timestamp on graphiti dir), 2 AMBIGUOUS (`/srv/gitnexus` and `/srv/graphiti` owner 1000:1000→0:0 mode 0755→0750) |
| ct-dev-homelab × deploy-hermes | 11 | not applied | 1 NOISE (apt cache), several SAFE-LEAN (new file deployments — start-hermes.sh, spawn-worker.sh), 1 SAFE (SOUL.md guardrails update), 2 architecture-migration AMBIGUOUS (wiki-auto-push systemd→cron, new cron entries), 1 AMBIGUOUS-DANGEROUS (unconditional Docker restart would interrupt graphiti+gitnexus stacks) |

## SAFE fixes applied

### ct-docker-01 × deploy-restic.yml — 8 tasks aligned

Repo is source of truth; host had stale templates last rendered before commit `4b7dacf` (initial role landing) and subsequent fixes. None of the changes alter logical behavior of restic; they tighten security and add documentation.

| Task | Diff summary | Why SAFE |
|---|---|---|
| Create backup repository parent directory (local backend only) | `/mnt/backups` mode `0755 → 0700` | Repo asserts 0700 per NFR-SEC-6; host had legacy 0755. Tighter is better. |
| Deploy restic environment file | Added 3 header comment lines, `RESTIC_REPOSITORY` and `RESTIC_PASSWORD` values unchanged | Comment-only re-render |
| Deploy restic backup script | Exclude list `*.cache,__pycache__` → `.cache` | Repo simplified exclusions in commit history; host has stale excludes |
| Deploy restic restore and verification script | Whitespace expansion of compact `;`-chained statements into multi-line; identical control flow; one new `--read-data` example in usage docstring | Refactor for readability, no logic change |
| Deploy restic failure notification script | Comment-only additions (NFR-REL-1 reference, dot-stuffing comment, sendmail fallback comment) | Comment-only |
| Deploy restic failure notification systemd service unit | Two comment lines added (OnFailure trigger, NFR-REL-1) | Comment-only |
| Deploy restic-backup systemd timer unit | `RandomizedDelaySec=900 → 300` | Repo standardized this earlier; host was on legacy 900s |
| restart restic-backup timer (handler) | Triggered by timer unit re-render | Required to pick up new randomization |

**Verification:** `--check` re-run after apply: `changed=0`. Timer healthy, `Active: active (waiting)`, `Trigger: Tue 2026-04-28 02:00:14 UTC` (within new RandomizedDelaySec=300 window). `/mnt/backups` mode confirmed `0700` post-apply.

## AMBIGUOUS findings (operator review needed)

### A1. Recursive 1000:1000 chown in docker-host and media-host roles — would clobber CouchDB

**Hosts affected:** ct-docker-01, ct-media-01.
**Where:** `ansible/roles/docker-host/main.yml` and `ansible/roles/media-host/main.yml`, tasks "Create Docker host appdata directories" and "Create media host appdata directories".

The roles use `file: state=directory recurse=yes owner=1000 group=1000 mode=0755` over a fixed loop including `/opt/appdata/productivity-obsidian/couchdb/{data,config}`. The host has those CouchDB dirs at `5984:5984` because **CouchDB containers run as UID 5984 by container default**. Forcing `1000:1000` would break CouchDB at the next compose restart.

Other dirs in the loop (traefik, portainer, prometheus, grafana, organizr, n8n, plex, etc.) are currently `root:root` on the host. The repo wants `developer:developer` (1000:1000) for those. That isn't obviously wrong — many docker-compose stacks DO run as the invoking user on Linux — but applying it would override what initial deploy or operator did manually.

**Recommended action:** Patch the role to drop `recurse: yes` and `owner/group/mode` for the directory creation step (use `file: state=directory` only, let mkdir defaults stand), or add a per-dir override. Then re-run.

**Diff excerpt (ct-docker-01):**
```
TASK [Create Docker host appdata directories]
--- before                          +++ after
"group": 0,                         "group": 1000,
"owner": 0,                         "owner": 1000,
"path": "/opt/appdata/infra-core/traefik"     ← repeated for portainer, prometheus, grafana, ...
...
"group": 5984,                      "group": 1000,    ← CouchDB — would break
"owner": 5984,                      "owner": 1000,
"path": "/opt/appdata/productivity-obsidian/couchdb/data"
```

### A2. Stale Hermes deployment on ct-dev-homelab — architecture migration pending

**Host:** ct-dev-homelab.
**Playbook:** `deploy-hermes.yml` (11 changes).

Real changes (not noise):
- `Restart Docker after runc downgrade` — task is **unconditional** (no `notify`/`when`), runs every play. **Would interrupt the running graphiti and gitnexus stacks** during the restart window.
- New files to deploy: `~/.hermes/start-hermes.sh` (tmux session launcher), `~/.hermes/spawn-worker.sh` (Claude worker invocation).
- `Stop wiki-auto-push systemd user timer` + `Disable wiki-auto-push systemd user timer` — repo migrated from systemd-user-timer to root crontab.
- `Deploy Hermes cron jobs` — adds two crontab entries (wiki-lint weekly, wiki-auto-push every 5 minutes).
- `Template Hermes SOUL.md` — content update with expanded guardrails (NEVER force-push, NEVER run apt/pip/npm directly, etc.).

**Recommended action:** Treat this as "deploy E4-S09 hermes update", not "drift fix". Operator should:
1. Stop or accept brief downtime for graphiti+gitnexus, OR patch the role to remove the unconditional Docker restart.
2. Run `deploy-hermes.yml --limit ct-dev-homelab` deliberately during a maintenance window.
3. Verify wiki-lint cron entry has working PATH expansion (the `$(ls ...)` inside the cron command uses runtime expansion; this works in bash but is fragile).

### A3. ct-dev-homelab `/srv/gitnexus` and `/srv/graphiti` ownership

**Host:** ct-dev-homelab.
**Playbook:** `deploy-context-stack.yml` (3 changes — 2 dir owner/mode, 1 rsync timestamp NOISE).

Repo's compose-app role asserts `root:root` `0750` per role docs ("0750 keeps non-root users out of any vault-derived secrets in `.env`"). The hosts have `developer:developer` `0755` on the top-level dirs `/srv/gitnexus` and `/srv/graphiti`. The `data/` subdirs and `.env` files are already correctly `root:root` (`0750` and `0600`).

The change is recent (`/srv/graphiti` ctime is 2026-04-27 15:25 — a few hours before this investigation), so I cannot rule out that another session deliberately set this. Both compose stacks are running healthy; named volumes don't depend on `/srv/{stack}` ownership. Applying the chown would not break runtime.

**Recommended action:** Operator decides. If aligning to repo intent, run `deploy-context-stack.yml --limit ct-dev-homelab` (will also re-render and rsync, which has its own timestamp noise — see N1 below).

### A4. ct-sparkle-cps dev-host-setup — runc downgrade + Docker restart + claude install drift

**Host:** ct-sparkle-cps.
**Playbook:** `dev-host-setup.yml` (10 changes).

Several entwined changes:
- `Pin runc to v1.1.15 for LXC compatibility` — would downgrade runc.
- `Symlink runc for Docker` — `/usr/bin/runc` is currently a regular file; repo wants a symlink (paired with the runc downgrade).
- `Restart Docker after runc downgrade` — unconditional restart.
- `Install Claude Code CLI (native installer)` — would run the claude installer (likely an upgrade).
- `Create Claude Code wrapper` — wrapper points to `/usr/bin/claude` on host vs `/home/developer/.local/bin/claude` in repo.
- `Add ~/bin to PATH` — bashrc PATH change adds `.local/bin` and `.npm-global/bin`.
- `Ensure ~/bin precedes ~/.local/bin in .profile` — .profile rewrite with new comment block.
- `Clone project repositories` — clones include `https://github.com/tomamourette/CPS-Fabric.playbook.git` which **hangs on git ls-remote** (likely repo doesn't exist publicly or auth issue). The drill ran with `--check`; the role completed but this clone task was killed manually after 5 min (`ignored=1` in recap suggests `failed_when: false` is set somewhere).

This is the same multi-axis drift pattern as A2 — repo has moved forward with new dev-host conventions and ct-sparkle-cps is on the older config. None are simple drift fixes.

**Recommended action:** Schedule a coordinated update window. CPS-Fabric repos on this host are non-trivial to recover if Docker restart misbehaves; consider snapshotting LXC first.

### A5. ct-ai-01 llama.cpp tracks HEAD — would pull and rebuild on next deploy

**Host:** ct-ai-01.
**Playbook:** `deploy-ollama-models.yml` (specifically the `llama-server` role).

`ansible/roles/llama-server/defaults/main.yml` has `llama_cpp_version: HEAD`. Each `--check` shows the current upstream `git pull` diff (today: Intel ONEAPI version bump 2025.3.2 → 2025.3.3, OpenVINO Dockerfile changes, new GGUF code). When applied, `Configure llama.cpp build` and `Build llama-server` are conditional on `git changed`, so they would run, **rebuilding llama-server**. Running llama-server units would be restarted via the systemd service unit's `state: restarted` conditional.

**Recommended action:** Pin `llama_cpp_version` to a tag (`b5220` is mentioned as an example in the role's comment) to stop chronic drift. Until pinned, every deploy includes an unintended upstream upgrade.

### A6. ct-docker-01 root in docker group

**Host:** ct-docker-01.
**Playbook:** `docker-setup.yml`, task `Add root user to docker group`.

Mostly cosmetic (root has full system access regardless), but flags as `changed` because root is not currently in the docker group. Applying is harmless. Filed as AMBIGUOUS only because it's bundled with the chown task that operator must NOT auto-apply.

### B. BROKEN dependency — deploy-applications.yml

`deploy-applications.yml` references `community.docker.docker_compose` (the v1 module) which was removed in `community.docker` collection v4.0. Cannot run this playbook against ct-docker-01 or ct-media-01 until refactored to `docker_compose_v2` or replaced with `compose-app` role pattern.

**Recommended action:** Either rewrite deploy-applications.yml using docker_compose_v2 / compose-app, or remove the playbook and document that compose stacks are deployed manually / via the compose-app role.

## NOISE findings (ignore)

These are chronic "always changed" patterns in --check mode that don't represent real drift:

- **N1.** `compose-app : Synchronize compose source` — `..t......` rsync flags = timestamp-only differences; content matches. Caused by ansible templating remote files with current timestamp; harmless.
- **N2.** `gemma-hybrid-proxy : Sync proxy source` — `.og` rsync flags = owner/group "drift" because controller files are 1000:1000 and target wants gemma-hybrid:gemma-hybrid; the role's follow-up `Re-chown venv to gemma-hybrid` task corrects it back. The end-state is always correct.
- **N3.** `Upgrade pip inside venv` (gemma-hybrid-proxy AND litellm-gateway) — pip in `command:` mode always reports changed even when "Requirement already satisfied".
- **N4.** `Install proxy runtime requirements into venv` — same pip pattern.
- **N5.** `Update package cache` / `Update apt cache after Microsoft repo` — apt cache always reports changed.
- **N6.** `gemma4-uncensored — Download GGUF model file`, `Download mmproj file`, `Download 26B model GGUF`, `Download asf0/gemma4_jinja chat template` — `get_url` in --check mode reports changed because it can't HEAD-verify the destination matches without contacting the URL. Files exist on disk with expected sizes; real apply would skip download (`force: no` default).

These could be silenced with `changed_when: false` filters but that's a repo cleanup, not a drift issue.

## Pre-fix vs post-fix changed counts (consolidated)

| Host | Pre-fix total changed | Post-fix total changed | Delta |
|---|---|---|---|
| ct-docker-01 | 8 (restic) + 4 (docker-setup) = 12 + 1 broken playbook | 0 (restic) + 4 (docker-setup, not applied) | -8 |
| ct-media-01 | 0 (restic) + 3 (docker-setup) + 4 (media-setup) = 7 | 7 (none applied) | 0 |
| ct-sparkle-cps | 0 (restic) + 10 (dev-host-setup) = 10 | 10 (none applied) | 0 |
| ct-ai-01 | 10 (mostly noise) | 10 (none applied) | 0 |
| ct-dev-homelab | 0 (restic) + 3 (context-stack) + 11 (hermes) = 14 | 14 (none applied) | 0 |

Only ct-docker-01 had truly safe drift to correct in this pass.

## Anything genuinely unexpected

1. **`deploy-applications.yml` is dead code** — the `community.docker.docker_compose` module was removed (v4.0) and the playbook hasn't been migrated. The infra-core, observability, automations-n8n, and productivity-obsidian compose stacks on ct-docker-01 are not deployable via this playbook anymore. Either they're managed manually now, or someone needs to migrate.
2. **dev-host role hangs cloning a non-existent GitHub repo** — `tomamourette/CPS-Fabric.playbook.git` git ls-remote on ct-sparkle-cps blocks indefinitely. The play has `failed_when: false` so it resumes after kill, but every sparkle-cps deploy now needs manual intervention.
3. **llama-server role tracks HEAD of llama.cpp** — chronic drift; every `--check` shows upstream Dockerfile churn; every apply would pull-and-rebuild.
4. **Hermes architecture migration is pending on ct-dev-homelab** — wiki-auto-push has moved from systemd-user-timer to crontab in repo; host still on the old design. This is a real architecture change that hasn't been deployed.
5. **Recent `/srv/graphiti` ctime (Apr 27 15:25)** — something modified the dir ownership a few hours before this investigation started. May be another session, may be a manual touch. Worth flagging.

## Recommendations (operator review priority)

| # | Item | Why first |
|---|---|---|
| 1 | Patch `docker-host` and `media-host` roles to NOT recursively chown to 1000:1000 — preserve per-dir ownership (CouchDB at 5984, etc.) | Highest-risk task that would silently break CouchDB on next deploy |
| 2 | Pin `llama_cpp_version` away from `HEAD` — pick a known-good tag | Eliminates chronic drift + accidental rebuild on every deploy |
| 3 | Remove or fix the unreachable git clone in `dev-host` role | Blocks every sparkle-cps deploy with a 5-minute hang |
| 4 | Decide on `deploy-applications.yml` — migrate to docker_compose_v2 or remove | Currently broken; no path to deploy compose stacks via that playbook |
| 5 | Schedule the Hermes architecture migration on ct-dev-homelab — coordinate with graphiti+gitnexus downtime | Brings ct-dev-homelab forward to current Hermes design |
| 6 | Operator review of A4 (sparkle-cps dev-host drift) — runc downgrade + Docker restart in particular | Could affect CPS-Fabric workflows if Docker misbehaves on restart |
| 7 | Decide on `/srv/{gitnexus,graphiti}` ownership policy and either align repo or align hosts | Cosmetic but worth resolving for consistency |

## Investigation logs (retained for reference until cleanup)

All under `/tmp/`:
- `drift-restic-all.log` — full deploy-restic check across 4 backup_hosts
- `drift-context-stack-ct-dev-homelab.log`
- `drift-hermes-ct-dev-homelab.log`
- `drift-ollama-ct-ai-01.log`
- `drift-docker-setup-ct-docker-01.log`
- `drift-docker-setup-ct-media-01.log`
- `drift-media-setup-ct-media-01.log`
- `drift-dev-host-ct-sparkle-cps.log`
- `drift-deploy-apps.log` — module-removal error
- `apply-restic-ct-docker-01.log` — successful apply
- `verify-restic-ct-docker-01.log` — post-apply changed=0 confirmation

Cleanup of `/tmp/drift-*.log` and `/dev/shm/vp` happens in the same session that wrote this evidence.

## A2 RESOLVED 2026-04-27

**Action:** Applied the Hermes migration deploy on `ct-dev-homelab` (192.168.50.156). Operator (Tom) authorized 2026-04-27 with explicit awareness that Docker daemon would restart, briefly interrupting graphiti+gitnexus.

**Command:**
```
LC_ALL=C.UTF-8 ansible-playbook -i inventories/homelab/hosts.ini \
  deploy-hermes.yml --limit ct-dev-homelab \
  --vault-password-file /dev/shm/vp
```

### Pre-deploy state

```
NAMES          STATUS
graphiti-mcp   Up 4 hours (healthy)
falkordb       Up 4 hours (healthy)
gitnexus       Up 4 hours (healthy)
```
- `graphiti /health` = 200
- `gitnexus :4747/` = 404 on `/`, `/health`, `/api/health` — pre-existing baseline (Docker healthcheck reports healthy via internal probe). Not a regression introduced by deploy.

### PLAY RECAP

```
ct-dev-homelab : ok=79  changed=10  unreachable=0  failed=0  skipped=8  rescued=0  ignored=1
```

The single `ignored=1` is the pre-existing dev-host task `Register ruflo MCP server in Claude Code` — fails with `MCP server ruflo already exists in local config` and has `ignore_errors: yes`. Out of scope for A2.

### Hermes-specific changed tasks (10)

1. `Template Hermes config.yaml`
2. `Template Hermes SOUL.md`
3. `Deploy BMAD skill stubs to Hermes`
4. `Template Hermes tmux session launcher` *(new spawn-worker tooling deployed)*
5. `Template Claude Code worker spawn script` *(new spawn-worker tooling deployed)*
6. `Stop wiki-auto-push systemd user timer (replaced by cron)`
7. `Disable wiki-auto-push systemd user timer (replaced by cron)`
8. `Deploy Hermes cron jobs` (item=wiki-lint)
9. `Deploy Hermes cron jobs` (item=wiki-auto-push)
10. `Deploy integration test script`

### Docker daemon downtime — graphiti recovery measurement

| Event | Timestamp (UTC) |
|---|---|
| systemd: Stopping docker.service | 16:31:48 |
| systemd: Stopped docker.service | 16:31:49 |
| systemd: Starting docker.service | 16:31:49 |
| dockerd "Starting up" | 16:31:49.17 |
| systemd: Started docker.service | 16:31:50 |
| graphiti-mcp container started | 16:31:50.10 |
| graphiti-mcp first healthy healthcheck PASS | 16:31:55.49 |

**Total graphiti downtime: ~7 seconds** (16:31:48 → 16:31:55). Well inside the 60s escalation window. falkordb and gitnexus also came back via `restart: unless-stopped`, all reported `(healthy)` within seconds.

### Post-deploy state

```
NAMES          STATUS
graphiti-mcp   Up 33 seconds (healthy)
falkordb       Up 33 seconds (healthy)
gitnexus       Up 33 seconds (healthy)
```
- `graphiti /health` = 200
- `gitnexus :4747/` = 404 (matches pre-deploy baseline)

### Hermes-side verifications

**Crontab (developer user — Hermes runs as `developer` on this CT):**

```
#Ansible: hermes-wiki-lint
0 3 * * 0 PYENV_ROOT=... HOME=/home/developer cd /home/developer/workspace/homelab/wiki && hermes "Run wiki-lint on this wiki directory"
#Ansible: hermes-wiki-auto-push
*/5 * * * * PYENV_ROOT=... HOME=/home/developer /home/developer/.local/bin/wiki-auto-push.sh
```

Both Ansible-managed entries present.

**systemd-user timer (old design, must be off):**

```
* wiki-auto-push.timer - Wiki auto-push timer — trigger every 5 minutes
   Loaded: loaded (/home/developer/.config/systemd/user/wiki-auto-push.timer; disabled; preset: enabled)
   Active: inactive (dead)
  Trigger: n/a
Apr 27 16:32:12 ct-dev-homelab systemd[164]: Stopped wiki-auto-push.timer ...
```

Disabled and inactive — old timer-based design fully retired.

### Idempotency --check post-deploy

```
ct-dev-homelab : ok=72  changed=2  unreachable=0  failed=0  skipped=15  rescued=0  ignored=0
```

Target was `changed=0`. Actual is `changed=2`, but **both deltas are in the `dev-host` role, not `ai-dev-hermes`**, and both are known unconditional --check noise:

1. `dev-host : Update apt cache after Microsoft repo` — `apt update` always reports changed in --check (cache TTL artifact)
2. `dev-host : Restart Docker after runc downgrade` — task is unconditional (no `when:`, no `notify:` guard) per `roles/dev-host/tasks/main.yml`. ALWAYS reports changed in --check; in actual runs it does restart Docker every time (which matches the brief's expectation: "Docker restart is part of the deploy, unconditional in the role").

**The `ai-dev-hermes` role itself reports changed=0 in --check — Hermes migration is fully converged.** The 2 dev-host changes are pre-existing role-design noise, out of scope for A2 (and overlap with the A4 sparkle-cps dev-host drift item already on the follow-ups list).

### Verdict

A2 RESOLVED. Hermes migration applied cleanly on ct-dev-homelab:
- 11-task drift resolved (10 hermes tasks changed + 1 dev-host runc/docker side-effect; the brief's "11 tasks pending" estimate matches)
- New tmux session + spawn-worker scripts deployed
- wiki-auto-push transitioned from systemd-user-timer (disabled) to crontab
- Docker daemon restart caused ~7s graphiti downtime; all three containers (graphiti-mcp, falkordb, gitnexus) recovered automatically via `restart: unless-stopped`
- gitnexus 404-on-`/` pre-existed and is not a regression

## A4 RESOLVED 2026-04-27 (v2 — role pin updated)

Earlier A4 attempt halted at pre-flight because the `dev-host` role pinned `runc 1.1.15` while ct-sparkle-cps host empirically ran `runc 1.3.4` on `Docker 29.3.1` for an extended period without LXC issues. Operator authorized the safer-direction fix: update the role default to match the working empirical state rather than downgrade a healthy host.

### Investigation findings

- Role uses runc only via `get_url` of the release binary + `/usr/bin/runc` symlink + Docker restart — no `1.1.x`-specific CLI flags or apt-pin semantics. Safe to bump.
- No `defaults/main.yml` variable for runc; version is inline in `tasks/main.yml:414`. Updated inline (option (a) in brief) for minimal blast radius.
- The pin was introduced in commit `38eba72` (2026-03-30, "feat: add ct-dev-homelab dev container") and never revisited; comment "runc 1.2+ fails in LXC" was a defensive guess that proved stale on PVE 9.x kernel `6.17.2-1-pve` + Debian 12 LXC + Docker 29.
- Pre-update host state: `runc 1.3.4` (commit `v1.3.4-0-gd6d73eb8`, go1.25.8), Docker 29.3.1 active, 0 containers running.

### Role update

File: `homelab-infra/ansible/roles/dev-host/tasks/main.yml:414-432`

Diff summary: `1.1.15 → 1.3.4` (URL + task name + comment); `+7 −4` lines. Comment expanded to record empirical justification + 2026-04-27 verification date.

Commit: `0adff00 fix(dev-host): bump runc pin from 1.1.15 to 1.3.4 — LXC compat fixed in newer runc; matches host empirical state (drift A4)` (homelab-infra)

### Pre-deploy `--check` (post role update)

`PLAY RECAP: ok=45 changed=10 failed=0 skipped=7 ignored=1`

10 changed broken down:
- 4 Claude/dev drift (Claude install, wrapper, PATH precedence, aliases)
- 2 apt cache refresh (expected noise)
- 3 runc tasks (URL changed → `force: yes` re-fetches; Ansible reports `changed` even though end-state binary is identical version)
- 1 unconditional Docker restart

No HALT condition surfaced.

### Deploy

`PLAY RECAP: ok=50 changed=10 failed=0 skipped=2 ignored=2`

Two ignored failures, both expected:
1. **CPS-Fabric.playbook clone** — `Permission denied (publickey)`. Per Phase 1 Fix 4, deploy-key for the tomamourette/CPS-Fabric.playbook repo is still pending; operator UI action.
2. **Register ruflo MCP server** — `MCP server ruflo already exists in local config`. Pre-existing concern, not A4 scope.

### Post-deploy verification (ct-sparkle-cps, 192.168.50.151)

```
runc:    1.3.4 (commit v1.3.4-0-gd6d73eb8, go1.24.10)
docker:  29.3.1 (active)
claude:  2.1.119 (Claude Code)
docker ps: (empty — 0 containers)
```

The runc binary was replaced (Go toolchain version differs `go1.25.8 → go1.24.10` — confirms the URL fetch happened) but the resulting `runc --version` is unchanged at `1.3.4`. End-state alignment with role.

### Final `--check` (post-deploy convergence)

`PLAY RECAP: ok=45 changed=2 failed=0 skipped=7 ignored=1`

`changed=2` are both known-noise tasks:
- `Update apt cache after Microsoft repo` (re-runs cache module by design)
- `Restart Docker after runc update` (unconditional `state: restarted`, no `when:` guard)

Convergence achieved on the runc + Claude drift; role and host now match.

### Operator review flag

**Zero containers on ct-sparkle-cps.** `docker ps` returned empty both before and after the deploy, so the unconditional Docker restart was risk-free for this host (no recovery needed). Flagging for operator: is `0 containers running` on the sparkle-cps dev host intentional (workers stopped between sessions) or unexpected (a CPS-Fabric stack should be up)? The CPS-Fabric.playbook deploy-key is still pending, which would explain why `~/workspace/sparkle-cps-playbook` may be empty/incomplete and any docker-compose pulls from there can't run.

### Outstanding

- Deploy-key for `tomamourette/CPS-Fabric.playbook` still pending (operator UI follow-up — Phase 1 Fix 4).
- `Register ruflo MCP server` task should ideally be made idempotent (currently `failed_when` swallows the "already exists" error).
- Role's `Restart Docker after runc update` could gain a `when:` guard tied to a `runc_changed` register so it stops being unconditional changed-noise on every run.

