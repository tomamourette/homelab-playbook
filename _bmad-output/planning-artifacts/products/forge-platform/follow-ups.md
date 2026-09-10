---
type: follow-ups
product: forge-platform
created: 2026-09-09
owner: tomamourette
---

# Forge Platform PoC — Follow-ups

Work that was **deliberately not done** during FE1/FE2, recorded so it is deferred rather than
forgotten. Nothing here blocks the PoC verdict (FE4-S04); several items should be closed before the
PoC is treated as a durable service rather than a proof.

**Reading the columns.** *Owner* is who can actually close it — `operator` means no agent can. *Trigger*
is the event that makes it stop being deferrable.

---

## Blocking nothing today, but owed

### 1. Reconcile `hermes.bi-services.be` into Terraform

| | |
|---|---|
| **Owner** | operator (decision) + dev (implementation) |
| **Raised by** | FE2-S05, AC4 Part A |
| **Trigger** | the next time anyone regenerates or lands `pihole-custom.list` |

The live Pi-hole `custom.list` on ct-docker-01 carries a hand-added line,
`192.168.50.194 hermes.bi-services.be`, backing a **running** Traefik router for the Linear → Hermes
webhook. It was never entered into Terraform, so the generated
`terraform/envs/homelab/generated/pihole-custom.list` does not contain it — **landing the generated
file deletes a live integration.** That is why FE2-S05 took the additive dnsmasq route instead and
left `custom.list` untouched.

This is a trap with a fuse, not a static gap: the next person who regenerates that file for an
unrelated reason and lands it without diffing will break the webhook and will not connect the two
events. The fix is to add `hermes` to the Terraform source of truth so the generated file is a
superset of the live one, then diff before landing.

**Related, and worse:** the live file is bind-mounted from the on-host clone at
`/opt/homelab-apps/stacks/dns-pihole/config/`, whose working tree is **dirty — 45 files**. The
`hermes` line is the one that has been identified; it is not necessarily the only divergence. Any
reconciliation should start by diffing that whole clone against its remote, not just this one line.

### 2. `ansible/update-dynamic-configs.yml` — `ct_docker_ip` dereference

| | |
|---|---|
| **Owner** | dev |
| **Raised by** | FE1/FE2 estate work |
| **Trigger** | anyone attempting to run this playbook |

`ansible/update-dynamic-configs.yml:22` sets
`current_docker_ip: "{{ tf_outputs.outputs.ct_docker_ip.value }}"` and was reported **undefined at
runtime**.

**The output itself is not missing** — verified 2026-09-09: `output "ct_docker_ip"` exists at
`terraform/envs/homelab/outputs.tf:189` and `output "ct_media_ip"` at `:195`. So the failure is in
how the deprecated `terraform` Ansible module registers its result, not a gap in the Terraform.

**Look at the whole task before fixing the expression.** The registering task uses
`terraform: project_path=... state: present`, which is the module's **apply** mode. A playbook whose
stated purpose is "update configuration files with current IPs" would, if it ever ran to completion,
**apply Terraform as a side effect** — against NFR-IAC's targeted-plan-then-apply discipline (gate
(j)). The dereference bug is currently the only thing stopping it. Fix both together or neither.

### 3. `dev-host` — "Restart Docker after runc update" is not idempotent

| | |
|---|---|
| **Owner** | dev |
| **Raised by** | FE1-S04 |
| **Trigger** | any idempotency assertion over `dev-host-setup.yml` |

`ansible/roles/dev-host/tasks/main.yml:468`, `Restart Docker after runc update`, reports `changed`
on every run. FE1-S04's converged re-run was `changed=1` and this task is the one. It makes
"`--check --diff` is clean" unassertable for the whole role, so a *real* drift can hide behind the
expected noise. Gate it on the runc install actually having changed.

### 4. Remove the stale SSH key from `terraform.tfvars`

| | |
|---|---|
| **Owner** | **operator** (which key is stale is a judgement only the operator can make) |
| **Raised by** | FE1 substrate work |
| **Trigger** | before the next new container is provisioned |

`terraform/envs/homelab/terraform.tfvars:22-24` sets `ssh_keys` to a **two-element** list, both
labelled `homelab-infra`. Every container Terraform creates gets both. One is believed stale.

An unremoved authorised key on every CT in the estate is a standing access path nobody is tracking.
This is an operator call because removing the wrong one locks the operator out of new containers —
do not let an agent guess.

### 5. Credential rotation — three items

| | |
|---|---|
| **Owner** | **operator only** — no agent can close any of these |
| **Raised by** | FE2-S05 blockers |
| **Trigger** | before the PoC is treated as durable; immediately if any workstation is compromised |

1. **The Proxmox API token** used by Terraform.
2. **`dev_vm_password`** — `terraform/envs/homelab/terraform.tfvars:15`.
3. **The Cloudflare API token** — `vault_cloudflare_api_token`.

Each rotation is two moves: reissue at the source (PVE's API-token UI, Cloudflare's token UI, or a
new password), then update the consumer (`ansible-vault` re-encrypt, or the tfvars entry) and
re-apply.

> **Standing rule for this artifact set:** no document here ever records, prints, or echoes a secret
> value. **Length** is the only property any of these files may state, and lengths are of the
> **unquoted** value — see FE2-S06's dated correction, where `22`/`42` were quoted-literal lengths and
> the real values are **20**/**40** (Cloudflare token **53**).

### 6. The Caddy build URL is not immutable — re-pin on each release

| | |
|---|---|
| **Owner** | dev |
| **Trigger** | every Caddy release, and any `forge-coder-host` apply that fails on a checksum |

`forge_caddy_url` (`forge-coder-host/defaults/main.yml`) is
`https://caddyserver.com/api/download?os=linux&arch=amd64&p=<plugin>` — **the URL carries no
version**. Caddy's build service serves *current* for that plugin set, so the same URL yields a
different binary the day Caddy ships a release.

The `forge_caddy_sha256` pin is what makes this safe, and it does so by **failing**: on the next
release the download stops matching and the role errors out. That is the correct failure mode, but
it is a **scheduled** one — it will fire on an unrelated maintenance day with a checksum-mismatch
message that says nothing about Caddy having released. Treat a checksum failure here as "upstream
released", verify the new build, and re-pin `forge_caddy_version` + `forge_caddy_sha256` **together**.
The same joint-bump rule applies to `coder_version` + `coder_deb_sha256`.

---

## Findings carried, not closed

> **Provenance note added 2026-09-09 — read this before citing an "F" number from this section.**
> These items were raised in a review pass over the live FE1/FE2 deployment on CT 167. **That pass
> left no artifact on disk**: a repo-wide `grep` for a forge-platform findings document defining
> F1–F7 returns nothing, so an `F<n>` label here **cannot be resolved by a reader** — which is the
> same failure mode as the fabricated "ADR-010" citation this product exists to guard against
> (R7, FE2-S05-AC6).
>
> Worse, the labels **collide**. `readiness-check.md` §F is a real, on-disk F-series about something
> else entirely, and every row in it is **PASS**:
>
> | | `readiness-check.md` §F says | this section previously used the same label for |
> |---|---|---|
> | F4 | "The VMID 166 phantom is neutralised before any plan" — PASS | sshd `PerSourcePenalties` |
> | F5 | "The ingress posture cites a document that exists" — PASS | no firewall on CT 167 |
> | F7 | "Backup of the new CT is in scope" — PASS | certificate renewal unmonitored |
>
> A reader chasing "F5" in this product folder lands on a PASS row about citations, not on a
> firewall. **The labels have therefore been dropped from the headings below; the descriptions,
> which were never in doubt, are unchanged.** Where the underlying issue is also tracked somewhere
> resolvable, that pointer is given instead. Do not re-introduce `F<n>` numbering here unless the
> review pass is first written to a file that defines it.

### 7. No firewall on CT 167 (**PoC-accepted**)

CT 167 runs no host firewall. **Accepted for the PoC** and recorded as accepted, not overlooked: the
host has no public inbound, sits behind the estate's Tailscale-first posture
(`wiki/architecture/tailscale-policy.md:20-31`), and serves one operator. It stops being acceptable at
the same trigger as ADR-002's privileged-workspace acceptance — **a second, less-trusted user** — and
should be revisited there rather than on its own schedule.

### 8. Certificate renewal is unmonitored

The Let's Encrypt certificate for `forge.bi-services.be` renews automatically inside Caddy and
**nothing watches whether it did**. The first signal of a failed renewal would be a browser warning,
i.e. the operator discovering it by being blocked. The estate already has the pieces for this —
Prometheus, Alertmanager and the ntfy push channel — so this is wiring, not new infrastructure.

Sharpened by the 2026-09-09 wildcard reversal, and by what that reversal turned out to mean
mechanically: Caddy issues **one certificate per name**, so CT 167 now holds **two independent
certificates** — `forge.bi-services.be` (expires `Dec 8 13:54 UTC`) and `*.forge.bi-services.be`
(expires `Dec 8 16:09 UTC`) — each renewing on its own DNS-01 challenge. **Two certificates is
strictly worse than one two-SAN certificate for this failure mode:** the wildcard can lapse while
the apex renews fine, and the apex is the name the operator opens every day. The first signal would
then be a warning on a preview URL, weeks after the cause.

**Item 5's Cloudflare token rotation is a live way to break renewal silently** — rotate the token
without updating `/etc/caddy/cloudflare.env` and nothing fails until the certificates expire up to 90
days later. Whatever gets wired, it must check **both** names, not just the apex; a probe against
`forge.bi-services.be` alone would have looked green throughout.

### 9. sshd `PerSourcePenalties` locked the Ansible control host out mid-run

During FE2, sshd's `PerSourcePenalties` (on by default in current OpenSSH) blocked the Ansible
control host **192.168.50.156** part-way through a run, after repeated connections from one source
tripped the penalty threshold. The symptom is a run that starts fine and then cannot reconnect — it
looks like a network fault or a hung host, not a deliberate block, so it burns diagnosis time.

Decide the estate-wide answer rather than reacting to it again: exempt the control host, tune the
thresholds, or accept it and reduce connection churn (`ControlMaster`/`ControlPersist`,
`pipelining`). It will recur on the next long play against a fresh host, and it is not specific to
CT 167.

### 10. The nested Docker daemon bypasses lxcfs

Measured on CT 167, 2026-09-09 (FE1-S05). CT 167's own `/proc/meminfo` is lxcfs-masked and reports
`MemTotal: 12582912 kB` (12 GiB, the configured limit). **Inside a container on that host,
`/proc/meminfo` reports `MemTotal: 65446256 kB` — ~62 GiB, the pve3 host's real RAM.** Docker mounts
a fresh `/proc`, so lxcfs's masking does not follow it down.

The cgroup limit is still enforced; only the *advertised* number is wrong. Anything inside a
workspace that sizes itself from `/proc/meminfo` — JVM default heap, Node's old-space heuristics,
build parallelism tuned to "available" memory — will size against **62 GiB** and be **OOM-killed**
long before it reaches that, with a kill that looks unrelated to the sizing that caused it. Same
class as the qBittorrent/libtorrent mmap-vs-cgroup-accounting incident on ct:102.

No fix is proposed for the PoC. The mitigations, when needed, are explicit limits inside the
workspace image (`JAVA_TOOL_OPTIONS -XX:MaxRAMPercentage`, `NODE_OPTIONS --max-old-space-size`,
bounded `-j`) rather than anything at the LXC layer. **Read FE4-S02's gate (h) with this in mind**:
a workspace that OOMs is not necessarily evidence that CT 167 is undersized.

### 11. `tests/acceptance.md` — eight stories are `done` with no per-AC evidence

**Owner:** each story's implementer. **Trigger:** FE4-S02, which reads these rows as its input.

`tests/acceptance.md` §3 was regenerated from the story files on 2026-09-09 and now indexes **141
ACs across 27 stories, none derived**. Its `Status` column tracks **evidence**, not delivery, and
those two currently disagree for eight stories: `FE1-S04`, `FE2-S01`, `FE2-S04`, `FE2-S06`,
`FE3-S01`, `FE3-S03`, `FE3-S04` and `FE3-S05` are `done` in
`implementation-artifacts/sprint-status-forge-platform.yaml` but carry **no per-AC verdict** in their
own files, so all their rows read `pending`.

That is the honest state, not a bug in the index — but it is a real gap, and it is the gap that
matters at FE4-S02: a gate that reads "AC pending" cannot tell "not run" from "run, not written
down". Four stories show what closing it looks like (`FE1-S05`, `FE2-S02`, `FE2-S03`, `FE3-S02` each
carry an AC-by-AC evidence table with real output); the other eight need the same treatment, which is
a transcription job, not re-execution, wherever the work was actually done.

**Smaller, related:** `FE3-S02`'s evidence table records a verdict for an **`AC6`** (`terraform
fmt`/`validate`) that the story never defines — it states AC1–AC5 only. Either add the AC or drop the
row; it is left alone here because it belongs to that story's owner.

### 12. Story frontmatter and the sprint file drifted, and will again

**Owner:** whoever closes a story. **Trigger:** the next status change.

On 2026-09-09, twelve story files still read `status: draft` in their own frontmatter while the sprint
file marked them `done` (`FE0-S01`…`S05`, `FE1-S01`…`S04`, `FE3-S01`/`S03`/`S05`). They were
reconciled **to the sprint file**, which is the authority for delivery state. Six `FE4` + `FE3-S06`
files legitimately still read `draft` because they are `backlog`.

The drift recurs because a story's status lives in two places with no check tying them together. The
check is one line and worth adding to whatever runs at close-out:

```bash
# prints every story whose own frontmatter disagrees with the sprint file
python3 - <<'EOF'
import pathlib, yaml, re
s = yaml.safe_load(open('_bmad-output/implementation-artifacts/sprint-status-forge-platform.yaml'))
st = {re.match(r'^(fe\d-s\d+)', k).group(1).upper(): v
      for k, v in s['development_status'].items() if re.match(r'^fe\d-s\d+', k)}
for p in sorted(pathlib.Path('.../stories').glob('*.md')):
    have = [l for l in p.read_text().split('\n')[:20] if l.startswith('status:')][0].split(':')[1].strip()
    want = st.get(p.name[:7])
    if want in ('done', 'in-progress') and have != want:
        print(p.name, have, '->', want)
EOF
```

---

## Not follow-ups — recorded here so they are not mistaken for open items

- **R5 (double-nested Docker untested) is CLOSED, disproven.** FE1-S05 ran it: it works, and the
  inner daemon's overlayfs came up directly on the ZFS dataset. Nothing is owed.
  **Stale "R5 is untested" prose still exists, and the previous disclosure of it was incomplete.**
  A repo-wide sweep on 2026-09-09 found it in **nine** files, not the three first reported:

  | file | where |
  |---|---|
  | `prd.md` | `:358` risk register row; `:407` §11.2 heading "**UNTESTED** (R5)" |
  | `product-brief.md` | `:205` risk table row |
  | `epics.md` | `:411` traceability row "**[UNTESTED]**" |
  | `README.md` | `:132` |
  | `readiness-check.md` | `:37`, `:97` (G3 "R5 is recorded as **untested**" — PASS), `:161` |
  | `architecture.md` | `:99` inside the ASCII diagram; `:310` AR2 |
  | `adrs/ADR-001` | `:78` §Consequences |
  | `adrs/ADR-003` | `:63`, `:71`, `:94` |
  | `tests/e2e-deployment.md` | `:353` |

  Plus `stories/FE3-S06:172`, a DoD checkbox reading "R5 explicitly noted as still unverified by
  this story (deferred to FE4)" — that one is now false twice over, since FE4 did not run it either;
  FE1-S05 did.

  **Left as-is deliberately, and the reason is unchanged:** R5's disproof does not change either
  ADR's decision — ADR-001 still picks the LXC, ADR-003 still makes gate (g) non-gating — and these
  are risk-register and narrative entries, not gates that anything executes against.
  `stories/FE3-S06` (body), `stories/FE4-S02` and the sprint-status header already carry the dated
  CLOSED/DISPROVEN note. **What changed here is only the honesty of the list:** it was reported as
  "four remaining", and it is twelve locations across nine files. Sweep them as one deliberate pass
  at FE4-S05, or accept them as historical — but decide it from the real list, not the short one.
- **`workspace_privileged` stays `true`.** FE1-S05's `set-privileged-false` recommendation is the
  **available flip** (one value in `poc.variables.yaml`), not pending work. The trigger for taking it
  is ADR-002's: a second, less-trusted user on this host.
- **The Cloudflare token needs no re-scoping for the wildcard.** One `Zone.DNS Edit` grant on
  `bi-services.be` already covers it. FE0-S02's AC3 conclusion survives its own title.
- **The wildcard-reversal sweep is DONE, not owed — and as of 2026-09-09 the claim is finally true.**
  On 2026-09-09 a repo-wide pass annotated every live "wildcard is not required" statement in this
  product folder: the 20 story banners carrying the §5.4 boilerplate, `tests/e2e-deployment.md`, both
  unamended copies of acceptance gate (a) (`prd.md` and `product-brief.md` — these were the ones that
  would have failed the *correct* deployment), `prd.md` §9.1, `epics.md` §2 and its gate (a) copy,
  `README.md` ×2, `product-brief.md` §4, `architecture.md` ×2, and `FE0-S02`'s Background paragraph,
  which contradicted its own AC3 note. `ADR-005`'s frontmatter `title:` was flipped too — the prose
  amendment governs a human reader, but anything indexing frontmatter reads the field. `FE2-S06`'s
  copy sits inside a retained historical quote and was annotated in the surrounding banner (21 lines
  above it) instead of inside the quote.

  **That location list was incomplete, and this entry asserted a clean sweep it had not earned. Three
  residues, all closed 2026-09-09:**
  - **`adrs/ADR-005-dns-01-wildcard-over-public-ingress.md:133`** (now `:139` after the fix) — the
    **Consequences → Positive** bullet, "Keeping wildcard scope optional means the PoC's actual
    certificate need (one fixed hostname, path-proxied code-server) is met…". A live, unstruck,
    unflagged claim, in the one section a reader skims for the decision's upside — and the ADR's own
    amendment at `:22-23` promises that "the paragraphs it reverses are **flagged in place**." The
    Consequences body was never in this list. **Fixed:** original text struck (`~~…~~`), never deleted,
    with an adjacent dated `REVERSED 2026-09-09` note recording the measured state. The
    issuance-rights half of the bullet survives and is called out as surviving: no broader Cloudflare
    grant was requested for the wildcard.
  - **`stories/FE2-S05-caddy-static-block-dns01.md:199-203`** — the AC4-Part-A scope note still called
    the wildcard slice "still open" and instructed the reader to read AC1/AC4 "against the two-SAN
    expectation", flatly contradicting `:88` in the same file. Not caught by the sweep's grep because
    it says "still open", not "optional / not required". **Fixed:** rewritten to the closed state
    (now `:214-227`), with the certificate mechanism and both `notBefore` timestamps.
  - **`tests/acceptance.md:345`** — the §3.1 index row for `FE0-S02 | AC3` echoed that story's
    misleading AC title ("Wildcard scope explicitly not required") with no marker anywhere near it.
    **Fixed 2026-09-09:** the row now carries the dated reversal inline. The AC's conclusion about
    the **token** still stands; only its title was wrong.

  **"Two SANs" is itself a stale framing — do not reintroduce it while sweeping.** The correct
  deployment is **two separate single-SAN Let's Encrypt certificates**, one per subject (apex
  `notBefore Sep 9 13:54:39 2026 GMT`, never reissued; wildcard `notBefore Sep 9 16:09:35 2026 GMT`),
  because Caddy/CertMagic manages **one certificate per subject** — a single dual-SAN *managed*
  certificate is not obtainable for a two-name site block without dropping to static certs. Any check
  written as "the certificate carries two SANs" **fails a fully correct host**. The invariant is
  **"every SNI name presents a browser-trusted certificate covering that name."**

  **Verification.** The old one-liner (`grep -rn "ildcard" …`) emitted dozens of lines (61 on
  2026-09-09, before this entry itself grew) and left the adjudication to a human, which is exactly
  how `ADR-005:133` survived it. Replaced by a mechanical
  check: every line that still states the wildcard is optional / not required / not asserted must
  carry a **dated 2026-09-09 reversal marker within ±8 lines**. Two structural exceptions are excluded
  by content, not by line number, and each is annotated elsewhere on purpose: nested-quote lines
  (`> >` — `FE2-S06`'s byte-for-byte-intact historical quote, flagged in its banner at `:38`) and the
  amendment's own recital line `**What was decided (original):**` (`ADR-005:25`, inside the blockquote
  whose heading at `:17` is "AMENDMENT — DECISION REVERSED 2026-09-09"). Run from
  `products/forge-platform/`:

  ```bash
  T=$(mktemp)
  grep -rn "ildcard" *.md stories/ adrs/ tests/ \
  | grep -iE "optional|not required|not asserted" \
  | grep -v ':> >' \
  | grep -v 'What was decided (original)' \
  | while IFS=: read -r f n rest; do
      w=$(awk -v n="$n" 'NR>=n-8 && NR<=n+8' "$f")
      if printf '%s' "$w" | grep -q '2026-09-09' \
         && printf '%s' "$w" | grep -qiE 'REVERS|amended|corrected|no longer|is dead'; then
        echo "FLAGGED"
      else
        echo "UNFLAGGED $f:$n:$rest"
      fi
    done > "$T"
  echo "candidate lines : $(wc -l < "$T")"
  echo "dated-flagged   : $(grep -c '^FLAGGED' "$T")"
  echo "UNFLAGGED       : $(grep -c '^UNFLAGGED' "$T")"
  grep '^UNFLAGGED' "$T"; rm -f "$T"
  ```

  **Real output, run 2026-09-09 after the three fixes above and after this entry was rewritten
  (the entry's own prose and transcripts are themselves candidate lines, and are dated-flagged in
  place — which is why the total is 64 rather than the 59 of the scratch run below):**

  ```
  candidate lines : 64
  dated-flagged   : 64
  UNFLAGGED       : 0
  ```

  **This check has teeth — measured, not assumed.** Re-run on 2026-09-09 against a scratch copy of
  this folder with the `ADR-005:133` and `tests/acceptance.md:345` fixes reversed out, it prints
  exactly the two offenders (and nothing else), which is why the "REVERSED" wording below is a
  transcript of a deliberately broken tree, not a live claim:

  ```
  # scratch copy taken 2026-09-09 BEFORE this entry was rewritten, then the two fixes reversed out;
  # that is why the candidate total is 59 here and higher in the clean run above (this entry's own
  # prose and transcripts are themselves candidate lines, and are dated-flagged in place).
  candidate lines : 59
  dated-flagged   : 57
  UNFLAGGED       : 2
  UNFLAGGED adrs/ADR-005-dns-01-wildcard-over-public-ingress.md:139:- Keeping wildcard scope optional means the PoC's actual certificate need (one fixed hostname,
  UNFLAGGED tests/acceptance.md:345:| FE0-S02 | AC3 | Wildcard scope explicitly not required | FR-PRE-002 | a | pending |
  ```

  The companion check for the "still open" phrasing that the wildcard grep cannot see:
  `grep -rn "still open" stories/*.md` — returns nothing wildcard-related.
- **The `fqdn_dns_records` no-wildcard rule SURVIVES the reversal — do not sweep it.** `prd.md`
  FR-SUB-003, `epics.md`, `FE1-S01-AC4`, `FE2-S05-AC5` and `architecture.md` §4.4 all still say a
  wildcard must never enter `fqdn_dns_records`. That is correct and unrelated: the map renders
  hosts-format lines and dnsmasq rejects `*` there, so a `*` produces a broken file, not a wildcard
  answer. The wildcard is served publicly from the Cloudflare map and internally from the additive
  dnsmasq `address=` drop-in.
