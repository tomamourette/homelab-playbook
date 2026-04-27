#!/usr/bin/env bash
# homelab-playbook/scripts/weekly-digest.sh
#
# Weekly observability digest gather script (E4-S09).
#
# Aggregates K1-K6 KPIs, footprints, and tool-hit-rate into a markdown
# digest body printed to stdout. Operator pipes to a per-week file under
# `wiki/decisions/weekly-digest-<ISO-WEEK>.md`, refines the [TBD] prose
# rows, and commits.
#
# Idempotent — running twice in a minute produces deterministic output
# (no time-dependent randomness; same window snapshots the same data).
#
# All commands fall back to the "TBD" sentinel on failure so the digest
# never aborts mid-render. The operator manually fills any TBDs.
#
# Sources (per E4-S09 acceptance criteria + ADR-008 amendment):
#   K3 spend          → ct-ai-01:/var/log/cost-cap.log (NOT graphiti-cost-cap.log;
#                       ADR-008 amended path)
#   FalkorDB RSS      → ct-dev-homelab `docker stats falkordb`
#   GitNexus RSS      → workstation `docker stats gitnexus`
#   Reindex recency   → ~/.gitnexus-data/registry.json indexedAt
#   Tool-hit-rate     → ~/.claude/projects/*/sessions/*.jsonl grep
#
# Refer to wiki/runbooks/weekly-observability-digest.md for the operator
# procedure and per-KPI threshold definitions.
#
# Usage:
#   bash scripts/weekly-digest.sh                                    # print to stdout
#   bash scripts/weekly-digest.sh > wiki/decisions/weekly-digest-$(date -u +%Y-W%V).md
#
# Exit: 0 on completion (always; failures embedded as TBD sentinels).

set -uo pipefail

# Discover repo root for portable invocation.
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

WEEK="$(date -u +%Y-W%V)"          # display form (e.g., 2026-W18)
WEEK_SLUG="$(date -u +%Y-w%V)"     # slug-safe lowercase form (kebab-case lint rule)
TODAY="$(date -u +%Y-%m-%d)"
WEEK_AGO="$(date -u -d '7 days ago' +%Y-%m-%d)"

# Per ADR-008 amendment + Sprint 4 retro, log path is /var/log/cost-cap.log
# (the v1 spec name /var/log/graphiti-cost-cap.log was never the deployed
# path — ADR-008 amended source switch dropped the graphiti- prefix).
COST_CAP_LOG_REMOTE="/var/log/cost-cap.log"
CT_AI_01_HOST="${CT_AI_01_HOST:-192.168.50.160}"
CT_DEV_HOMELAB_HOST="${CT_DEV_HOMELAB_HOST:-192.168.50.156}"
SSH_KEY="${HOMELAB_SSH_KEY:-$HOME/.ssh/homelab_ed25switch}"
[ -f "$SSH_KEY" ] || SSH_KEY="$HOME/.ssh/homelab_ed25519"
SSH_OPTS="-i $SSH_KEY -o ConnectTimeout=5 -o StrictHostKeyChecking=no -o BatchMode=yes"

# ----- Footprint probes -----
falkordb_rss="$(ssh $SSH_OPTS root@"$CT_DEV_HOMELAB_HOST" \
  "docker stats --no-stream --format '{{.MemUsage}}' falkordb" 2>/dev/null \
  | awk -F' / ' '{print $1}' || true)"
[ -z "$falkordb_rss" ] && falkordb_rss="TBD"

# Workstation gitnexus RSS (container name 'gitnexus' on this host)
gitnexus_rss="$(docker stats --no-stream --format '{{.MemUsage}}' gitnexus 2>/dev/null \
  | awk -F' / ' '{print $1}' || true)"
[ -z "$gitnexus_rss" ] && gitnexus_rss="TBD"

# ----- K3 spend (week-window from cost-cap log) -----
# Sum the gemini_total_lifetime_usd values from log lines in window;
# weekly spend = (latest-in-window) - (earliest-in-window). Falls back
# to the latest single value if the window has only one tick. The log
# is on ct-ai-01.
k3_week_spend="$(ssh $SSH_OPTS root@"$CT_AI_01_HOST" \
  "awk -v from='$WEEK_AGO' -v to='$TODAY' '
    /gemini_total_lifetime_usd=/ {
      date = substr(\$0, 2, 10);
      if (date >= from && date <= to) {
        line = \$0;
        i = index(line, \"gemini_total_lifetime_usd=\");
        if (i > 0) {
          tail = substr(line, i + length(\"gemini_total_lifetime_usd=\"));
          n = tail + 0;
          if (start == \"\") start = n;
          end = n;
        }
      }
    }
    END {
      if (start == \"\" || end == \"\") { print \"TBD\"; }
      else { printf \"%.6f\", end - start; }
    }
  ' $COST_CAP_LOG_REMOTE 2>/dev/null" 2>/dev/null || true)"
[ -z "$k3_week_spend" ] && k3_week_spend="TBD"

# Latest lifetime spend (for context)
k3_lifetime="$(ssh $SSH_OPTS root@"$CT_AI_01_HOST" \
  "tail -200 $COST_CAP_LOG_REMOTE 2>/dev/null | awk -F'=' '/gemini_total_lifetime_usd=/ {v=\$NF} END {print v+0}'" 2>/dev/null || true)"
[ -z "$k3_lifetime" ] && k3_lifetime="TBD"

# Did any cap-breach happen in window?
k3_cap_breaches="$(ssh $SSH_OPTS root@"$CT_AI_01_HOST" \
  "awk -v from='$WEEK_AGO' '
    /throttled=true/ {
      date = substr(\$0, 2, 10);
      if (date >= from) c++;
    }
    END {print c+0}
  ' $COST_CAP_LOG_REMOTE 2>/dev/null" 2>/dev/null || echo 0)"
[ -z "$k3_cap_breaches" ] && k3_cap_breaches="0"

# K3 status
k3_status="TBD"
if [ "$k3_week_spend" != "TBD" ]; then
  if [ "$k3_cap_breaches" -gt 0 ]; then
    k3_status="R"
  else
    k3_status="$(awk -v s="$k3_week_spend" 'BEGIN{
      if (s > 7) print "R";
      else if (s > 5) print "A";
      else print "G";
    }')"
  fi
fi

# ----- GitNexus tool-hit-rate (week window) -----
# Counts JSON-RPC tool calls to gitnexus across this operator's session
# logs. The exact log layout depends on Claude Code's transcript
# location; we grep both common prefixes. Window-bounded by file mtime.
hit_count="$(find "$HOME/.claude/projects" -type f -name '*.jsonl' \
  -newermt "$WEEK_AGO" 2>/dev/null \
  -exec grep -c 'mcp__gitnexus\|"server":"gitnexus"' {} + 2>/dev/null \
  | awk -F: '{s+=$NF} END {print s+0}' || true)"
[ -z "$hit_count" ] && hit_count="0"

# K6 zero-week trigger (FR-OBS-006)
hit_status="G"
if [ "$hit_count" -eq 0 ] 2>/dev/null; then
  hit_status="R"  # CLAUDE.md review trigger
fi

# ----- K2 reindex recency (per-repo, from registry.json) -----
registry="$HOME/.gitnexus-data/registry.json"
k2_lines=""
if [ -f "$registry" ] && command -v jq >/dev/null 2>&1; then
  k2_lines="$(jq -r '.[] | "\(.name)|\(.indexedAt)|\(.stats.files)|\(.stats.nodes)"' "$registry" 2>/dev/null)"
fi
[ -z "$k2_lines" ] && k2_lines="TBD|TBD|TBD|TBD"

# ----- K4 facts/week (Graphiti — if reachable) -----
# Counts Episodic nodes in the operator's tom-personal namespace on
# ct-dev-homelab (production target). Note: at fresh-deploy time this
# returns ~0; the metric grows as the operator uses Graphiti.
k4_facts="$(ssh $SSH_OPTS root@"$CT_DEV_HOMELAB_HOST" \
  "docker exec falkordb redis-cli GRAPH.QUERY tom-personal 'MATCH (n:Episodic) RETURN count(n)' 2>/dev/null \
   | grep -A1 'count(n)' | tail -1 | tr -d ' '" 2>/dev/null || true)"
[ -z "$k4_facts" ] && k4_facts="TBD"

# ----- Footprint status (numeric extraction) -----
# Best-effort MiB parse from "57.53MiB" form; non-numeric → TBD-status
falkordb_mib="$(echo "$falkordb_rss" | sed -E 's/MiB$//; s/^[^0-9]+//' | head -c 8)"
gitnexus_mib="$(echo "$gitnexus_rss" | sed -E 's/MiB$//; s/^[^0-9]+//' | head -c 8)"
falkordb_status="$(awk -v v="$falkordb_mib" 'BEGIN{
  if (v == "" || v ~ /[^0-9.]/) print "TBD";
  else if (v < 200) print "G";
  else if (v < 250) print "A";
  else print "R";
}')"
gitnexus_status="$(awk -v v="$gitnexus_mib" 'BEGIN{
  if (v == "" || v ~ /[^0-9.]/) print "TBD";
  else if (v < 500) print "G";
  else if (v < 600) print "A";
  else print "R";
}')"

# ----- Recent commits (this week, all 3 sibling repos) -----
recent_commits=""
for r in homelab-apps homelab-infra homelab-playbook; do
  d="$HOME/workspace/homelab/$r"
  if [ -d "$d/.git" ]; then
    cnt="$(git -C "$d" log --since="$WEEK_AGO" --oneline 2>/dev/null | wc -l)"
    recent_commits="${recent_commits}- ${r}: ${cnt} commits this week\n"
  fi
done

# ----- Render -----
cat <<EOF
---
title: "Weekly observability digest — $WEEK"
slug: weekly-digest-$WEEK_SLUG
category: decisions
last_reviewed: $TODAY
owner: tomamourette
related_pages: [weekly-observability-digest]
related_frs: [FR-OBS-001, FR-OBS-004, FR-OBS-006]
related_adrs: [ADR-008, ADR-013]
status: stable
supersedes: []
superseded_by: null
---

## Summary

[1-2 sentences from operator: how the week went; standout signals.]

## Context

Pilot $WEEK. Stack state: GitNexus on workstation, Graphiti on ct-dev-homelab
(production target), wiki tier active, LiteLLM bridge: DEFERRED (FR-LLM-007
gate operator-pending). Source data window: $WEEK_AGO to $TODAY.

## Decision (KPI scorecard)

| KPI | Value | Threshold | Status |
|---|---|---|---|
| K1 token reduction | [TBD; 3 cross-repo Q&A samples this week] | >= 5x | [G/A/R] |
| K2 reindex time (incr.) | [TBD; from PostToolUse hook log] | <= 30 s | [G/A/R] |
| K2 reindex time (full) | [TBD] | <= 60 s | [G/A/R] |
| K3 spend (week) | \$$k3_week_spend (lifetime: \$$k3_lifetime; cap-breaches in window: $k3_cap_breaches) | <= \$5/wk | $k3_status |
| K4 facts/week (tom-personal) | $k4_facts | >= 25 | [G/A/R] |
| K5 good-catch tally | [TBD; manual operator-tag count] | >= 3 over 4 weeks | [G/A/R] |
| K6 subjective uplift | [TBD; 1-paragraph operator note] | "noticeable" by week 4 | [G/A/R] |
| FalkorDB RSS (ct-dev-homelab) | $falkordb_rss | < 200 MB | $falkordb_status |
| GitNexus daemon RSS (workstation) | $gitnexus_rss | < 500 MB | $gitnexus_status |
| GitNexus tool-hit-rate (week) | $hit_count calls | > 0/wk | $hit_status |

EOF

# K2 sub-table (per-repo reindex recency)
echo "## GitNexus reindex recency (registry.json)"
echo
echo "| Repo | Last indexed | Files | Nodes |"
echo "|---|---|---|---|"
if [ "$k2_lines" = "TBD|TBD|TBD|TBD" ]; then
  echo "| TBD | TBD | TBD | TBD |"
else
  echo "$k2_lines" | awk -F'|' '{ printf "| %s | %s | %s | %s |\n", $1, $2, $3, $4 }'
fi
echo

echo "## Recent commits (window: $WEEK_AGO -> $TODAY)"
echo
printf "%b" "$recent_commits"
echo

# CLAUDE.md review callout if hit-rate=0 (FR-OBS-006)
if [ "$hit_count" = "0" ]; then
  cat <<'EOF'
## CLAUDE.md review needed (FR-OBS-006)

GitNexus tool-hit-rate is 0 calls over the 7-day window. Per FR-OBS-006,
this triggers a CLAUDE.md review — verify the GitNexus section of
`~/.claude/CLAUDE.md` instructs Claude Code to use the gitnexus MCP for
cross-repo code-graph queries; if it does and the rate is still zero,
the operator's Q&A patterns may not be exercising cross-repo reasoning.

EOF
fi

# Cost-neutrality block (only if Phase 4 LiteLLM bridge active)
LITELLM_BRIDGE_ACTIVE="$(ssh $SSH_OPTS root@"$CT_DEV_HOMELAB_HOST" \
  "grep -q '^OPENAI_BASE_URL=http://hybrid-gemma\|^OPENAI_BASE_URL=.*litellm' /srv/graphiti/.env 2>/dev/null && echo yes || echo no" 2>/dev/null || echo "no")"
if [ "$LITELLM_BRIDGE_ACTIVE" = "yes" ]; then
  cat <<'EOF'
## Cost-neutrality (NFR-COST-003)

| Window | Spend | Notes |
|---|---|---|
| Pre-bridge (7-day) | [TBD] | from `tests/litellm-50-fact-summary-*.md` |
| Post-bridge (7-day) | [TBD] | this digest's K3 row |
| Status | [G if post <= pre; R otherwise] | |

EOF
fi

cat <<EOF
## Cross-references

- [Weekly digest template](weekly-observability-digest)
- [Cost cap (ADR-008)](git:_bmad-output/planning-artifacts/products/context-stack/adrs/ADR-008-daily-1-dollar-cap-implementation.md)
- [Tier of truth (ADR-013)](_schema)

## Notes

[Operator paragraph: lessons from the week; retro candidates for ADR-013
promotion to wiki proper or Graphiti add_episode.]
EOF
