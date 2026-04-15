# Deferred Work

## Deferred from: code review of 0-4-build-doc-update-skill-update-mode (2026-04-04)

- **W1: Date fallback baseline unreliable** — File modification dates (mtime) vary across git clones, CI environments, and containers. The fallback in Phase 1 step 1 that uses oldest doc mtime as baseline can produce wrong results. Pre-existing from Story 0-3 check mode.
- **W2: Unbounded source file contents in template** — If a large refactor touches many files, `{source_file_contents}` in the section update prompt can overflow LLM context limits. Needs architectural decision about chunking/prioritization strategy.
- **W3: Mode detection keyword ambiguity** — When user input contains multiple trigger words (e.g., "check if docs need a full update"), no priority rule determines which mode wins. Pre-existing in workflow.md.
- **W4: Multi-repo git detection** — `git log` only works in a single repo. The mapping file references paths across `homelab-infra/`, `homelab-apps/`, `homelab-playbook/` but change detection only runs in the current working directory. Architectural constraint of the current design.

## Deferred from: code review of 0-5-build-doc-update-skill-full-mode-and-mapping (2026-04-04)

- **W1: Mode detection keyword ambiguity/priority** — Same as 0-4 W3. When multiple keywords match (e.g., "check if full update needed"), no priority rule. Pre-existing.
- **W2: project_knowledge path never validated** — The resolved docs folder path is used throughout but never checked for existence. If directory missing, modes fail silently. Pre-existing design pattern.
- **W3: No schema definition for project-scan-report.json** — Different modes write different fields with no canonical schema. Risk of inconsistent structures across modes. Architectural concern.
- **W4: Concurrency across modes** — No guard prevents running check while full is in progress. Unrealistic for single-user skill but noted.

## Deferred from: code review of 3-1-install-hermes-agent-and-configure-basics (2026-04-14)

- **D1: Runbook step order** — Prometheus targets file is copied (step 2) before node-exporter is deployed (step 3), causing brief scrape errors in the 60s reload window. Low impact, self-healing.
- **D2: Manual cp step lacks idempotency guard** — The cross-repo copy from homelab-infra to homelab-apps has no automation or path validation. Needs Ansible task or CI step.
- **D3: No documented opt-out for monitoring_enabled** — monitoring_enabled defaults to true but there is no documented example of setting it to false. Belongs in infra repo Terraform variable docs.
- **D4: No container decommission monitoring procedure** — Runbook covers adding containers but not removing them from Prometheus targets after terraform destroy.

## Deferred from: code review of 3-2-configure-omega-mcp-connection-and-bmad-skills (2026-04-14)

- **D1: Copy task overwrites user-customized skill files** — `configure-skills.yml` has no `force: no`. Re-runs overwrite manual edits to SKILL.md stubs. Deferred because stubs are not meant for customization; Story 3.3 will replace them.
- **D2: No negative assertion for stale MCP entry** — If OMEGA is removed after a prior run, verify.yml skips the MCP check (conditional on OMEGA presence) and cannot detect a stale mcp_servers block. Template re-render handles removal, so verify is supplementary.
- **D3: Broken pyenv shim passes stat but fails at runtime** — stat only checks file existence, not that the shim resolves to a working Python binary. A broken shim (`pyenv version uninstall`) would cause Hermes MCP spawn errors.
- **D4: verify.yml uses shell instead of command for grep** — `VERIFY | OMEGA MCP entry` uses `ansible.builtin.shell` where `lineinfile` with `check_mode` would be cleaner. Low priority.
- **D5: Copy deploys temp/editor backup files** — `ansible.builtin.copy src: "skills/"` copies everything including potential `.swp`, `.DS_Store` files. No exclude mechanism in Ansible copy. Currently no temp files in the directory.
