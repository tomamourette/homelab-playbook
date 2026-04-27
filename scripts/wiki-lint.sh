#!/usr/bin/env bash
# homelab-playbook/scripts/wiki-lint.sh
#
# Wiki schema lint per ADR-006 / wiki/_schema.md.
#
# Validates each wiki/**/*.md file for:
#   1. YAML frontmatter present (between leading --- markers)
#   2. All required frontmatter keys present
#   3. slug matches filename (without .md), kebab-case-or-underscore
#   4. category in allow-list
#   5. last_reviewed is ISO YYYY-MM-DD
#   6. status in {draft, stable, superseded}
#
# Soft warning (does NOT fail): last_reviewed older than 6 months.
#
# Exit codes:
#   0 = all hard rules pass (warnings allowed)
#   1 = at least one hard-rule failure
#   2 = environment / invocation error
#
# Usage:
#   scripts/wiki-lint.sh                 # lint full wiki tree
#   scripts/wiki-lint.sh path1.md ...    # lint specific files (used by pre-commit)
set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo "")"
if [ -z "$REPO_ROOT" ]; then
  echo "FAIL: not in a git work tree" >&2
  exit 2
fi

WIKI_DIR="$REPO_ROOT/wiki"
if [ ! -d "$WIKI_DIR" ]; then
  echo "FAIL: wiki dir not found at $WIKI_DIR" >&2
  exit 2
fi

# Choose targets: argv if provided, otherwise the full tree.
if [ "$#" -gt 0 ]; then
  TARGETS=("$@")
else
  # Use find + mapfile so spaces in paths survive.
  mapfile -t TARGETS < <(find "$WIKI_DIR" -type f -name '*.md' | sort)
fi

if [ "${#TARGETS[@]}" -eq 0 ]; then
  echo "wiki-lint: no markdown files to check"
  exit 0
fi

# Hand off to embedded Python (PyYAML required; available system-wide).
PY=$(command -v python3 || command -v python || true)
if [ -z "$PY" ]; then
  echo "FAIL: python3 not found in PATH (required for wiki-lint)" >&2
  exit 2
fi

exec "$PY" - "$WIKI_DIR" "${TARGETS[@]}" <<'PYEOF'
"""Embedded Python lint body for wiki-lint.sh."""
import datetime as _dt
import os
import re
import sys

try:
    import yaml  # PyYAML
except ImportError:
    sys.stderr.write("FAIL: PyYAML not installed (pip install pyyaml)\n")
    sys.exit(2)

VALID_CATEGORIES = {
    "architecture",
    "runbooks",
    "decisions",
    "glossary",
    "projects",
    "meta",
}
VALID_STATUS = {"draft", "stable", "superseded"}
REQUIRED_KEYS = [
    "title",
    "slug",
    "category",
    "last_reviewed",
    "owner",
    "related_pages",
    "related_frs",
    "related_adrs",
    "status",
    "supersedes",
    "superseded_by",
]
SLUG_RE = re.compile(r"^_?[a-z0-9]+(?:[-_][a-z0-9]+)*$")
ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)

STALE_DAYS = 183  # ~6 months


def parse_frontmatter(text):
    m = FRONTMATTER_RE.match(text)
    if not m:
        return None, "no leading YAML frontmatter (file must start with '---')"
    raw = m.group(1)
    try:
        data = yaml.safe_load(raw)
    except yaml.YAMLError as exc:
        return None, f"malformed YAML frontmatter: {exc}"
    if not isinstance(data, dict):
        return None, "frontmatter is not a YAML mapping"
    return data, None


def lint_file(path, wiki_root):
    errors = []
    warnings = []

    try:
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
    except OSError as exc:
        return [f"cannot read file: {exc}"], []

    fm, err = parse_frontmatter(text)
    if err:
        return [err], []

    # Required keys
    for key in REQUIRED_KEYS:
        if key not in fm:
            errors.append(f"missing required frontmatter key: {key}")
    if errors:
        return errors, warnings

    # Slug == filename (without .md)
    expected_slug = os.path.splitext(os.path.basename(path))[0]
    slug = fm.get("slug")
    if not isinstance(slug, str) or not slug:
        errors.append("slug must be a non-empty string")
    else:
        if slug != expected_slug:
            errors.append(
                f"slug '{slug}' does not match filename '{expected_slug}'"
            )
        elif not SLUG_RE.match(slug):
            errors.append(
                f"slug '{slug}' must be kebab-case (a-z, 0-9, -, _; optional leading '_')"
            )

    # Category
    cat = fm.get("category")
    if cat not in VALID_CATEGORIES:
        errors.append(
            f"category '{cat}' not in allow-list "
            f"({', '.join(sorted(VALID_CATEGORIES))})"
        )

    # last_reviewed: ISO YYYY-MM-DD; warn if > STALE_DAYS old.
    lr = fm.get("last_reviewed")
    lr_str = None
    if isinstance(lr, _dt.date):
        # PyYAML auto-parses YYYY-MM-DD into datetime.date; that's fine.
        lr_str = lr.isoformat()
        lr_date = lr
    elif isinstance(lr, str):
        lr_str = lr
        if not ISO_DATE_RE.match(lr):
            errors.append(
                f"last_reviewed '{lr}' must be ISO YYYY-MM-DD"
            )
            lr_date = None
        else:
            try:
                lr_date = _dt.date.fromisoformat(lr)
            except ValueError as exc:
                errors.append(f"last_reviewed '{lr}' is not a valid date: {exc}")
                lr_date = None
    else:
        errors.append(
            f"last_reviewed must be a date or ISO YYYY-MM-DD string, got {type(lr).__name__}"
        )
        lr_date = None

    if lr_date is not None:
        age_days = (_dt.date.today() - lr_date).days
        if age_days > STALE_DAYS:
            warnings.append(
                f"last_reviewed {lr_str} is {age_days} days old (>{STALE_DAYS}); review recommended"
            )

    # Status
    status = fm.get("status")
    if status not in VALID_STATUS:
        errors.append(
            f"status '{status}' not in {{{', '.join(sorted(VALID_STATUS))}}}"
        )

    return errors, warnings


def main(argv):
    wiki_root = argv[1]
    targets = argv[2:]

    total = 0
    failed = 0
    warned = 0

    for path in targets:
        # Only lint files inside the wiki tree.
        ap = os.path.abspath(path)
        if not ap.startswith(os.path.abspath(wiki_root) + os.sep) and ap != os.path.abspath(wiki_root):
            # Pre-commit may pass paths outside scope; skip silently.
            continue
        if not os.path.isfile(ap):
            continue
        if not ap.endswith(".md"):
            continue

        total += 1
        rel = os.path.relpath(ap, os.path.dirname(wiki_root))
        errs, warns = lint_file(ap, wiki_root)

        for w in warns:
            print(f"WARN: {rel}: {w}")
        for e in errs:
            print(f"FAIL: {rel}: {e}", file=sys.stderr)

        if warns:
            warned += 1
        if errs:
            failed += 1

    print(
        f"wiki-lint: pages={total} failed={failed} warnings={warned}"
    )
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main(sys.argv)
PYEOF
