# Forge PoC — Full Analysis & Validation Plan (v2)

**Date:** 2026-09-10
**Status:** APPROVED 2026-09-10 as written (operator: tomamourette)
**Operator:** tomamourette
**Method:** multi-perspective discovery → adversarial verification → fix → re-review → re-validate, looped to convergence
**Engine:** Claude Code Workflow tool, Opus 5 sub-agents throughout, concurrency cap 10 (CT 250 has 12 cores)
**v1 → v2:** rewritten after an adversarial critique (§13 lists every change and why)

---

## 1. Objective and exit criteria

Establish, with evidence, the true state of everything built on 2026-09-08/09 for the Forge self-hosted PoC; fix every defect above "minor"; leave behind a system whose remaining known issues are cosmetic or explicitly *accepted* by the operator, plus an audit record a second person can re-run against a fixed baseline.

**Exit (converged):** a full verification pass in which every confirmed finding is either **Low**, or carries an operator-signed **ACCEPTED_RISK** disposition (§4). Severities are never lowered to reach exit.

**Exit (bounded):** after **4 rounds**, if findings ≥ Medium remain without acceptance, the audit closes as **FAILED-WITH-RESIDUALS**. The final report lists them; the operator decides what ships. There is no third outcome.

## 2. Scope — what was built

| # | Subsystem | Where | State |
|---|---|---|---|
| S1 | Terraform & fleet IaC | `homelab-infra/terraform/` — `ct_forge_01`, `outputs.tf` DNS + Prometheus registration, `ct-debian` (`target_node` in `ignore_changes`), sparkle-cps reconciliation, Cloudflare apex + wildcard records, provider debug logging off; **gitignored inputs:** `terraform.tfvars` (incl. the added `ssh_keys` entry), `terraform.tfstate` | applied |
| S2 | Ansible: Coder host | `roles/forge-coder-host/` + `playbooks/forge-coder-host.yml`, `forge-workspace-image.yml` — coderd, Postgres 16, Caddy (custom build), secrets dir, `coder.env`, Docker pin + `time-namespaces`, systemd drop-in, pg_dump timer, sshd exemption, access log, secret-argv guard | applied to CT 167 |
| S3 | Ansible: DNS, HA, inventory, dev-host | `roles/forge-dns` (Pi-hole `05-forge.conf`); `pve-ha-replication` + `pve-ha-rules` defaults for ct:167; `hosts.ini`, `host_vars/ct-forge-01`; `dev-host` as applied (known non-idempotent Docker-restart task) | applied to ct-docker-01 / pve3 / CT 167 |
| S4 | Live runtime — CT 167 **and its credential material** | units, listeners, certs, resolver, Docker, image `forge-workspace:latest`, template `forge`, admin user; **`~developer/.config/forge/coder-admin.env` (cleartext admin password, 0600), `~developer/.config/coderv2/session` (long-lived admin token)**; Proxmox side: `pct config 167` incl. out-of-band `keyctl=1`, HA resource + rules on pve3, both replication jobs | running |
| S5 | forge-platform repo | Hermes generalisation (`config.py`, `worker.py`, `workflow.py`, TF variables/validations, `acr.tf`, `forge-sync.sh`, `forge-onboard.sh`); template (`main.tf`, `variables.tf`, `poc.variables.yaml`, `scripts/poc-plan.sh`); `workspace/Dockerfile`; `.github/workflows/coder-template-push.yml`; docs/ADRs | **working tree ahead of GitHub** (remote HEAD == local HEAD, but ~11 files modified/untracked locally) |
| S6 | agentic-ai / company-overlay / knowledge-base | strip, rebrand, BMad attribution, history purges, skeletons, profile rename; **GitHub-side state:** all four repos private, zero forks, remote HEAD == local HEAD (verified 2026-09-10); no Actions secrets configured | pushed |
| S7 | Planning & governance | `products/forge-platform/` (PRD, architecture, 6 ADRs, 27 stories, acceptance, e2e, readiness, follow-ups), proposal, `sprint-status-forge-platform.yaml`; **vault entries added** (`vault_forge_github_client_*`, `vault_coder_pg_password`, `vault_coder_admin_password`) — listed, not diffable (encrypted) | files |
| S8 | Evidence provenance | Yesterday's workflow outputs `/tmp/{fe2,fe3,fe3fix,co}.json` and `/tmp/audit_parsed.json` — cited by earlier reports, currently unretained | volatile |

**Out of scope:** Hermes/OpenMemory/Langfuse deployment; anything Azure-side; the pre-existing `update-dynamic-configs.yml` breakage except as a follow-up. **FE4 (workspace path):** in or out is an operator decision taken **before Phase 0** (§9 item 2) and does not change mid-audit — rounds must stay comparable.

## 3. The six perspectives

Each perspective is a separate Opus agent with its own brief. They are deliberately orthogonal. **"Nothing found — here is exactly what I examined" is an acceptable, first-class verdict**; an agent is never rewarded for producing findings.

| P | Persona | Hunts | Evidence style |
|---|---|---|---|
| **P1 Correctness** | Platform engineer accepting the work | Does each artifact do what its story/AC/doc says; gates **(a), (h), (j), (k)** (workspace-interior gates b–g, i only if FE4 is in scope); per-AC evidence for stories marked done | Runs verify commands; diffs claim vs observed |
| **P2 Security** | Security engineer, assume-breach | Secrets in files/logs/git history/`/proc`/shell history/**host credential material**; modes; listener exposure; credential lifecycle; supply chain (pins, checksums, `curl \| sh`); privilege boundaries | Greps by secret *value* (in-agent, counts out), `ss`, `stat`, `git log -p -S`, sandboxed re-runs |
| **P3 Reliability & Operations** | SRE on call at 03:00 | Boot ordering, restart policies, HA failover path, backup **restore** (§7 drill), cert renewal, headroom, log rotation, SPOFs; **monitoring: is CT 167 actually scraped/alerted?** | `systemctl show`, controlled failure injection, restore drill |
| **P4 IaC Quality & Maintainability** | Reviewer who owns this in six months | Idempotency, **declared-vs-live drift** (§7), conventions vs estate, dead code, misleading comments, doc↔code agreement, repo hygiene | Re-runs playbooks under mutex, `terraform plan`, template vs live file diffs |
| **P5 Generalisation & Portability** | Engineer onboarding a *second* company | Saply/Azure hard requirements; every default overridable; retrofit path (overlay `config/`, variables file, org names, tracker); fresh-host provision from zero (`--check` against a scratch inventory host); fresh-clone viability | Dry-runs, literal greps, end-to-end variable plumbing traces |
| **P6 Seams & Expiry** *(new)* | Integrator who has been burned by "it worked yesterday" | **Seams:** Terraform-declared vs `pct config`; role template vs live `/etc`; repo template vs the version inside coderd; repo Dockerfile vs image on host; vault vs consumers. **Expiry:** cert, Docker pin (2026-12-09), Coder session token, OAuth secret, Tailscale key, Caddy build-URL pin. **External quotas:** Let's Encrypt / Cloudflare rate limits the audit's own restarts could trip. **Upgrade/rollback:** `apt upgrade` under the pin; coder 2.37 conffile behaviour | Hash comparisons, API ↔ repo diffs, date arithmetic, rate-limit accounting |

**Cell selection (round 1):** 6 × 8 = 48 cells; **barren cells are dropped by design** (e.g. P2×S7, P3×S7, P5×S8) — expected ~30 finders. Rounds ≥ 2: changed subsystems × all six, plus a standing **P1 / P2 / P4** sweep.

## 4. Severity and disposition

| Severity | Definition |
|---|---|
| **Critical** | Live secret exposure; data-loss path; platform down or unable to return after reboot/failover |
| **High** | Documented workflow fails; unrecoverable on a common path (HA failover, upgrade); drift that makes the next `apply` destructive |
| **Medium** | Wrong behaviour with a workaround; doc/comment that leads an operator to a harmful action; missing idempotency; unpinned/unchecked download |
| **Low** | Cosmetic; naming; wording that cannot mislead; hardening beyond PoC scope |

| Disposition | Who sets it | Effect on exit |
|---|---|---|
| **FIXED** | fixer, then re-verified | none |
| **CATALOGUED** | verifiers (Low only) | none |
| **ACCEPTED_RISK** | **operator only, in-session** — with rated severity (unchanged), expiry date, and the condition that would make it unacceptable | does not block exit; listed in the final report with its expiry |
| **OPEN** | default | blocks exit if ≥ Medium |

Severity is assigned by **verifiers**; a fixer may not lower it, narrow it, or convert "fix" into "document". Disagreement goes back to verification (§5). Nothing is pre-negotiated with the operator: items such as the Docker pin are found, rated, and — if the operator chooses — accepted *on the record*.

## 5. The loop

```
Round r (r = 1..4):
  DISCOVER  finders read the Phase-0 EVIDENCE BUNDLE, never the live host.
            (round 1: ~30 cells; rounds ≥2: changed subsystems × P1-P6, plus P1/P2/P4 sweep)
  DEDUPE    deterministic code (workflow JS + audit/tools/dedupe.py, checked in):
            key = (subsystem, file|absence_of, normalised claim); absence findings are first-class
            (file: null, absence_of: required); root-cause linking merges cross-subsystem symptoms.
  VERIFY    each unique finding → 3 independent verifiers (serialised host access via one
            ControlMaster socket). Verdicts: CONFIRMED | REFUTED | COULD_NOT_REPRODUCE.
            A REFUTED must be constructive (quote the evidence the behaviour is correct + the exact
            scope searched). COULD_NOT_REPRODUCE escalates to a 4th verifier with a widened scope
            supplied by the finder. Survives at ≥2 CONFIRMED. Finder gets one written rebuttal.
            Verifiers assign final severity independently of the vote.
  GATE      if every confirmed finding is Low or ACCEPTED_RISK → EXIT (converged)
  FIX       confirmed ≥ Medium, grouped by subsystem; serialised on CT 167 and per tree; IaC-only;
            each fix ships a NEW CHECK that is DEMONSTRATED TO FAIL on the pre-fix state
            (stash → run → quote red → restore → quote green). The regression pack is append-only.
  REVIEW    P1-P6 re-review the fixed areas only (fresh agents, no prior-round memory)
  VALIDATE  (a) targeted re-verification of every fix; (b) the regression pack (§7) incl. one
            SEEDED-DEFECT CONTROL; (c) declared-vs-live reconciliation. All green or the round stays open.
```

## 6. Phases and deliverables

All audit artefacts live **outside the audited tree**: `homelab-playbook/_bmad-output/audit/forge-2026-09-10/`. Every write passes a redaction filter; Phase 6 is gated on a post-write **secret scan by vault value over the whole audit directory** (counts only).

| Phase | Work | Deliverable |
|---|---|---|
| **0 Baseline** | (1) If approved: Forge-scoped commit per tree on a new `audit/forge-baseline` branch, unrelated paths untouched, excluded paths recorded as a patch. (2) **Evidence bundle** captured once over a single SSH session: full `/etc` tree (redacted copy + per-file hashes/modes), `systemctl show` for every unit, `ss -tlnp`, package list, cert SANs + dates, `pct config 167`, HA/replication status, Pi-hole drop-in, `docker image ls`, coderd template version + variables via API (token never written), `free -m`, `df`. (3) Hashes of `terraform.tfvars` (redacted), `terraform.tfstate`, `group_vars/vault.yml` (encrypted, listed not diffed). (4) `terraform plan -refresh=false` + one **refreshed** plan captured for comparison. (5) Copy `/tmp/*.json` evidence into `baseline/provenance/`. (6) **Expected-drift allowlist** seeded with `keyctl=1` (out-of-band by necessity, documented in `main.tf`). | `baseline/` — bundle, hashes, `manifest.json`, `expected-drift.yaml` |
| **1–4 Rounds** | §5 | `round-N/{findings,verdicts,fixes,validation}.json` + `.md` |
| **5 Final** | Full regression pack + **reboot proof** (§7 method) + six-perspective sign-off panel: each writes an independent opinion; disagreements are recorded, not averaged | `final-report.md` + `re-run.sh` that replays the pack against the current host |
| **6 Close** | Secret scan of `audit/**`; update `follow-ups.md`, sprint status, memory | — |

## 7. Regression pack (end of every round, and Phase 5) — append-only

Every check names **who** runs it (root vs non-root), **from where** (on-host vs off-host), and its **negative control** where one exists.

**Concurrency rules (S7):** any playbook or `terraform` invocation takes a `flock` on `/tmp/forge-audit.lock`; no playbook runs while finders/verifiers are live against the host; the `forge-dns` `changed=0` proof runs **once**, first or last in the pack (its reload path recomputes from a live `dig` and can trigger a lab-wide DNS reload); `dev-host` is **not** re-run (known non-idempotent Docker restart) — excluded with reason.

- **IaC:** `forge-coder-host` `changed=0` (under mutex); `forge-dns` `changed=0` (once); `terraform validate` clean (both roots); `terraform plan -refresh=false` → *No changes* **and** a `-refresh=true` plan whose only diffs are on the expected-drift allowlist; `scripts/poc-plan.sh` renders.
- **Declared-vs-live reconciliation:** `pct config 167` vs module inputs; `/etc/coder.d/coder.env`, Caddyfile, `05-forge.conf`, drop-ins: live hash vs template render. Any diff not on `expected-drift.yaml` is a finding.
- **Runtime:** all units active+enabled; **`NRestarts=0` measured ≥10 min after any reboot and never immediately after one**; coderd `127.0.0.1:3000` only; Caddy `:80/:443`; from **off-host, real DNS, non-root:** `/healthz`, `/api/v2/buildinfo`, both SANs by SNI with **per-run random labels**; `dig @192.168.50.194` apex + random label + `hermes`; `dig @1.1.1.1` + `@9.9.9.9` random wildcard label; template `forge` active and its variables == `poc.variables.yaml`; image digest unchanged; pg_dump timer active with a dump < 26 h old; HA `ct:167 (pve3, started)`; both replication jobs.
- **Restore drill (P3, once per round):** executed **as an Ansible task** (the one sanctioned write): create `coder_restore_<random>`, `pg_restore --schema-only` + table row-count comparison against live, drop the DB in a `trap` — never a full data load, never left behind.
- **Repos:** `services/hermes` pytest **0 failed and ≥156 passed**; agentic-ai **0 failed and ≥178**; `generate_catalog.py --check`; no `ADR-010` (control: a planted literal must be caught); no Saply-hard literal (control likewise); **no secret value** in any tracked/untracked file or in the audit directory (grep by vault values, in-agent, counts only).
- **Seeded-defect control (one per round):** plant a known break in a scratch copy (e.g. an unflagged wildcard-optional claim, a `0644` on `coder.env` in a rendered copy) and prove the pack turns red. Without this the exit gate proves nothing.
- **Reboot proof (Phase 5, and at most once per round):** via the Ansible `reboot` module (in-guest, HA-neutral for `state=started`), **never** while an apt/dpkg transaction is running, **never** as the last action before uptime-dependent checks.
- **Round-closing rule:** a round cannot close with the pack red, even if its own fixes verify.

## 8. Guardrails (every agent, every round)

1. Host changes only through Ansible in `homelab-infra/ansible`; hand commands read-only; the restore drill is the single sanctioned write and is itself an Ansible task. Terraform only with a narrow, quoted plan.
2. Never print a secret value; grep by value in-agent, report counts/lengths/hashes.
3. No commits/pushes/history rewrites except the Phase-0 baseline commit if approved.
4. No `ha-manager`/`pvesr` writes; no other containers touched; Pi-hole additive files only.
5. "Pass" is backed by output the agent produced in its own run.
6. Fixers may not narrow scope or lower severity; disputes return to verification.
7. Fresh agents each round; verifiers see claim + evidence, not the finder's reasoning.
8. Finders never touch the live host — they read the baseline bundle. Verifiers use one shared `ControlMaster` socket, serialised.
9. `flock` around every playbook/terraform run; nothing mutating runs while a discovery wave is live.

## 9. Operator decisions & inputs

| # | Item | Why | When |
|---|---|---|---|
| 1 | **Baseline commit** — one Forge-scoped commit per tree on branch `audit/forge-baseline` (homelab-infra, homelab-playbook, forge-platform); unrelated pending work left out and recorded | Fixes become diffable/revertible; today the live platform's IaC is uncommitted. Note: `homelab-infra` is on `feature/context-stack-e3-graphiti` and `homelab-playbook` on `docs/remote-access-tailscale-primary`, each with unrelated pending changes — hence a dedicated branch and scoped paths | **Before Phase 0** |
| 2 | **FE4 in or out** — requires your GitHub OAuth consent at `https://forge.bi-services.be/external-auth/github` as `forge-admin` (password: `ansible-vault view … \| grep vault_coder_admin_password`) | If out: gates b–g, i and the Coder→GitHub→agent-callback path are reported as *unverified*. If in: they are exercised. Decision is fixed for the whole audit | **Before Phase 0** |
| 3 | **Credential rotation** ×3 (Proxmox API token, `dev_vm_password`, Cloudflare token) | Rotating mid-audit turns the regression pack red for non-defect reasons (plans fail, DNS-01 renewal breaks). Do it **before Phase 0** (then Phase 0 re-verifies one plan and one Caddy renewal path) **or after Phase 5 — never during** | Before 0, or after 5 |
| 4 | **Approve this plan** | — | Now |

The Docker pin (FE2-S06) is deliberately **not** listed: it will be found, rated, and presented for an ACCEPTED_RISK decision inside the loop, on the record.

## 10. Effort & duration (honest range)

Round 1: ~30 finders (bundle-only, fast) → ~25–40 unique findings → 75–120 verifiers (serialised host access is the bottleneck) → fixes → 6 reviewers → pack. Measured throughput yesterday: FE2 ≈ 5 h / 58 agents; close-out ≈ 3.7 h / 37. **Round 1 ≈ 6–8 h; rounds 2–3 ≈ 2–3 h each; Phase 5 ≈ 1–1.5 h. Total ≈ 12–18 h** if it converges in three rounds. Blow-ups: verifier count scaling with findings; an SSH lockout costing a wave; the DNS reload path hanging (documented 5–20 min).

## 11. Known limitations

- If FE4 is out, the workspace path is *unverified*, and the report says so.
- HA failover is verified by configuration and boot path, not by failing pve3.
- A full PBS restore of CT 167 is not performed (FE4-S03 territory); the pg_dump restore drill is schema + row counts only.
- The vault is listed and hashed, never diffed.

## 12. Findings schema (machine-readable, stable IDs)

```
id: R1-P2-S4-003            # round-persona-subsystem-seq
subsystem, persona
file: <path> | null          # null requires absence_of
absence_of: <what is missing>
claim, evidence: [ ... ]     # quoted output
reproducer: <literal command a second person can paste>
observed_against: <baseline manifest sha256>
severity, disposition
verifier_votes: [ {agent, verdict, scope_searched, evidence} ... ]
rebuttal: <finder's one written rebuttal, if any>
fix_commit | fix_files, check_added, check_fails_pre_fix: <quoted red run>
```

## 13. v1 → v2 change log (from the adversarial critique)

| Ref | Change |
|---|---|
| B1 | Added ACCEPTED_RISK disposition; removed the pre-negotiated Docker-pin severity from §9 |
| B2 | Finders read a Phase-0 evidence bundle, never the host; verifiers serialised via ControlMaster |
| B3 | Declared-vs-live reconciliation + expected-drift allowlist (keyctl #1); tfvars/tfstate/vault hashed in baseline |
| B4 | Rotation timing fixed: before Phase 0 or after Phase 5, never during |
| B5 | Restore drill made an Ansible task into a random-suffixed DB, schema+counts, dropped in a trap; reboot method and timing named |
| B6 | Estimate corrected to 12–18 h; Round 1 shrunk via barren-cell drop and bundle-only finders |
| B7 | Audit artefacts moved outside the audited tree; redaction on write + secret scan gating Phase 6 |
| S1 | Constructive refutation; COULD_NOT_REPRODUCE escalation; finder rebuttal; severity decoupled from vote |
| S2 | Absence findings first-class; root-cause linking before verification |
| S3 | P6 Seams & Expiry added |
| S4 | New checks must fail on the pre-fix state; pack is append-only |
| S5 | pytest asserts 0 failed + count ≥ baseline; seeded-defect control per round; non-root/off-host/random-label checks; NRestarts timing rule |
| S6 | Standing sweep is P1/P2/P4 |
| S7 | flock mutex; no playbooks during discovery; DNS proof once; dev-host excluded |
| S8 | Baseline commit scoped per tree on a dedicated branch |
| S9 | FE4 in/out fixed before Phase 0; P1 gates restated |
| S10 | Findings schema, stable IDs, re-run.sh, hashes |
| S11 | Scope rows added: host credential material, GitHub-side state, vault entries, Proxmox CT config, monitoring registration, provenance |
| N1–N3 | "Nothing found" is a first-class verdict; FAILED-WITH-RESIDUALS defined; dedupe code location named |

---

**Operator:** ☑ Approved as written — 2026-09-10

**Pre-Phase-0 decisions recorded:**
1. Baseline commit: **YES** — Forge-scoped commit per tree on `audit/forge-baseline` (homelab-infra, homelab-playbook, forge-platform); unrelated pending work excluded and recorded as a patch. No push.
2. FE4: **IN SCOPE** — operator performs the GitHub OAuth consent before Phase 0; the evidence bundle is captured after it so all rounds see the linked state.
3. Credential rotation: **NOT ROTATING** — the three disclosed credentials (Proxmox API token, `dev_vm_password`, Cloudflare token) are to be presented inside the loop as an ACCEPTED_RISK for the operator to sign on the record, with expiry and unacceptability condition. Severity stays as rated.

**Housekeeping:** this plan file sits inside the audited tree (`products/forge-platform/audit/`). Per §6/B7 the working artefacts go to `_bmad-output/audit/forge-2026-09-10/`; Phase 0 copies this plan there as `plan.md` and this copy remains as the pointer of record.
