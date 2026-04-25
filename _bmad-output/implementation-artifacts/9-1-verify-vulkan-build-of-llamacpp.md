# Story 9.1: Verify Vulkan build of llama.cpp on ct-ai-01

Status: ready-for-dev

**Sprint:** 1 (Foundation)
**Epic:** Hybrid Gemma Serving (Epic 9, Sprint 1, Story 1)
**Owner:** unassigned
**Date Created:** 2026-04-25
**Depends on:** none in Epic 9 (relies on Epic 8 Story 8.4 — existing E4B `llama-server` already deployed on `ct-ai-01:8080`)
**Risks:** R3 (llama.cpp upgrade breaks Vulkan build on Strix iGPU)
**ADR References:**
- ADR-001 (Vulkan/RADV backend mandatory) — `homelab-playbook/_bmad-output/planning-artifacts/hybrid-gemma-serving-architecture.md`
- ADR-009 (loopback-only inter-service) — same file (informational; rebinding deferred to Story 9.4)

## Story

As a homelab operator,
I want the existing `llama-server` Ansible role's Vulkan build verified (and idempotently re-run if not),
So that the new 26B-A4B unit launches on the same proven Vulkan/RADV backend rather than discovering a build mismatch mid-Sprint.

## Story Summary

The 26B-A4B reasoner introduced in Sprint 1 will share the same llama.cpp binary as the existing E4B `llama-server` on `ct-ai-01` (VMID 160, 192.168.50.160 on pve3). ADR-001 makes Vulkan/RADV mandatory because ROCm has a confirmed endless-loop bug on `gemma-4-26B-A4B` for the Strix-class iGPU (llama.cpp issue #21416). This story verifies the existing build was compiled with `-DGGML_VULKAN=ON` and, only if not, re-runs the existing Ansible role with `llama_cpp_vulkan: true` to rebuild idempotently. The existing E4B service must remain healthy after any rebuild.

## Context for the Implementation Agent

### Why this story exists

- **ADR-001 (Vulkan mandatory):** ROCm produces garbage output (`<|channel><unused24>...`) on `gemma-4-26B-A4B` for gfx1151 (Strix-class iGPU). See [llama.cpp #21416](https://github.com/ggml-org/llama.cpp/issues/21416). The existing Vulkan path is the benchmarked-good path on Radeon 880M-class.
- **Sprint integrity:** Sprint 1 deploys a second `llama-server-26b` unit (Story 9.3) reusing the same `/opt/llama.cpp/build/bin/llama-server` binary. If the binary is missing Vulkan, every downstream Sprint 1 story silently breaks.
- **Architecture §Starter Template Evaluation:** the existing role is the explicit template for the 26B sibling role; verifying it now is cheaper than discovering a regression after Story 9.3 ships.

### Current state on ct-ai-01

- Container `ct-ai-01` (VMID 160) on `pve3`, IP `192.168.50.160`.
- `llama-server.service` runs Gemma 4 E4B + mmproj on `:8080` (per Epic 8 Story 8.4 / research §Implementation, Phase 0).
- Existing role binds `0.0.0.0` per defaults (`llama_server_host: 0.0.0.0`). Re-binding to `127.0.0.1` is **out of scope here** — that is ADR-009 enforcement work scheduled in Story 9.4.

### Existing role to read

`homelab-infra/ansible/roles/llama-server/`:
- `defaults/main.yml` — confirm `llama_cpp_vulkan: true` and `llama_cpp_build_deps` already include `libvulkan-dev`, `glslc`, `spirv-headers`, `spirv-tools`.
- `templates/llama-server.service.j2` — the systemd unit that launches `{{ llama_cpp_dir }}/build/bin/llama-server` with `LD_LIBRARY_PATH={{ llama_cpp_dir }}/build/bin`.
- `tasks/main.yml` — the build/install logic; this is what gets re-run if rebuild is needed.

### Decision tree (idempotent re-run vs fresh build)

```
Run AC-1 (--version) and AC-2 (ldd) commands
  ├── Vulkan present in BOTH outputs
  │     → no rebuild; mark story complete; log evidence in artifacts
  └── Vulkan missing in EITHER output
        → re-run Ansible role with --tags llama_server (or llama-server)
        → role MUST be idempotent (already compiled by Epic 8)
        → if role rebuilds the binary, restart llama-server.service
        → re-run AC-1 + AC-2 to confirm Vulkan now present
        → run AC-3 (smoke test) + AC-4 (radeontop) to confirm E4B still serves
```

## Acceptance Criteria

1. **Given** `ct-ai-01` (192.168.50.160) has the existing `llama-server` Ansible role applied and the E4B `llama-server.service` running
   **When** I run `ssh pve3 "pct exec 160 -- /opt/llama.cpp/build/bin/llama-server --version 2>&1 | head -10"`
   **Then** the output lists Vulkan among the active ggml backends (no ROCm references)

2. **Given** the binary is on disk
   **When** I run `ssh pve3 "pct exec 160 -- ldd /opt/llama.cpp/build/bin/llama-server | grep -i vulkan"`
   **Then** the output shows a Vulkan shared library linked (e.g., `libvulkan.so.1 => /lib/x86_64-linux-gnu/libvulkan.so.1`)

3. **Given** any rebuild has completed (or no rebuild was needed)
   **When** the existing `llama-server.service` (E4B + mmproj on `:8080`) restarts cleanly
   **Then** a smoke-test `curl` to `/v1/chat/completions` with a text-only prompt returns a coherent response (HTTP 200, valid JSON, non-empty `choices[0].message.content`)

4. **Given** the smoke test in AC-3 is in flight
   **When** I observe `radeontop` (or `intel_gpu_top` / `amdgpu_top` equivalent) on `ct-ai-01` or on `pve3` for the iGPU at `0000:c7:00.0`
   **Then** GPU activity is visible during inference (proves GPU offload still works; not CPU-only fallback)

Plus the gate from the epics doc:
- If Vulkan is missing initially, re-running the role rebuilds with `llama_cpp_vulkan: true` and a **second invocation reports zero changed tasks** (idempotency proof).
- The verified build evidence is captured in `homelab-playbook/_bmad-output/implementation-artifacts/llama-cpp-build-verification-2026-04.md` (raw outputs of AC-1, AC-2, AC-3 response excerpt, and AC-4 observation).

## Eval Assertions

| # | Assertion | Command/Check | Pass Criteria |
|---|-----------|---------------|---------------|
| AC-1 | Vulkan in `--version` backend list | `ssh pve3 "pct exec 160 -- /opt/llama.cpp/build/bin/llama-server --version 2>&1 \| head -10"` | Output contains `Vulkan` (case-insensitive); no `ROCm`/`HIP` references |
| AC-2 | Vulkan library linked | `ssh pve3 "pct exec 160 -- ldd /opt/llama.cpp/build/bin/llama-server \| grep -i vulkan"` | Returns at least one `libvulkan.so*` line |
| AC-3 | E4B serves text smoke test | `ssh pve3 "pct exec 160 -- curl -s http://127.0.0.1:8080/v1/chat/completions -H 'Content-Type: application/json' -d '{\"model\":\"gemma-4-e4b\",\"messages\":[{\"role\":\"user\",\"content\":\"Say hello in one word.\"}]}'"` | HTTP 200, JSON parses, `.choices[0].message.content` non-empty |
| AC-4 | iGPU active during inference | `ssh pve3 "pct exec 160 -- radeontop -d - -l 5"` (or `amdgpu_top -d` on host) while AC-3 fires | GPU/Shader busy > 0% during inference window |
| Idempotency | Role re-run reports zero changes | `cd homelab-infra && ansible-playbook -i inventory ct-ai-01.yml --tags llama_server` (run twice) | Second run: `changed=0` |

## Tasks / Subtasks

- [ ] Task 0: Verify prerequisites (AC: pre-flight)
  - [ ] Confirm `ct-ai-01` (VMID 160) is `running` on pve3: `ssh pve3 "pct status 160"`
  - [ ] Confirm existing E4B service is healthy: `ssh pve3 "pct exec 160 -- systemctl status llama-server.service --no-pager"` shows `active (running)`
  - [ ] Note current binary mtime + sha256 for rollback reference: `ssh pve3 "pct exec 160 -- stat /opt/llama.cpp/build/bin/llama-server && sha256sum /opt/llama.cpp/build/bin/llama-server"`
- [ ] Task 1: Verify current build flags (AC: 1, 2)
  - [ ] Run AC-1 command — capture raw output
  - [ ] Run AC-2 command — capture raw output
  - [ ] Decision: if both pass → skip Tasks 2 + 3, jump to Task 4
- [ ] Task 2: (Conditional) Re-run Ansible role on ct-dev-test FIRST (AC: idempotency, per `feedback_test_container.md`)
  - [ ] Confirm `ct-dev-test` (192.168.50.152) is present in the `ai_hosts` inventory group (the playbook targets `hosts: ai_hosts`); if not, either add it temporarily or skip ct-dev-test stage and document the deviation
  - [ ] Run `cd homelab-infra/ansible && ansible-playbook playbooks/deploy-ollama-models.yml --tags llama-server --limit ct-dev-test` (the playbook is `deploy-ollama-models.yml` which composes `ollama-models` + `llama-server` roles; the tag is `llama-server` with a hyphen)
  - [ ] Validate AC-1 + AC-2 against ct-dev-test
  - [ ] Run the playbook a SECOND time against ct-dev-test → confirm `changed=0` (idempotency)
- [ ] Task 3: (Conditional) Re-run Ansible role on ct-ai-01 (AC: 1, 2, 3, idempotency)
  - [ ] Take a Proxmox snapshot of CT 160 first: `ssh pve3 "pct snapshot 160 pre-vulkan-rebuild-$(date +%Y%m%d-%H%M)"`
  - [ ] Run `cd homelab-infra/ansible && ansible-playbook playbooks/deploy-ollama-models.yml --tags llama-server --limit ct-ai-01`
  - [ ] If the binary changed, role's handler should restart `llama-server.service`; otherwise restart manually: `ssh pve3 "pct exec 160 -- systemctl restart llama-server.service"`
  - [ ] Wait for `active (running)` state
  - [ ] Re-run AC-1 + AC-2 → confirm Vulkan now present
  - [ ] Run the playbook a SECOND time against ct-ai-01 → confirm `changed=0`
- [ ] Task 4: Post-verification smoke test (AC: 3, 4)
  - [ ] Run AC-3 curl from inside CT 160 against `127.0.0.1:8080`; capture response excerpt
  - [ ] In a parallel shell, run AC-4 (`radeontop`) for ~5 seconds spanning the inference window; capture GPU busy %
  - [ ] Confirm both are green
- [ ] Task 5: Capture evidence (AC: epic-doc-mandated artifact)
  - [ ] Create `homelab-playbook/_bmad-output/implementation-artifacts/llama-cpp-build-verification-2026-04.md` with: AC-1 raw output, AC-2 raw output, AC-3 response excerpt, AC-4 observation, llama.cpp commit/tag in use, date
- [ ] Task 6: Update sprint status (AC: tracking)
  - [ ] Edit `homelab-playbook/_bmad-output/implementation-artifacts/hybrid-gemma-serving-sprint-status.md`; mark Story 9.1 status `completed`, owner set, completion date today
  - [ ] Commit with conventional message (see Definition of Done)

## Test Plan

### Pre-deploy (per `feedback_test_container.md`)

If a rebuild is needed (Vulkan missing initially), the rebuild MUST run on `ct-dev-test` (192.168.50.152) FIRST. Only after the role passes there (binary present, Vulkan in version, idempotent on second run) can it run on `ct-ai-01`. If verification confirms Vulkan is already present (no rebuild needed), the test-container detour is not required.

### Smoke test command

From inside CT 160 (or via SSH jump):

```bash
ssh pve3 "pct exec 160 -- curl -s http://127.0.0.1:8080/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{
    \"model\":\"gemma-4-e4b\",
    \"messages\":[{\"role\":\"user\",\"content\":\"Say hello in one word.\"}],
    \"max_tokens\":16
  }'"
```

Expected: HTTP 200, JSON with `choices[0].message.content` non-empty (model name string in `model` may differ; the role doesn't set it — read whatever llama-server reports).

### Browser validation

Not required (per `feedback_browser_validation.md`). This is infrastructure-level verification, not feature-level UI work. Playwright MCP is reserved for the full multi-app flow validated in Story 9.20.

## Rollback Plan

1. **Pre-rebuild safeguards (Task 0 + Task 3):**
   - Captured: current `/opt/llama.cpp/build/bin/llama-server` sha256 + mtime.
   - Captured: Proxmox snapshot of CT 160 named `pre-vulkan-rebuild-<timestamp>`.
2. **If rebuild breaks E4B service or smoke test fails:**
   - Stop the service: `ssh pve3 "pct exec 160 -- systemctl stop llama-server.service"`.
   - Roll back the role change: `cd homelab-infra && git checkout -- ansible/roles/llama-server/`.
   - Restore binary from snapshot if needed: `ssh pve3 "pct rollback 160 pre-vulkan-rebuild-<timestamp>"` (this restores the entire CT — only use if the binary corruption blocks recovery).
   - Re-run the role to reach the prior known-good state.
3. **If only AC-3 (smoke test) fails but AC-1/2 pass:**
   - Capture journald logs: `ssh pve3 "pct exec 160 -- journalctl -u llama-server.service --no-pager -n 200"`.
   - Pause story, escalate, and update Risks before retrying.

## Risk Flags

- **Risk profile: LOW.** The most likely outcome is "Vulkan already present, no rebuild needed" — the existing role default is `llama_cpp_vulkan: true` and Epic 8 deployed it that way.
- **Only material risk:** if a rebuild IS needed and runs against the production CT, there is unavoidable E4B downtime during compilation (potentially several minutes on Strix-class hardware). Mitigation: snapshot first, run on `ct-dev-test` first, communicate the maintenance window if any other consumer (Open WebUI, Hermes, etc.) depends on the E4B endpoint right now.
- **Secondary risk (R3 from epics doc):** llama.cpp HEAD may have introduced a Vulkan build regression since the last successful build. Defaults pin `llama_cpp_version: HEAD` — if compile fails, pin to a known-good tag (e.g., `b5220` per the role's own comment) before retrying.

## Definition of Done

- [ ] AC-1 passes on `ct-ai-01` (Vulkan in `--version` backend list).
- [ ] AC-2 passes on `ct-ai-01` (Vulkan library linked per `ldd`).
- [ ] AC-3 passes on `ct-ai-01` (smoke `curl` returns coherent response on `:8080`).
- [ ] AC-4 passes on `ct-ai-01` (iGPU activity visible during inference).
- [ ] If a rebuild was needed: idempotency confirmed (second role run reports `changed=0`); ct-dev-test path was used first per `feedback_test_container.md`.
- [ ] Evidence file `homelab-playbook/_bmad-output/implementation-artifacts/llama-cpp-build-verification-2026-04.md` committed.
- [ ] Sprint status YAML updated; Story 9.1 marked `completed`.
- [ ] Conventional commit pushed, e.g.:
  - No-rebuild path: `chore(llama-server): verify Vulkan build present on ct-ai-01 (Story 9.1)`
  - Rebuild path: `fix(llama-server): rebuild with Vulkan on ct-ai-01 (Story 9.1)`

## Dev Notes

### Source tree components touched

- **Read-only:** `homelab-infra/ansible/roles/llama-server/defaults/main.yml`, `homelab-infra/ansible/roles/llama-server/templates/llama-server.service.j2`, `homelab-infra/ansible/roles/llama-server/tasks/main.yml` (verify the actual playbook tag — the epics doc uses `llama-server`, the defaults file is `llama-server`; confirm the tag in `tasks/main.yml` before running).
- **Write (only on completion):** `homelab-playbook/_bmad-output/implementation-artifacts/llama-cpp-build-verification-2026-04.md` (new evidence artifact); `homelab-playbook/_bmad-output/implementation-artifacts/hybrid-gemma-serving-sprint-status.md` (status update — mark Story 9.1 as `completed`).
- **Conditional write (only if rebuild needed):** none expected to source files; the role rebuilds the binary at `/opt/llama.cpp/build/bin/llama-server` inside the container — no repo files change unless the role itself needs a tweak (in which case treat that as scope expansion and pause for direction).

### Pattern: follow existing role exactly (per `feedback_correct_fix.md`)

Do NOT introduce a quick workaround (e.g., manually `cmake -DGGML_VULKAN=ON` inside the container). The fix must go through the existing Ansible role with the existing variable (`llama_cpp_vulkan: true`). If the role doesn't produce a Vulkan-enabled binary even with the flag, that's a role bug to fix in-place, not a story to ship around.

### Project Structure Notes

- Story file path matches the established `N-N-slug.md` convention (e.g., `8-3-setup-gpu-via-oculink-and-lxc-with-ollama.md`).
- Evidence file path matches the established `<topic>-<yyyy-mm>.md` convention (e.g., `media-recordsize-rewrite-2026-04-22.md`).
- No conflict with the unified project structure.

## References

- [Source: homelab-playbook/_bmad-output/planning-artifacts/hybrid-gemma-serving-epics.md#Story 9.1: Verify Vulkan build of llama.cpp on ct-ai-01]
- [Source: homelab-playbook/_bmad-output/planning-artifacts/hybrid-gemma-serving-architecture.md#ADR-001 — Vulkan/RADV backend mandatory]
- [Source: homelab-playbook/_bmad-output/planning-artifacts/hybrid-gemma-serving-architecture.md#Starter Template Evaluation — Inference Layer]
- [Source: homelab-infra/ansible/roles/llama-server/defaults/main.yml]
- [Source: homelab-infra/ansible/roles/llama-server/templates/llama-server.service.j2]
- [Source: homelab-playbook/_bmad-output/planning-artifacts/research/technical-hybrid-gemma-serving-research-2026-04-25.md — §Tech Stack Gotcha #1 (ROCm endless-loop bug)]
- [Source: https://github.com/ggml-org/llama.cpp/issues/21416 — llama.cpp ROCm endless-loop bug on gemma-4-26B-A4B / gfx1151]
- [Memory: ~/.claude/projects/-home-developer-workspace-homelab/memory/feedback_test_container.md — deploy to ct-dev-test before ct-ai-01]
- [Memory: ~/.claude/projects/-home-developer-workspace-homelab/memory/feedback_browser_validation.md — Playwright reserved for feature-level UI work]
- [Memory: ~/.claude/projects/-home-developer-workspace-homelab/memory/feedback_correct_fix.md — follow existing patterns exactly, not workarounds]
- [Memory: ~/.claude/projects/-home-developer-workspace-homelab/memory/project_pve3_local_llm.md — Epic 8 context, ct-ai-01 VMID 160 / pve3 / .160]

## Dev Agent Record

### Agent Model Used

_(populated by implementing agent)_

### Debug Log References

### Completion Notes List

### Change Log

### File List
