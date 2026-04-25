# Implementation Readiness Report — Epic 9 Hybrid Gemma Serving

**Audit date:** 2026-04-25
**Auditor:** code-review-agent (BMad implementation-readiness audit)
**Scope:** Research doc + architecture (12 ADRs) + epics (21 stories) + sprint status + Story 9.1 file
**Verdict:** READY WITH NOTES

## Per-dimension scores

- A. Cross-doc consistency: PASS
- B. PRD-equivalent completeness: PASS
- C. Architecture completeness: PASS
- D. Epic/story completeness: PASS WITH NOTES
- E. First-story executability: PASS
- F. Risk + open question coverage: PASS
- G. Operational readiness: PASS WITH NOTES

## Findings

### Critical (must fix before Sprint 1 starts)

None. Story 9.1 is self-contained, executable, and the Sprint 1 chain (9.1→9.5) has no blocking inconsistencies. The recent cleanups (B-G + Story 9.5 rewrite + ADR-002 addendum) reconciled all previously-tracked OD-7…OD-11 contradictions.

### Important (should fix during Sprint 1)

1. **Sprint status YAML naming inconsistency in Story 9.1's Task 6.** Story file (line 121) instructs the implementer to "Edit the matching `homelab-playbook/_bmad-output/implementation-artifacts/sprint-status-*.yaml` for the Hybrid Gemma sprint plan". The actual file is `hybrid-gemma-serving-sprint-status.md` (no `sprint-status-` prefix, `.md` not `.yaml`). Implementer will look at the wrong glob. Fix the path in Story 9.1 Task 6.
2. **Story 9.1 references nonexistent inventory file `ct-dev-test.yml`.** Tasks 2 and 3 reference `cd homelab-infra && ansible-playbook -i inventory ct-dev-test.yml --tags llama_server`. The repo convention (per epic doc Story 9.4) is `ct-ai-01.yml`. Verify whether `ct-dev-test.yml` playbook exists in `homelab-infra/ansible/playbooks/`; if not, story needs the actual playbook name (or a note that the implementer must create it). Same applies to Story 9.4 ACs.
3. **OD-1 LiteLLM tool-call delta passthrough verification still pending.** Sprint status correctly tracks this as resolution-required-by-Story-9.16, but no concrete sub-task or AC is added to Story 9.16 itself in the epic. When Story 9.16 file is authored, ensure it has an explicit AC: "verify tool_call deltas pass through unmodified; if buffered/rewritten, document FastAPI direct-bypass plan."
4. **Architecture §Open question #2 (Renovate vs Dependabot cadence) is OD-4 cross-cutting with no resolution date.** Sprint status says `resolution_required_by: "Before first dep-bump PR lands"` — there is no story owning this. Consider adding a Sprint 2 sub-task to Story 9.6 (proxy scaffolding is when the first deps get pinned) or explicitly accept the default (Renovate weekly with manual LiteLLM merges) before Sprint 1 closes.

### Nice-to-have (can defer)

1. Architecture §Project Structure shows `homelab-apps/gemma-hybrid-proxy/` in research §Development Workflows and Tooling line 558, but architecture's resolved location is `homelab-infra/ansible/roles/gemma-hybrid-proxy/files/`. Research doc is the older artifact; not worth retroactive editing, but note that an implementation agent who reads research first may briefly be misled before reaching the architecture doc. Already flagged in epic Story 9.6 notes ("REPO LOCATION RESOLVED 2026-04-25").
2. Sprint status line 173 names artefact `sprint1-toolcall-gate-results-YYYY-MM-DD.md` with literal `YYYY-MM-DD` — fine, but Story 9.1 evidence file uses literal `2026-04` (committed date format). Pick one convention for evidence-file naming.
3. ADR-008 (defer audio) vs Sprint 4 stories 9.18-9.21 surface contradiction: sprint status §note_on_audio_contradiction lines 393-398 explicitly addresses this and instructs the 415 short-circuit be removed before 9.19 lands. Adequate, but no story-level AC exists in 9.19 enforcing the removal. Add as 9.19 AC when that story is authored.
4. The existing E4B `llama-server` rebinding to `127.0.0.1` (ADR-009 enforcement) is referenced in Story 9.11 ACs and sprint cutover step 5, but not as a discrete story or sub-task. Acceptable but easy to forget at deploy time.

## Confirmed strengths

- **All 5 cleanups (B-G) are consistently applied across all 4 docs.** Three-tier gate (≥90%/70-89%/<70%), `image_id: string` schema, max iterations 5, status format `\n_[describing image...]_\n`, repo location at `homelab-infra/ansible/roles/gemma-hybrid-proxy/files/`, and LiteLLM `1.83.13` pin all match across research §Implementation, architecture ADR-002 addendum + ADR-011, epic Stories 9.5/9.10/9.12/9.14/9.16, and sprint status exit_gate + open_decisions block.
- **All 12 ADRs are coherent** with explicit Status/Context/Decision/Consequences/References, plus a §ADR coherence note at line 310 and a coherence matrix at lines 575-591 verifying no two ADRs contradict.
- **All 10 research-doc acceptance criteria map to stories** (epic doc §Final Validation lines 651-661 has the explicit AC#→story table).
- **All 10 risks map to mitigation stories** (epic doc lines 671-684 + sprint status risks block lines 435-520). R8 and R10 are correctly accepted with no mitigation-story.
- **Story 9.1 is genuinely self-contained.** Includes pre-flight (Task 0), exact SSH/curl/ansible commands, decision tree for "rebuild needed vs not", concrete rollback (snapshot + git checkout), explicit ct-dev-test-first per `feedback_test_container.md`, evidence file path, conventional-commit guidance, and traces back to research + architecture + memory files.
- **systemd ordering is documented end-to-end** (architecture §systemd ordering lines 544-557, with `Requires=` chain + `WatchdogSec=30` + sd_notify discipline).
- **Tailscale-only exposure (ADR-010) consistently referenced** in research §Integration Security, architecture, epic Story 9.17, and sprint status R7.
- **Browser validation (Playwright MCP) flagged on the right stories** — Story 9.11 (vision smoke) and Story 9.20 (full E2E suite) per `feedback_browser_validation.md`. Story 9.1 correctly opts out (infra-level work).
- **No hardcoded secrets in any artifact.** Vault references are consistent: `vault_litellm_master_key`, vault-encrypted bearer key path. Story 9.16 explicitly states bearer key recorded only in operator's password manager (vs vault is OD-3 open).
- **PRD-equivalent completeness solid:** all FR domains FR1-FR31 trace to components in architecture §Functional requirements coverage table; all NFRs have an explicit mechanism in §Non-functional requirements coverage.

## Sprint 1 readiness verdict

**GO.** Story 9.1 is ready for an implementation agent to pick up immediately; the four "Important" items above are documentation/path corrections that can be fixed in-sprint without blocking 9.1's execution, and the gate decision (Story 9.5 three-tier) is fully specified with a re-runnable test harness design.

## Implementation agent handoff checklist

- [x] Story 9.1 file exists at `/home/developer/workspace/homelab/homelab-playbook/_bmad-output/implementation-artifacts/9-1-verify-vulkan-build-of-llamacpp.md` and is self-contained
- [x] Architecture doc has all 12 ADRs with full SCDC+R structure + ADR-002 three-tier addendum
- [x] Sprint status YAML has three-tier exit gate with explicit pass/marginal/fail actions
- [x] All cross-doc inconsistencies (OD-7…OD-11) resolved per sprint-status §known_inconsistencies
- [x] Risk register R1-R10 mapped to mitigation stories
- [x] All 10 research ACs mapped to story owners
- [x] Story 9.1 references existing role at `homelab-infra/ansible/roles/llama-server/`
- [x] Test container (ct-dev-test 192.168.50.152) honored in Story 9.1 conditional rebuild path
- [x] Rollback plan in Story 9.1 includes Proxmox snapshot before rebuild
- [ ] Verify `ct-dev-test.yml` Ansible playbook exists (or correct Story 9.1 Tasks 2-3 to reference the actual playbook name)
- [ ] Correct sprint-status YAML path glob in Story 9.1 Task 6 (`hybrid-gemma-serving-sprint-status.md`, not `sprint-status-*.yaml`)
- [ ] Confirm OD-1 (LiteLLM passthrough) becomes an explicit AC in the future Story 9.16 file
- [ ] Confirm OD-4 (dep-bump bot/cadence) is decided before first PR bumps a Python dep in Sprint 2
- [ ] Capture any pre-rebuild binary sha256 in Story 9.1 Task 0 evidence (already in story; agent must execute)
