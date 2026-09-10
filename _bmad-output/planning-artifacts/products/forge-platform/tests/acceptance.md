---
type: acceptance-tests
product: forge-platform
version: 1.0.0-draft
status: draft
date: 2026-09-09
prd_ref: ../prd.md
epics_ref: ../epics.md
proposal_ref: ../../../sprint-change-proposal-2026-09-09.md
total_stories: 27
total_acceptance_criteria: 141
---

# Forge Platform PoC — Acceptance Test Suite

## 1. Overview

This document aggregates the acceptance criteria (ACs) authored across the 27 stories of the Forge
Platform PoC (`stories/FE0-S*.md` … `FE4-S*.md`), maps them to the eleven PoC gates from §5.3 of the
sprint change proposal, and audits FR coverage against the frozen `FR-PRE/SUB/CTL/WS/KIT` list.

**Status caveat — RESOLVED 2026-09-09. There are no derived ACs left.** At the time this document
was authored, `FE1-S04`, `FE1-S05`, `FE2-S06` and all six of `FE3-S01`…`FE3-S06` were not yet on
disk, so their AC counts and content were **derived from §4.2 and the canon FR list, not read from
the story files**, and were marked `[derived — pending authoring]`. **All nine are now on disk, and
§3 and §1.1 have been regenerated mechanically from the real files** — every row in §3 is now read
from a story file, so the derived column is zero everywhere.

**Why this was regenerated rather than patched.** The previous partial regeneration (`FE1-S05` only)
left §1.1 carrying a stale summand: it reported FE2 at 25 authored ACs when the §3.3 rows it
summarised already totalled 26, because `FE2-S05` has six ACs and the summary still counted five.
A summary that is hand-edited alongside the rows it summarises will drift again, so §1.1 is now
**derived from the §3 rows**, and the regeneration is reproducible:

```
# 141 across 27 stories, matching §1.1 exactly
grep -cE '^\*\*AC[0-9]+ — ' stories/*.md          # per story, from the story files
grep -oE '^\| *FE[0-9]-S[0-9]+[^|]*\| *AC[0-9]+' tests/acceptance.md | wc -l   # 141, from §3
```

Run both after any AC is added or removed; if they disagree, §1.1 is stale.

### 1.1 Counts

| Epic | Stories | ACs (authored, read from disk) | ACs (derived, pending) | Total |
|---|---|---|---|---|
| **FE0 Prerequisites and truth** | 5 | 22 | 0 | 22 |
| **FE1 Substrate (CT 167)** | 5 | 26 | 0 | 26 |
| **FE2 Control plane** | 6 | 31 | 0 | 31 |
| **FE3 Workspace template** | 6 | 30 | 0 | 30 |
| **FE4 Toolkit and acceptance** | 5 | 32 | 0 | 32 |
| **Total** | **27** | **141** | **0** | **141** |

> **Regenerated 2026-09-09, second pass — full, not partial.** The counts moved
> **132 → 141** and the derived column went **32 → 0**. What changed, per epic, and why:
>
> | Epic | was | now | cause |
> |---|---|---|---|
> | FE0 | 22 | 22 | unchanged |
> | FE1 | 25 (21 + 4 derived) | 26 | `FE1-S04` re-derived from disk: it has **5** ACs, not the 4 guessed |
> | FE2 | 29 (25 + 4 derived) | 31 | `FE2-S06` re-derived: **5** ACs, not 4; **and** the FE2 authored summand was already wrong before that — `FE2-S05` has six ACs and §1.1 counted five |
> | FE3 | 24 (0 + 24 derived) | 30 | all six stories re-derived from disk: **5** ACs each, not the 4 guessed |
> | FE4 | 32 | 32 | unchanged |
>
> **Every derived guess undercounted by exactly one AC per story.** That is not a coincidence worth
> ignoring: the derivation was built from the FR list, and the stories consistently carry one more AC
> than the FRs imply — usually an idempotence, "not forked", or "recorded honestly" criterion that no
> FR states. Treat any future derived count as a **lower bound**, never an estimate.
>
> **What did NOT change: story-level `done` is not AC-level `pass`.** Several stories are `done` in
> `implementation-artifacts/sprint-status-forge-platform.yaml` while their rows here stay `pending`.
> That is deliberate, per the §3 legend: `pass` requires that specific AC's execution to be recorded
> with output in the story's own file. `FE1-S05`, `FE2-S02`, `FE2-S03` and `FE3-S02` carry per-AC
> evidence tables and are marked accordingly; `FE1-S04`, `FE2-S01`, `FE2-S04`, `FE2-S06`,
> `FE3-S01`, `FE3-S03`, `FE3-S04` and `FE3-S05` are `done` in the sprint file but carry no per-AC
> verdict, so their rows stay `pending`. **Reading those `pending` rows as "not delivered" would be
> wrong; reading them as "verified" would be worse.** Closing that gap is owed work, tracked in
> [`../follow-ups.md`](../follow-ups.md).
>
> One inconsistency found while regenerating and **not** silently fixed: `FE3-S02`'s evidence table
> records a verdict for an **`AC6`** (`terraform fmt`/`validate`) that the story never defines — it
> states AC1–AC5 only. The row is absent here because there is no AC to hang it on. That belongs to
> `FE3-S02`'s owner, not to this document.

### 1.2 Definition of "observable" (the gating standard)

An AC is observable iff at least one of:

- **cmd** — a runnable command with a checkable exit code, stdout pattern, or measured value
  (`terraform plan`, `coder ssh ... 'command'`, `ha-manager status`, `free -g`, `stat -c%s`)
- **filesystem** — `test -f` / `test -d` / `ls` / `stat` against a concrete path
- **api** — an HTTP/TLS check (`curl -vI`, a browser certificate inspection)
- **git** — `git diff`, `git status --porcelain`, `git log` against repo state
- **infra** — Proxmox/Coder/PBS process or resource state (`ha-manager`, `pvesr`,
  `proxmox-backup-client`, `coder templates list`, `coder mcp`-equivalent checks)
- **log** — a grep/pattern match against a captured build or command log

ACs lacking any of the above are flagged in §5.

### 1.3 Test execution model

**From a tailnet client that is genuinely NOT on the LAN**, per §5.3's explicit instruction — this
is the standing requirement for all eleven gates (a)–(k), not a preference. FE0's two operator
stories (FE0-S01, FE0-S02) are inherently local (credential minting); FE1–FE3 are mostly
IaC-verification (`terraform`, `ansible`, filesystem/log checks) run from wherever the operator's
IaC tooling lives; FE4 is entirely tailnet-client-driven per its stories' Implementation Notes.
No CI runner is used anywhere in this suite — GitHub-hosted runners have no LAN route to Proxmox
(§3.4), and CI wiring is explicitly out of PoC scope.

---

## 2. The eleven PoC gates (a)–(k)

Each gate below: statement, concrete command, expected result, producing story, FR/ADR binding, and
gating status.

### Gate (a) — Browser-trusted certificate ~~, no wildcard SAN~~ **on both SANs** (amended 2026-09-09)

- **Statement:** Coder's web UI and code-server open over a browser-trusted certificate with no
  warning, from a tailnet client not on the LAN.
- **Command:** `curl -vI https://forge.bi-services.be` (inspect the TLS handshake) and a manual
  browser open of the `coder_app "code_server"` URL, from the tailnet client. **Added 2026-09-09:**
  and a browser open of a **preview URL** under `*.forge.bi-services.be`.
- **Expected:** No certificate warning; issuer is Let's Encrypt (or configured ACME CA) via DNS-01;
  ~~no wildcard SAN present~~ ~~exactly two SANs present~~ **both `forge.bi-services.be` and an
  arbitrary name under `*.forge.bi-services.be` present a browser-trusted certificate — `curl`
  reports `ssl_verify=0` for each, with no `-k`. Do NOT count SANs (see the second correction
  below).**
- **Produced by:** `FE0-S02` (token), `FE2-S05` (Caddy static block + DNS-01), verified end-to-end
  in `FE4-S02-AC1`.
- **FR/ADR:** FR-PRE-002, FR-CTL-005; ADR-005 **as amended 2026-09-09**.
- **Gating:** **Gating.**

> **Amended 2026-09-09 — the "no wildcard SAN" expectation is REVERSED.** As originally written this
> gate would have **failed the correct configuration**. Coder's preview URLs are subdomain-based
> (`agentic-ai/scripts/forge-preview-url`) and `CODER_WILDCARD_ACCESS_URL=*.forge.bi-services.be` is
> set on CT 167, so the PoC serves the wildcard. **Serving only the apex is a FAIL.**
> Struck text is left in place as the record. See ADR-005's amendment and FE2-S05's Background note.
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
> **Unchanged by this amendment:** a wildcard still must never enter Terraform's `fqdn_dns_records`
> (dnsmasq rejects `*` in that hosts-format map). `FE1-S01-AC4` and `FE2-S05-AC5` stand as written.

### Gate (b) — agentic-ai lands via GitHub token; no double clone

- **Statement:** `~/workspace/repos/github/` contains ≥1 repo cloned via
  `coder external-auth access-token github`, and `company-overlay` does not exist there.
- **Command:** `ls ~/workspace/repos/github/`; `test -d ~/workspace/repos/github/company-overlay; echo $?`
- **Expected:** ≥1 repo present (at least `agentic-ai`); second command returns `1`.
- **Produced by:** `FE0-S01` (grant), `FE2-S04` (external-auth provider config), `FE3-S02`
  (`local.repo_deny` fix), `FE3-S03` (parameterised `forge-sync.sh`), verified in
  `FE4-S01-AC2` and `FE4-S02-AC2`.
- **FR/ADR:** FR-PRE-001, FR-CTL-004, FR-CTL-007, FR-WS-004, FR-WS-005; none.
- **Gating:** **Gating.**

### Gate (c) — Toolchain lists tools; both API keys unset

- **Statement:** `~/.forge-toolchain` lists claude, codex, gh, terraform, and reports both provider
  API keys unset (subscription-auth path intact).
- **Command:** `cat ~/.forge-toolchain`
- **Expected:** All four tools listed; both keys reported unset.
- **Produced by:** Workspace image build (FE3, no single story owns this file's content in the
  frozen FR list — it ships with the template); verified in `FE4-S01-AC6` and `FE4-S02-AC3`.
- **FR/ADR:** FR-KIT-001 (verification only); none.
- **Gating:** **Gating.**

### Gate (d) — Skill count and settings registrations

- **Statement:** `ls ~/.claude/skills | wc -l` ≥ 200; `~/.claude/settings.json` has 2 global
  registrations; the resolved project root's `.claude/settings.json` has 18 (restated per C1).
- **Command:** `ls ~/.claude/skills | wc -l`; inspect both `settings.json` files.
- **Expected:** ≥200; 2; 18.
- **Produced by:** agentic-ai content landing via gate (b)'s clone; verified in `FE4-S02-AC4`.
- **FR/ADR:** FR-KIT-001, FR-KIT-002 (verification only); none.
- **Gating:** **Gating.**

### Gate (e) — `claude` starts under subscription OAuth

- **Statement:** `claude` starts and answers one prompt under subscription OAuth. The actual
  product value the PoC exists to test.
- **Command:** `claude` (interactive) or `claude -p "..."` inside the workspace.
- **Expected:** Answers without prompting for an API key.
- **Produced by:** Verified in `FE4-S01-AC6` and `FE4-S02-AC5`.
- **FR/ADR:** FR-KIT-001 (verification only); none.
- **Gating:** **Gating — the single most consequential gate per FE4-S04's verdict framework.**

### Gate (f) — Empty-file-means-disabled contract, end to end

- **Statement:** `~/.config/forge/openmemory.env` and `langfuse.env` are both zero-byte; the build
  log contains both "skipped" lines; `sudo -n true` succeeds.
- **Command:** `stat -c%s ~/.config/forge/openmemory.env ~/.config/forge/langfuse.env`; grep the
  build log; `sudo -n true; echo $?`.
- **Expected:** Both files `0` bytes; two "skipped" log lines; exit `0`.
- **Produced by:** `FE2-S03` (six empty 0600 files, mnemosyne pair absent), verified in
  `FE4-S02-AC6`.
- **FR/ADR:** FR-CTL-003; ADR-006.
- **Gating:** **Gating.**

### Gate (g) — Nested Docker inside the workspace (NON-GATING)

- **Statement:** `docker run --rm hello-world` succeeds inside the workspace. Recorded either way.
- **Command:** `docker run --rm hello-world` inside the workspace.
- **Expected:** Recorded regardless of pass/fail.
- **Produced by:** `FE2-S06` (daemon.json time-namespace fix +
  Docker pin, mitigating R2), verified in `FE4-S02-AC7`.
- **FR/ADR:** FR-CTL-006, FR-KIT-003; **ADR-003 (non-gating)**.
- **Gating:** **Explicitly NON-GATING.** Recorded either way per FR-KIT-003 / ADR-003; a failure
  here cannot, by itself, force a DOES-NOT-PORT call in `FE4-S04`.

### Gate (h) — pve3 capacity headroom; CT 167 not swap-thrashing

- **Statement:** `free -g` on pve3 shows headroom with the workspace running; CT 167 is not
  swap-thrashing. The R4 sizing conflict, measured.
- **Command:** `free -g` on pve3; `swapon --show` / `vmstat 1 5` on CT 167.
- **Expected:** Headroom present; swap-thrashing state stated explicitly either way.
- **Produced by:** `FE1-S01` (`swap_mb` set explicitly, FR-SUB-002), `FE3-S01` (four real
  `variable`s driving `coder_parameter` defaults and maxima, FR-WS-002), measured in `FE4-S01-AC3`
  and `FE4-S02-AC8`.
- **FR/ADR:** FR-SUB-002, FR-WS-002; none (R4 is explicitly unresolved — see HARD RULE 2 in canon).
- **Gating:** **Gating**, but the "pass" bar is deliberately soft — R4 is measured, not resolved, by
  this suite; `FE4-S04`'s decision framework treats a narrowly-scoped, workaround-compatible
  swap-thrash as caveat-worthy rather than an automatic DOES-NOT-PORT.

### Gate (i) — Wall-clock create-to-reachable baseline

- **Statement:** Wall-clock create → code-server-reachable is recorded. Baseline for future
  optimisation, no target time asserted.
- **Command:** Timestamp `T0` at `coder create`, `T1` at first successful code-server response;
  report `T1 − T0`.
- **Expected:** A number is recorded, whatever it is.
- **Produced by:** `FE4-S01-AC5`, copied forward in `FE4-S02-AC9`.
- **FR/ADR:** FR-KIT-001 (verification only); none.
- **Gating:** **Non-blocking measurement gate** — always "passes" by having a number recorded; there
  is no numeric threshold in scope.

### Gate (j) — `terraform plan` clean apart from CT 167; no phantom recreation

- **Statement:** `terraform plan` on the homelab root is clean apart from the intended CT; the
  `ct_sparkle_vlabel` phantom has not been recreated.
- **Command:** `terraform plan -target=module.ct_forge_01 -target=<the two outputs.tf locals>`
  against the homelab root.
- **Expected:** No changes beyond the FE1 apply; no `module.ct_sparkle_vlabel` resource shown.
- **Produced by:** `FE0-S05` (phantom stashed/resolved), `FE1-S01` (module block + outputs),
  `FE1-S02` (targeted plan/apply), verified in `FE4-S02-AC10`.
- **FR/ADR:** FR-PRE-006, FR-SUB-001, FR-SUB-003, FR-SUB-004; NFR-IAC-002.
- **Gating:** **Gating.**

### Gate (k) — HA state and both replication jobs present

- **Statement:** `ha-manager status` shows `ct:167 (pve3, <state>)` and `/etc/pve/replication.cfg`
  has both `167-0` and `167-1`. The ct:151 lesson.
- **Command:** `ha-manager status | grep ct:167`; `grep -A2 '^167-' /etc/pve/replication.cfg`.
- **Expected:** `ct:167` present on `pve3` in the FE1-S03-recorded state (`started` or `stopped`);
  both replication jobs present.
- **Produced by:** `FE1-S03` (replication jobs + rule membership via the Ansible roles only),
  verified in `FE4-S02-AC11`.
- **FR/ADR:** FR-SUB-005; NFR-IAC-001.
- **Gating:** **Gating.**

---

## 3. AC index by epic

**Every row below is read from a story file on disk.** The `[derived — pending authoring]`
placeholders are gone (regenerated 2026-09-09 — see §1.1); if a row ever reappears without a story
behind it, it is a bug in this document, not a pending story.

**Status legend.**

- `pending` — not yet executed, **or** executed as part of a story now marked `done` but with no
  per-AC verdict recorded in that story's file. This column tracks **evidence**, not delivery; the
  delivery state lives in `implementation-artifacts/sprint-status-forge-platform.yaml` and the two
  are deliberately allowed to differ. See the note under §1.1.
- `pass` — that specific AC's execution is recorded, with output, in the story's own evidence
  section. True today for `FE1-S05` AC1–AC6, `FE2-S02` AC1–AC5, `FE2-S03` AC1–AC5, and `FE3-S02`
  AC1–AC3/AC5.
- `partial` — executed, but one sub-check could not be run here and is deferred to a named later
  story. Used once: `FE3-S02` AC4, whose live double-clone check is deferred to `FE4-S01`; its
  offline simulation passed and the pre-change simulation failed, so the change is evidenced but the
  end-to-end path is not.

**Gate column.** A bare letter is the story's own `gate_refs` frontmatter. A letter **in
parentheses**, e.g. `(g)`, is inferred from the AC text where the story declares no `gate_refs` —
informative, not a claim the story made.

### 3.1 FE0 — Prerequisites and truth

| Story | AC | One-line description | FR | Gate | Status |
|---|---|---|---|---|---|
| FE0-S01 | AC1 | OAuth App created | FR-PRE-001 | b | pending |
| FE0-S01 | AC2 | All four credential values recorded | FR-PRE-001 | b | pending |
| FE0-S01 | AC3 | Grant covers `tomamourette/agentic-ai` | FR-PRE-001 | b | pending |
| FE0-S01 | AC4 | Values staged for FE2-S04, not yet deployed | FR-PRE-001 | — | pending |
| FE0-S01 | AC5 | `optional = true` recommended alongside (FR-PRE-003) | FR-PRE-003 | — | pending |
| FE0-S02 | AC1 | Token minted, least-privilege scope | FR-PRE-002 | a | pending |
| FE0-S02 | AC2 | Token verified functional and scoped | FR-PRE-002 | a | pending |
| FE0-S02 | AC3 | Wildcard scope explicitly not required *(the story's own AC title; **REVERSED 2026-09-09** — a wildcard IS served. The AC's conclusion about the **token** survives: one `Zone.DNS Edit` grant covers both names.)* | FR-PRE-002 | a | pending |
| FE0-S02 | AC4 | Token staged for FE2-S05, not yet deployed | FR-PRE-002 | — | pending |
| FE0-S02 | AC5 | No "ADR-010" citation anywhere near this story | FR-PRE-002 | — | pending |
| FE0-S03 | AC1 | Ref pinned to an immutable tag, not a branch | FR-PRE-004 | — | pending |
| FE0-S03 | AC2 | `terraform validate` still passes | FR-PRE-004 | — | pending |
| FE0-S03 | AC3 | Value is a plain string literal, not a `coder_parameter` | FR-PRE-004 | — | pending |
| FE0-S04 | AC1 | `main.tf:399-404` corrected | FR-PRE-005 | — | pending |
| FE0-S04 | AC2 | `main.tf:559-566` rationale corrected | FR-PRE-005 | — | pending |
| FE0-S04 | AC3 | `docs/coder/setup.md:149-156` corrected | FR-PRE-005 | — | pending |
| FE0-S04 | AC4 | `docs/coder/orchestration-adr.md` sysbox mentions corrected | FR-PRE-005 | — | pending |
| FE0-S04 | AC5 | `workspace/Dockerfile` corrected | FR-PRE-005 | — | pending |
| FE0-S05 | AC1 | Phantom block re-confirmed via `git diff` | FR-PRE-006 | j | pending |
| FE0-S05 | AC2 | Fate decided and recorded (operator call) | FR-PRE-006 | j | pending |
| FE0-S05 | AC3 | VMID 167 confirmed as next free slot | FR-PRE-006 | j | pending |
| FE0-S05 | AC4 | `terraform plan` does not touch `ct_sparkle_vlabel` | FR-PRE-006 | j | pending |

### 3.2 FE1 — Substrate (CT 167)

| Story | AC | One-line description | FR | Gate | Status |
|---|---|---|---|---|---|
| FE1-S01 | AC1 | `module "ct_forge_01"` matches runbook pattern | FR-SUB-001 | j | pending |
| FE1-S01 | AC2 | `swap_mb` set explicitly | FR-SUB-002 | h | pending |
| FE1-S01 | AC3 | `outputs.tf` registrations | FR-SUB-003 | j | pending |
| FE1-S01 | AC4 | No wildcard entry introduced | FR-SUB-003 | j | pending |
| FE1-S01 | AC5 | `terraform fmt`/`validate` clean | FR-SUB-001 | — | pending |
| FE1-S02 | AC1 | Plan targets exactly the expected resources | FR-SUB-004 | j | pending |
| FE1-S02 | AC2 | No unrelated drift in the plan | FR-SUB-004 | j | pending |
| FE1-S02 | AC3 | Pre-apply Debian 13 template caching check | FR-SUB-004 | — | pending |
| FE1-S02 | AC4 | Apply succeeds, CT 167 reachable | FR-SUB-004 | — | pending |
| FE1-S02 | AC5 | Config sanity check post-create | FR-SUB-004 | — | pending |
| FE1-S03 | AC1 | Two replication jobs via role defaults | FR-SUB-005 | k | pending |
| FE1-S03 | AC2 | `standard` rule membership via role defaults | FR-SUB-005 | k | pending |
| FE1-S03 | AC3 | `started`/`stopped` recorded as open operator decision (R6) | FR-SUB-005 | k | pending |
| FE1-S03 | AC4 | Both playbooks applied idempotently | FR-SUB-005 | — | pending |
| FE1-S03 | AC5 | HA pickup verified (gate k precondition) | FR-SUB-005 | k | pending |
| FE1-S04 | AC1 | Inventory entry added | FR-SUB-006 | — | pending |
| FE1-S04 | AC2 | `host_vars/ct-forge-01/main.yml` created with `project_name` | FR-SUB-006 | — | pending |
| FE1-S04 | AC3 | SSH key gap check before Ansible (runbook §5) | FR-SUB-006 | — | pending |
| FE1-S04 | AC4 | `dev-host-setup.yml` completes successfully | FR-SUB-006 | — | pending |
| FE1-S04 | AC5 | Toolchain present post-provisioning | FR-SUB-006 | — | pending |
| FE1-S05 | AC1 | Privileged container launched on CT 167 | FR-SUB-007 | — | pass |
| FE1-S05 | AC2 | `CapEff` measured — `000001ffffffffff`, full set, matches E2 | FR-SUB-007 | — | pass |
| FE1-S05 | AC3 | Host uid 0 mapping checked — `uid_map` `0 100000 65536`, host uid 0 unmapped | FR-SUB-007 | — | pass |
| FE1-S05 | AC4 | Host block-device visibility checked — none visible | FR-SUB-007 | — | pass |
| FE1-S05 | AC5 | `modprobe` behaviour checked — fails, by `ENOENT` (no `/lib/modules`), **not** `EPERM` | FR-SUB-007 | — | pass |
| FE1-S05 | AC6 | Verdict recorded: confirms E2 unchanged, ADR-002 `[I]` → `[V]` | FR-SUB-007 | — | pass |

### 3.3 FE2 — Control plane

| Story | AC | One-line description | FR | Gate | Status |
|---|---|---|---|---|---|
| FE2-S01 | AC1 | Role exists with the standard shape | FR-CTL-001 | — | pending |
| FE2-S01 | AC2 | Pinned version, no `latest` | FR-CTL-001 | — | pending |
| FE2-S01 | AC3 | Checksum verified before install | FR-CTL-001 | — | pending |
| FE2-S01 | AC4 | Idempotent apply | FR-CTL-001 | — | pending |
| FE2-S01 | AC5 | Service present but not yet standalone-configured | FR-CTL-001 | — | pending |
| FE2-S02 | AC1 | Postgres 16 from the Debian repository | FR-CTL-002 | — | pass |
| FE2-S02 | AC2 | Dedicated role and database | FR-CTL-002 | — | pass |
| FE2-S02 | AC3 | Password authentication, not peer/trust | FR-CTL-002 | — | pass |
| FE2-S02 | AC4 | No extensions installed | FR-CTL-002 | — | pass |
| FE2-S02 | AC5 | Connection string derivable, not yet wired | FR-CTL-002 | — | pass |
| FE2-S03 | AC1 | Directory exists at 0700 | FR-CTL-003 | f | pass |
| FE2-S03 | AC2 | Exactly six files, each empty, mode 0600 | FR-CTL-003 | f | pass |
| FE2-S03 | AC3 | Mnemosyne pair explicitly absent | FR-CTL-003 | f | pass |
| FE2-S03 | AC4 | Idempotent and non-destructive | FR-CTL-003 | — | pass |
| FE2-S03 | AC5 | Feeds gate (f) end to end | FR-CTL-003 | f | pass |
| FE2-S04 | AC1 | File exists, correct permissions | FR-CTL-004 | b | pending |
| FE2-S04 | AC2 | OIDC block absent | FR-CTL-004 | — | pending |
| FE2-S04 | AC3 | Password auth enabled | FR-CTL-004 | — | pending |
| FE2-S04 | AC4 | Exactly one external-auth provider, GitHub, populated | FR-CTL-007 | b | pending |
| FE2-S04 | AC5 | coderd starts and reaches the database | FR-CTL-004 | — | pending |
| FE2-S05 | AC1 | Static site block, no on-demand TLS | FR-CTL-005 | a | pending |
| FE2-S05 | AC2 | DNS-01 via `caddy-dns/cloudflare` | FR-CTL-005 | a | pending |
| FE2-S05 | AC3 | Token via 0600 root-owned systemd EnvironmentFile | FR-CTL-005 | a | pending |
| FE2-S05 | AC4 | Certificate issues and is browser-trusted | FR-CTL-005 | a | pending |
| FE2-S05 | AC5 | No wildcard in the Terraform-managed DNS map | FR-CTL-005 | — | pending |
| FE2-S05 | AC6 | Correct citation, never "ADR-010" | FR-CTL-005 | — | pending |
| FE2-S06 | AC1 | daemon.json carries the flag | FR-CTL-006 | (g) | pending |
| FE2-S06 | AC2 | Docker package is version-pinned | FR-CTL-006 | (g) | pending |
| FE2-S06 | AC3 | Daemon restarts cleanly with the new config *and the flag demonstrably takes effect* | FR-CTL-006 | (g) | pending |
| FE2-S06 | AC4 | Verified against the actual installed version, not assumed | FR-CTL-006 | — | pending |
| FE2-S06 | AC5 | Existing privileged workspace containers unaffected | FR-CTL-006 | — | pending |

### 3.4 FE3 — Workspace template

| Story | AC | One-line description | FR | Gate | Status |
|---|---|---|---|---|---|
| FE3-S01 | AC1 | `local.image` sources from a local build, no registry reference remains as the default | FR-WS-001 | — | pending |
| FE3-S01 | AC2 | Four new `variable` blocks exist, each feeding one `coder_parameter`'s default and max | FR-WS-002 | h | pending |
| FE3-S01 | AC3 | Defaults left conservative, not pre-resolving R4 | FR-WS-002 | h | pending |
| FE3-S01 | AC4 | `main.tf` not forked | FR-WS-009 | — | pending |
| FE3-S01 | AC5 | `terraform plan` in the template directory is clean | FR-WS-001, FR-WS-002 | — | pending |
| FE3-S02 | AC1 | CLAUDE.md heredoc genericized | FR-WS-003 | — | pass |
| FE3-S02 | AC2 | repos/INDEX.md heredoc genericized | FR-WS-003 | — | pass |
| FE3-S02 | AC3 | `company-overlay` added to the deny list | FR-WS-004 | b | pass |
| FE3-S02 | AC4 | Double-clone eliminated (feeds gate b) | FR-WS-004 | b | partial |
| FE3-S02 | AC5 | No behavior change to the sync mechanism itself | FR-WS-003 | — | pass |
| FE3-S03 | AC1 | Confirm existing parameterisation is genuinely wired, not just present | FR-WS-005 | — | pending |
| FE3-S03 | AC2 | ADO org name has no hardcoded literal outside the `ADO_ORG` variable | FR-WS-005 | — | pending |
| FE3-S03 | AC3 | Per-repo failure messages preserved verbatim | FR-WS-005 | — | pending |
| FE3-S03 | AC4 | Per-repo flags preserved | FR-WS-005 | — | pending |
| FE3-S03 | AC5 | Idempotent, no behavior change for the current Saply deployment | FR-WS-005 | — | pending |
| FE3-S04 | AC1 | `az account show` gated on binary presence | FR-WS-006 | — | pending |
| FE3-S04 | AC2 | Existing behavior preserved when `az` is present | FR-WS-006 | — | pending |
| FE3-S04 | AC3 | Step 3b confirmed self-skipping, no code change required unless a gap is found | FR-WS-006 | — | pending |
| FE3-S04 | AC4 | Step 3 (ADO external-auth check) confirmed non-`az`-dependent | FR-WS-006 | — | pending |
| FE3-S04 | AC5 | Line reference corrected and recorded | FR-WS-006 | — | pending |
| FE3-S05 | AC1 | Trade-off stated accurately for the operator to decide | FR-WS-007 | — | pending |
| FE3-S05 | AC2 | `terraform validate` passes once a decision is implemented | FR-WS-007 | — | pending |
| FE3-S05 | AC3 | Decision recorded, not silently implied by the diff | FR-WS-007 | — | pending |
| FE3-S05 | AC4 | If REMOVE, no dangling references | FR-WS-007 | — | pending |
| FE3-S05 | AC5 | If KEEP, egress dependency documented where FE4-S02 will look for it | FR-WS-007 | — | pending |
| FE3-S06 | AC1 | forge-platform PoC branch present on CT 167 | FR-WS-008 | — | pending |
| FE3-S06 | AC2 | Docker build completes | FR-WS-008 | — | pending |
| FE3-S06 | AC3 | Local image matches what FE3-S01's `local.image` expects | FR-WS-008 | — | pending |
| FE3-S06 | AC4 | `coder templates push` succeeds, WITH `--variables-file` | FR-WS-008 | (i) | pending |
| FE3-S06 | AC5 | At least one failure encountered and resolved, recorded honestly | FR-WS-008 | — | pending |

### 3.5 FE4 — Toolkit and acceptance

| Story | AC | One-line description | FR | Gate | Status |
|---|---|---|---|---|---|
| FE4-S01 | AC1 | Workspace build succeeds, GitHub grant live | FR-KIT-001 | b | pending |
| FE4-S01 | AC2 | agentic-ai lands, no double clone | FR-KIT-001 | b | pending |
| FE4-S01 | AC3 | Sizing knobs actually chosen recorded | FR-KIT-001 | h | pending |
| FE4-S01 | AC4 | code-server reachable, browser-trusted | FR-KIT-001 | a | pending |
| FE4-S01 | AC5 | Wall-clock baseline recorded | FR-KIT-001 | i | pending |
| FE4-S01 | AC6 | Toolkit basics present | FR-KIT-001 | c, e | pending |
| FE4-S02 | AC1 | Gate (a) executed | FR-KIT-002 | a | pending |
| FE4-S02 | AC2 | Gate (b) executed | FR-KIT-002 | b | pending |
| FE4-S02 | AC3 | Gate (c) executed | FR-KIT-002 | c | pending |
| FE4-S02 | AC4 | Gate (d) executed | FR-KIT-002 | d | pending |
| FE4-S02 | AC5 | Gate (e) executed | FR-KIT-002 | e | pending |
| FE4-S02 | AC6 | Gate (f) executed | FR-KIT-002 | f | pending |
| FE4-S02 | AC7 | Gate (g) executed, non-gating | FR-KIT-003 | g | pending |
| FE4-S02 | AC8 | Gate (h) executed | FR-KIT-002 | h | pending |
| FE4-S02 | AC9 | Gate (i) recorded | FR-KIT-002 | i | pending |
| FE4-S02 | AC10 | Gate (j) executed | FR-KIT-002 | j | pending |
| FE4-S02 | AC11 | Gate (k) executed | FR-KIT-002 | k | pending |
| FE4-S03 | AC1 | Backup job runs to completion | FR-KIT-004 | — | pending |
| FE4-S03 | AC2 | Backup visible and dated in PBS | FR-KIT-004 | — | pending |
| FE4-S03 | AC3 | Backup integrity verified | FR-KIT-004 | — | pending |
| FE4-S03 | AC4 | Job details recorded | FR-KIT-004 | — | pending |
| FE4-S04 | AC1 | Verdict decision framework defined before results are read | FR-KIT-005 | — | pending |
| FE4-S04 | AC2 | Framework applied against FE4-S02's results | FR-KIT-005 | — | pending |
| FE4-S04 | AC3 | Single explicit verdict recorded | FR-KIT-005 | — | pending |
| FE4-S04 | AC4 | Open operator decisions carried forward | FR-KIT-005 | — | pending |
| FE4-S04 | AC5 | Verdict does not open productisation | FR-KIT-005 | — | pending |
| FE4-S05 | AC1 | Retrospective covers all five epics | FR-KIT-006 | — | pending |
| FE4-S05 | AC2 | FE4-S04's verdict restated verbatim | FR-KIT-006 | — | pending |
| FE4-S05 | AC3 | 16 platform-owner decisions triaged | FR-KIT-006 | — | pending |
| FE4-S05 | AC4 | Explicit OPEN/STOP decision | FR-KIT-006 | — | pending |
| FE4-S05 | AC5 | If OPEN, next-phase scope bounded | FR-KIT-006 | — | pending |
| FE4-S05 | AC6 | Closure state proposed, not applied | FR-KIT-006 | — | pending |

---

## 4. Cross-cutting test categories

### 4.1 The empty-file contract

Gate (f) plus `FE2-S03` and `FE0-S01`/`FE0-S02`'s "staged, not yet deployed" ACs together prove the
`/opt/coder/secrets` (six empty 0600 files, 0700 dir) → `/run/secrets/*` → `~/.config/forge/*.env`
seam end to end, per architecture.md and E5 of the proposal. The mnemosyne pair's explicit absence
(`FE2-S03-AC3`) is the regression guard against a future change accidentally re-introducing an
OpenMemory dependency inside the PoC's scope.

### 4.2 The IaC / no-drift guard

`FE1-S01`, `FE1-S02`, `FE0-S05`, and gate (j) together form a closed loop: the phantom
`ct_sparkle_vlabel` block must stay resolved, the `module.ct_forge_01` block must match the runbook
pattern exactly, and every `terraform plan` in this suite is narrowly `-target`ed per NFR-IAC-002.
No story in this suite runs a bare `terraform plan` against the homelab root.

### 4.3 The HA + replication pair

`FE1-S03` and gate (k) enforce the ct:151 lesson: a `standard` rule membership without matching
replication jobs to **both** peers is treated as a failed story, not a partial pass. The
`started`/`stopped` question (R6) is recorded as an open operator decision in `FE1-S03-AC3`, and
gate (k) checks against whatever that decision actually was — not an assumed default.

### 4.4 The sizing / capacity measurement (R4)

`FE1-S01-AC2` (swap_mb), `FE3-S01-AC2`/`AC3` (four new `variable`s), `FE4-S01-AC3` (values
actually chosen recorded), and gate (h) together measure R4 without resolving it. No story in this
suite is permitted to close R4 — see canon HARD RULE 2 and each story's explicit non-resolution
language.

### 4.5 The ingress posture

Every citation of the no-public-ingress policy in this suite (`FE0-S02-AC5`, `FE2-S05-AC6`, this
document's §1.3) points to `wiki/architecture/tailscale-policy.md:20-31` and
`wiki/architecture/remote-access-topology.md` — never "ADR-010" (HARD RULE 1). DNS-01 over an
outbound API call is the entire ingress story; no inbound port is opened anywhere in this suite.

---

## 5. Quality audit

### 5.1 FR coverage

All 35 frozen FRs (`FR-PRE-001`…`006`, `FR-SUB-001`…`007`, `FR-CTL-001`…`007`, `FR-WS-001`…`009`,
`FR-KIT-001`…`006`) map to at least one story AC in §3. **18 of the 35 have no dedicated lettered
gate (a)–(k)** — their only coverage is a story AC. This is expected, not a defect: the eleven
gates are deliberately a small, externally-observable subset; most FE1/FE3 FRs describe
implementation detail (a Terraform variable shape, a script parameterisation) that a lettered gate
would not usefully re-state. The 18:

`FR-PRE-003, FR-PRE-004, FR-PRE-005, FR-SUB-002 (partially — feeds gate h but has no dedicated
letter), FR-SUB-006, FR-SUB-007, FR-CTL-001, FR-CTL-002, FR-CTL-006 (partially — feeds gate g),
FR-WS-001, FR-WS-002 (partially — feeds gate h), FR-WS-003, FR-WS-006, FR-WS-007, FR-WS-009,
FR-KIT-004, FR-KIT-005, FR-KIT-006.`

### 5.2 Vague ACs

**All 141 ACs are now read from disk** (regenerated 2026-09-09), and none were found vague by title
— every one names a concrete file, command, or measurable value in its one-line description.
**This document did not re-open each story file to verify every AC's full Given/When/Then body
against §1.2's observability bar** — that verification is each story's own responsibility at `done`
time, per its Definition of Done checklist. The former caveat about 36 derived placeholders no
longer applies; the replacement caveat is narrower and stated in §1.1: a `pending` status here means
"no per-AC evidence recorded", which for a story already marked `done` is an evidence gap, not a
delivery gap.

### 5.3 Known gaps

> **The three gaps listed here — `FE1-S04`/`S05`, `FE2-S06`, and `FE3-S01`…`S06` not existing — are
> CLOSED as of 2026-09-09.** All nine stories are on disk and their ACs are indexed in §3. The gaps
> that replaced them are different in kind and are recorded under §1.1: eight stories are `done` in
> the sprint file with no per-AC evidence recorded, and `FE3-S02`'s evidence table carries a verdict
> for an AC6 its story does not define. Original text retained below.

- ~~`FE2-S06` does not yet exist; gate (g)'s R2 mitigation (the Docker 29.5.0 trap) has no authored
  story backing it as of this document's date.~~
- ~~`FE3-S01`…`S06` do not yet exist; the entire de-Azuring of the template (FR-WS-001…009) has no
  authored story, only this document's derived placeholders.~~
- ~~`FE1-S04`/`S05` do not yet exist; `dev-host` provisioning and the E2 privilege re-measurement have
  no authored story.~~

---

## 6. Test execution order

**FE0 → FE1 → FE2 → FE3 → FE4**, strictly — no epic's gates are meaningful ahead of its
predecessor's completion:

1. **FE0** — both operator prerequisites exist and are recorded (FE0-S01, FE0-S02), plus the three
   non-blocking hygiene stories (FE0-S03…S05).
2. **FE1** — CT 167 exists, is HA'd, and `dev-host` has run.
3. **FE2** — coderd, Postgres, secrets, coder.env, Caddy TLS, and the Docker daemon fix are all in
   place and coderd is reachable at `https://forge.bi-services.be`.
4. **FE3** — the template builds locally and `coder templates push` succeeds.
5. **FE4** — first workspace create, all eleven gates run from a tailnet client, PBS backup, verdict,
   retrospective — in that order, since each FE4 story is a hard dependency of the next.

## 7. Test tooling and prerequisites

| Tool | Used for | Where |
|---|---|---|
| A tailnet client, genuinely off the LAN | All eleven gates (a)–(k), per §5.3's execution model | FE4 |
| `coder` CLI | `coder create`, `coder ssh`, `coder templates push`, `coder external-auth` | FE3-S06, FE4-S01, FE4-S02 |
| A browser | Certificate inspection for gate (a) | FE4-S02 |
| `ha-manager` | Gate (k); break-glass diagnosis only, never for provisioning | FE1-S03, FE4-S02 |
| `pvesr` | Reading `/etc/pve/replication.cfg` for gate (k) | FE1-S03, FE4-S02 |
| Proxmox Backup Server (`proxmox-backup-client`, `vzdump`) | FE4-S03 | FE4 |
| `terraform` (narrowly `-target`ed) | Gate (j); FE1-S01/S02, FE0-S05 | FE1, FE4-S02 |
| `ansible` (the `pve-ha-replication` / `pve-ha-rules` / `dev-host` / `forge-coder-host` roles) | FE1-S03, FE1-S04, FE2-S01…S06 | FE1, FE2 |
| `git` | Phantom-block checks (FE0-S05), `main.tf` not-forked check (FE3-S06) | FE0, FE3 |
