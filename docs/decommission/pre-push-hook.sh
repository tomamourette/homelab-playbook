#!/usr/bin/env bash
# Pre-push hook installed by Context Stack Sprint 1 / Epic E1 (FR-DEC-009 forward protection).
# Blocks pushes that would re-introduce OMEGA or MemPalace references.
# Per ADR-010 + sprint-1-verify-report.md.
#
# Canonical source: homelab-playbook/docs/decommission/pre-push-hook.sh
# Installed at .git/hooks/pre-push in: homelab (parent), homelab-infra, homelab-playbook
#
# Override (only for retro / decommission-archive commits): git push --no-verify

set -euo pipefail

# FR-DEC-009 forbidden patterns (case-sensitive — these are concrete identifiers, not prose)
PATTERNS='mempalace|MemPalace|omega-memory|omega_memory|ai-dev-omega-memory|ai-dev-mempalace|wire-mempalace|wire-omega|ai_dev_hermes_omega|ai_dev_hermes_mempalace'

# Documented historical-record exclusions (per FR-DEC-009 + sprint-1-verify-report.md).
# git grep -l returns paths relative to repo root (no leading /), so we anchor with ^ or
# match path segments. Exclusions: .claude-flow/, _bmad-output/, fix/260415*, docs/decommission/,
# docs/context-stack/ (BMAD product evidence + retros + scorecards reference decommissioned
# components in prose, not as re-introductions), wiki/ (knowledge base documents the same),
# any pending-insights.jsonl.
EXCLUDE_REGEX='(^|/)\.claude-flow/|(^|/)_bmad-output/|(^|/)fix/260415|(^|/)docs/decommission/|(^|/)docs/context-stack/|(^|/)wiki/|(^|/)pending-insights\.jsonl$'

# Run from repo root
REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"

HITS="$(git grep -lE "$PATTERNS" 2>/dev/null | grep -vE "$EXCLUDE_REGEX" || true)"

if [ -n "$HITS" ]; then
  echo "pre-push: FR-DEC-009 forward-protection hook BLOCKED push." >&2
  echo "  Forbidden OMEGA/MemPalace references found in:" >&2
  echo "$HITS" | sed 's/^/    - /' >&2
  echo >&2
  echo "  See homelab-playbook/docs/decommission/sprint-1-verify-report.md" >&2
  echo "  To override (retro/archive only, NOT recommended): git push --no-verify" >&2
  exit 1
fi

exit 0
