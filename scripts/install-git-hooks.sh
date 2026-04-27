#!/usr/bin/env bash
# Install pre-commit hooks for homelab-playbook (wiki lint, etc).
#
# Idempotent: re-running just re-installs the hook bindings.
#
# Requires the `pre-commit` framework (https://pre-commit.com/).
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

if ! command -v pre-commit >/dev/null 2>&1; then
  cat >&2 <<EOF
ERROR: 'pre-commit' is not installed.

Install one of:
  - apt:  sudo apt install pre-commit
  - pip:  pipx install pre-commit  (or  pip install --user pre-commit)
  - brew: brew install pre-commit

Then re-run this script.
EOF
  exit 1
fi

pre-commit install
echo
echo "Hooks installed. Smoke-test with:"
echo "  pre-commit run --all-files"
