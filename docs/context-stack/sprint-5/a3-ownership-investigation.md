# A3 — /srv/graphiti + /srv/gitnexus ownership investigation

**Date:** 2026-04-27
**Operator:** Tom ("I don't know why it changed")
**Brief premise:** host root:root vs role default 1000:1000
**Actual finding:** premise is **inverted** — host is at 1000:1000, role default is **root:root**

## Current state

```
$ ssh root@192.168.50.156 'find /srv -maxdepth 2 -printf "%M %u:%g %p\n"'
drwxr-xr-x root:root          /srv
drwxr-xr-x developer:developer /srv/graphiti
-rw-r--r-- developer:developer /srv/graphiti/docker-compose.yml
-rw-r--r-- developer:developer /srv/graphiti/graphiti_mcp_server.py.patched
-rw-r--r-- developer:developer /srv/graphiti/Dockerfile
-rw-r--r-- developer:developer /srv/graphiti/.env.sample
-rw-r--r-- developer:developer /srv/graphiti/config-graphiti-mcp.yaml
drwxr-xr-x developer:developer /srv/graphiti/scripts
drwxr-x--- root:root           /srv/graphiti/data
-rw------- root:root           /srv/graphiti/.env
drwxr-xr-x developer:developer /srv/gitnexus
-rw-r--r-- developer:developer /srv/gitnexus/docker-compose.yml
drwxr-x--- root:root           /srv/gitnexus/data
```

Top-level dirs and source files are `developer:developer` (1000:1000), `0755`. The vault-derived `.env` and the runtime `data/` subdirs are `root:root` (`0600`/`0750`), which is normal and expected (Docker creates bind-mount paths as root by default for the falkordb / gitnexus containers).

## Timeline reconstruction

```
$ stat -c "ctime=%y mtime=%y atime=%y owner=%U:%G" /srv/graphiti /srv/gitnexus
ctime=2026-04-27 15:25:59 mtime=2026-04-27 15:25:59 owner=developer:developer /srv/graphiti
ctime=2026-04-27 12:34:03 mtime=2026-04-26 12:01:03 owner=developer:developer /srv/gitnexus
 Birth: 2026-04-27 12:23:25  /srv/graphiti
 Birth: 2026-04-27 12:23:20  /srv/gitnexus
```

The 15:25:59 ctime on `/srv/graphiti` is the timestamp the brief asked about. journalctl correlation:

```
Apr 27 15:25:45 sshd[1532119]: Accepted publickey for root from 192.168.50.156 port 34532 ssh2
Apr 27 15:25:59 sudo[1532372]: developer : PWD=/home/developer/workspace/homelab/homelab-playbook/wiki ;
                               USER=root ; COMMAND=/usr/bin/rm -rf /home/developer/.graphiti-data.preserved-by-e3-s08
```

**No `chown` ran in this window.** The 15:25:59 sudo invocation is `rm -rf` against a path under `/home/developer/`, not `/srv/graphiti`. There were no ansible-playbook executions, no docker-compose lifecycle events touching `/srv/graphiti`, and no other write activity in the 15:25–15:26 window aside from the unrelated `wiki-auto-push.service` cron.

The directory's ctime can be updated by content changes inside it (e.g. rsync syncing the patched `graphiti_mcp_server.py.patched` file at 09:55, which has its own matching ctime) — ctime tracks any inode-metadata change including link-count updates when subdirs are created. Directory ownership has not been changed since birth at 12:23:25.

The first-ever ansible deploy that created `/srv/graphiti` was the E4-S08 deploy on 2026-04-27 around 12:23 UTC (see `Birth:` timestamps).

### Why the host is at developer:developer despite role default root:root

Reading the role at `homelab-infra/ansible/roles/compose-app/tasks/main.yml`:

```yaml
- name: Synchronize compose source from controller to target
  ansible.posix.synchronize:
    src: "{{ compose_app_source_dir }}/"
    dest: "{{ compose_app_target_dir }}/"
    delete: false
    rsync_opts:
      - "--exclude=.env"
      ...
```

`ansible.posix.synchronize` uses rsync. With no `-o`/`--owner` or `-g`/`--group` flags and no `--archive`/`-a`, rsync **preserves ownership from the controller source** when running as root on the destination (rsync's default for root-owned destinations is to attempt ownership preservation). The Ansible controller's working tree at `/home/developer/workspace/homelab/homelab-apps/stacks/{graphiti,gitnexus}/` is owned by `developer` (uid 1000) on the controller. So the rsync step writes the files to the LXC as `developer:developer`.

Then the `Ensure target directory exists` task runs **before** synchronize (it is task 4, synchronize is task 5). Its job is to `mkdir -p` the target — it is idempotent on an already-existing dir. It does declare `owner: "{{ compose_app_owner }}"` (defaulted to `root`), but with `state: directory` Ansible's `file` module will only enforce ownership change if the dir doesn't already match the spec. On the **first deploy** the dir was created by this task as root:root, then synchronize immediately overwrote that with developer:developer (rsync of an existing directory updates dir ownership too). On **subsequent deploys** the rsync continued to write developer:developer.

Net result: the host **correctly reflects what the deploy pipeline produced**. The role's declared default of `compose_app_owner: root` is dead code for the directory tree because synchronize runs after and wins. The `.env` template task (which renders to a fixed path with `owner: root`) is the only ownership directive that survives, which is why `.env` is correctly root:root with mode 0600.

No host_vars override exists for `compose_app_owner` (verified via `grep -rn compose_app_owner ansible/`). No manual chown is in any bash_history. The audit framework (auditd) is not active.

## Verdict: **Option Y — Role has a bug (latent), host correctly reflects what the role ships**

Concrete reasoning:

1. The host state (developer:developer for source files, root:root for the runtime `data/` dir, root:root 0600 for `.env`) is what the running pipeline actually produces. It has been that way since first deploy at 12:23 UTC on 2026-04-27.
2. The 15:25:59 ctime that triggered the investigation is unrelated to any ownership change — it is the inode-metadata ripple from a sibling cleanup command (`rm -rf ~/.graphiti-data.preserved-by-e3-s08`) that ran under the same ssh session, with no chown anywhere in scope.
3. The role's documented default (`compose_app_owner: root`) is incongruent with the rsync-over-non-archive synchronize task that follows. The two interlocks fight, and synchronize wins. Therefore: the role has a latent design inconsistency, but no run actively *changed* anything — both the original deploy and every re-run land at the same host state.
4. Tom's "I don't know why" matches reality: nobody ran a chown, nobody overrode the default. The role just behaves this way.

Discounting the alternatives:

* **Option X (role works as designed, host is wrong)** — rejected. The role's `file:` task on the target dir runs *before* synchronize, so even if it correctly sets root:root, synchronize overwrites it. Re-running the playbook would produce no change in ownership, not "fix" it back to root:root. The brief's expected `--check` result ("would change to 1000:1000") would not occur — `--check` would in fact report no changes if synchronize sees content identity.
* **Option Z (operator-intent overrode)** — rejected. No bash_history entry, no host_vars override, no ansible run with `-e compose_app_owner=...`. Tom did not change it.

## Recommended fix direction

The host's current state (developer:developer for source files) is **operationally correct** for a developer-owned LXC where the operator wants to edit `/srv/<stack>/docker-compose.yml` without sudo and where the actual privilege boundary is `data/` (root-only) and `.env` (root, 0600). Recommendation: **align the role default to the host reality**, not the other way round.

**Concrete change** (homelab-infra/ansible/roles/compose-app/defaults/main.yml):

```yaml
# OLD
compose_app_owner: root
compose_app_group: root
compose_app_dir_mode: "0750"

# NEW
compose_app_owner: 1000  # developer-uid (matches synchronize behaviour, allows
                         # operator edits to docker-compose.yml without sudo)
compose_app_group: 1000
compose_app_dir_mode: "0755"
```

The `.env` template task already renders with `mode: "0600"` and an explicit owner, so the secret stays root-owned. The `data/` subdir ends up root-owned the moment the container starts (Docker bind-mount creates path as root if the container needs it root). The drift-investigation doc (line 99 onward) reaches the same conclusion.

A second fix, optional, makes the role *deterministic* regardless of caller's controller uid: add `--owner --group --chown=1000:1000` to `rsync_opts` in the synchronize task, OR add an explicit `recurse: yes` `file:` task after synchronize that re-asserts `compose_app_owner`. Either would close the "rsync silently controls ownership" footgun. Recommend the post-synchronize `file:` task — it's clearer in the role's own DSL and survives controller-side uid drift (e.g. running from CI where uid is unpredictable).

### Estimated time to fix

* **Default flip only** (defaults/main.yml + README footnote + commit): 5 minutes.
* **Default flip + post-synchronize chown task + tests update**: 25 minutes.
* **Full re-deploy + smoke test + drift re-scan to verify**: +15 minutes (so 40 minutes total for the deterministic fix).

## Risks

1. **Mode tightening implication**: today the dirs are `0755`. Flipping the role default to `0755` matches reality, but the role's comment ("0750 keeps non-root users out of any vault-derived secrets in `.env`") is a non-sequitur — `.env` has its own 0600 enforcement; the dir mode never protected it. No real risk here, just a doc cleanup.
2. **Other callers of compose-app**: at present only `deploy-context-stack.yml` uses the role. If a future stack genuinely needs root:root (e.g. one without vault secrets but with root-only-readable bind sources), the role default change forces that caller to override. Acceptable — explicit is better.
3. **First deploy vs re-deploy divergence**: the role *currently* writes root:root on first dir creation, then synchronize flips it. A future operator reading the role would expect "first deploy = root:root, never changes". They'd be surprised the second the rsync runs. Aligning the default removes this latent surprise.

## Anything unexpected

* The brief's premise was inverted — operator/parent saw the directories at 1000:1000 and described them as "root:root", or referred to a different read than the live `stat`. Confirmed by `find /srv -maxdepth 2 -printf` and `ls -la /srv/`.
* No `/var/log/auth.log` on this host — Debian 13 LXC ships journald-only auth logs. Used `journalctl` for sudo/sshd correlation, which worked.
* `auditd` is not running; no `ausearch -k chown` data available. Wasn't necessary because journald sudo logs were sufficient.
* `/srv/gitnexus/data` and `/srv/graphiti/data` mode is `0750` not the default `0755` — created by Docker (different containers run as different UIDs: graphiti-mcp = root, falkordb = root, gitnexus = uid 1000 'node'). Their permissions reflect each container's umask on first start, not anything the role did.

## Auxiliary issues surfaced

* **Latent footgun in compose-app role**: `synchronize` without `--archive` or explicit ownership flags lets the controller-side uid leak onto the target. Worth fixing even after the default flip, because it makes the role behave-as-documented instead of behave-as-side-effect.
* **No `/srv` parent ownership documented**: `/srv` itself is `root:root` `0755` (set by docker-host or base LXC template, not by this role). That's fine and expected; just noting it's not the role's concern.
* **Prior drift doc (drift-investigation-evidence.md, A3 entry, line 99)** reached a similar verdict but was less definitive about the cause. This investigation closes that loop with the rsync-non-archive root cause.

## Cross-references

* `homelab-infra/ansible/roles/compose-app/tasks/main.yml` (lines 41–73) — task ordering that produces the current ownership behaviour
* `homelab-infra/ansible/roles/compose-app/defaults/main.yml` (lines 41–43) — the dead-code defaults
* `homelab-playbook/docs/context-stack/sprint-5/drift-investigation-evidence.md` (lines 99–106, 188–194) — prior drift flag that triggered this investigation

---

## A3 Y-COMPLETE FIXED 2026-04-27

Fix landed on `homelab-infra` commit `dab5d02` (branch: main): the
operator-recommended Y-complete path — defaults flip + deterministic
post-rsync chown — implemented and verified in --check on ct-dev-homelab.

### Defaults diff (verbatim)

```diff
--- a/homelab-infra/ansible/roles/compose-app/defaults/main.yml
+++ b/homelab-infra/ansible/roles/compose-app/defaults/main.yml
- # Ownership of the target dir tree. `0750` keeps non-root users out of
- # any vault-derived secrets in `.env`. Override per-stack if a service
- # account is already provisioned on the host.
- compose_app_owner: root
- compose_app_group: root
- compose_app_dir_mode: "0750"
+ # Ownership of the target dir tree.
+ #
+ # Defaults flipped 2026-04-27 from root:root/0750 to 1000:1000/0755
+ # (post-A3 investigation). The previous root-default was masked by the
+ # role's `synchronize` task (rsync without --owner/--group/--chown),
+ # which silently preserved the controller-side uid (typically the
+ # operator, uid 1000) and won over the preceding `file:` task.
+ # ...
+ compose_app_owner: 1000
+ compose_app_group: 1000
+ compose_app_dir_mode: "0755"
```

### New tasks block (verbatim)

The `Ensure data directory exists` task was decoupled from
`compose_app_owner` (Docker owns the bind-mount path):

```yaml
- name: Ensure data directory exists (named-volume mount target)
  # Intentionally NOT declaring owner/group/mode here. The data dir is
  # Docker's territory — its bind-mount semantics set ownership on first
  # container start (root for falkordb/gitnexus, varies per stack), and
  # the role must not race or override that.
  ansible.builtin.file:
    path: "{{ compose_app_data_dir }}"
    state: directory
  tags: [compose-app, compose-app-deploy]
```

Three new tasks were added immediately after `synchronize` to enforce
ownership without recursing into `data/` or `.env`:

```yaml
- name: A3 Y-complete (2026-04-27) — enumerate source-tree paths for ownership pass
  ansible.builtin.find:
    paths: "{{ compose_app_target_dir }}"
    recurse: false
    file_type: any
    excludes:
      - data
      - .env
  register: compose_app_chown_targets
  changed_when: false
  tags: [compose-app, compose-app-deploy]

- name: A3 Y-complete (2026-04-27) — enforce ownership of top-level dir
  ansible.builtin.file:
    path: "{{ compose_app_target_dir }}"
    state: directory
    owner: "{{ compose_app_owner }}"
    group: "{{ compose_app_group }}"
    mode: "{{ compose_app_dir_mode }}"
  tags: [compose-app, compose-app-deploy]

- name: A3 Y-complete (2026-04-27) — enforce ownership of source tree (excl. data/, .env)
  ansible.builtin.file:
    path: "{{ item.path }}"
    owner: "{{ compose_app_owner }}"
    group: "{{ compose_app_group }}"
    recurse: "{{ item.isdir | default(false) }}"
  loop: "{{ compose_app_chown_targets.files | default([]) }}"
  loop_control:
    label: "{{ item.path }}"
  tags: [compose-app, compose-app-deploy]
```

The `.env` template task was hardcoded to `owner: root, group: root`
(was `compose_app_owner`) so the secret boundary holds regardless of
how the role's source-tree owner default is set.

### --check outcome on ct-dev-homelab

```
TASK [compose-app : Ensure target directory exists] ****************************
ok: [ct-dev-homelab]

TASK [compose-app : Ensure data directory exists (named-volume mount target)] ***
ok: [ct-dev-homelab]

TASK [compose-app : Synchronize compose source from controller to target] ******
ok: [ct-dev-homelab]                          # gitnexus: no diff
changed: [ct-dev-homelab]                     # graphiti: timestamp ripple only

TASK [compose-app : A3 Y-complete (2026-04-27) — enumerate source-tree paths for ownership pass] ***
ok: [ct-dev-homelab]

TASK [compose-app : A3 Y-complete (2026-04-27) — enforce ownership of top-level dir] ***
ok: [ct-dev-homelab]

TASK [compose-app : A3 Y-complete (2026-04-27) — enforce ownership of source tree (excl. data/, .env)] ***
ok: [ct-dev-homelab] => (item=/srv/graphiti/docker-compose.yml)
ok: [ct-dev-homelab] => (item=/srv/graphiti/graphiti_mcp_server.py.patched)
ok: [ct-dev-homelab] => (item=/srv/graphiti/Dockerfile)
ok: [ct-dev-homelab] => (item=/srv/graphiti/config-graphiti-mcp.yaml)
ok: [ct-dev-homelab] => (item=/srv/graphiti/scripts)

TASK [compose-app : Render env file from template (if provided)] ***************
ok: [ct-dev-homelab]                          # graphiti: .env already root:root 0600

PLAY RECAP
ct-dev-homelab : ok=26   changed=1   unreachable=0   failed=0   skipped=9   rescued=0   ignored=0
```

The single `changed=1` is the rsync `synchronize` task on graphiti
reporting a timestamp-only `.d..t......` ripple — pre-existing behaviour,
not new with this fix. All ownership-related tasks land at `ok` because
host reality (1000:1000/0755 for source tree, root:root/0750 for data/,
root:root/0600 for .env) now matches role intent on every line.

The earlier --check pass (before the data/ exclusion fix) showed the
recurse pass attempting to chown `/srv/{graphiti,gitnexus}/data` from
0:0/0750 → 1000:1000/0755, which would have broken Docker's bind-mount
ownership on Falkordb. That regression was caught in the first --check
and corrected before the commit.

### Files touched

* `ansible/roles/compose-app/defaults/main.yml` — defaults + comment
* `ansible/roles/compose-app/tasks/main.yml` — data-dir decoupling, three new chown tasks, .env hardcoded to root
* `ansible/roles/compose-app/meta/argument_specs.yml` — typed defaults updated
* `ansible/roles/compose-app/README.md` — variable table + ownership-behaviour section

### Anything unexpected (from the fix run)

* First --check pass surfaced a regression risk: the naive `recurse: yes`
  on `compose_app_target_dir` would have chowned Docker's `data/` bind-mount
  on every run. Caught and corrected by switching to a `find`-based
  enumeration with `excludes: [data, .env]`. The investigation file's
  recommendation ("recurse: yes file: task") was directionally right but
  needed the exclusion guard the operator should be aware of.
* The `.env` template task previously used `{{ compose_app_owner }}` not
  literal `root`. The investigation prose described it as "owner: root"
  which was slightly imprecise. Hardcoding it to `root` in this fix is
  what makes the secret boundary independent of `compose_app_owner` —
  defensive but matches stated intent.

### Closing

Verdict from the original investigation (Option Y) is now actioned:
role is deterministic, host state and role intent agree, and a future
controller running with a different uid (CI runner, root-only deploys)
will produce the same on-disk reality.
