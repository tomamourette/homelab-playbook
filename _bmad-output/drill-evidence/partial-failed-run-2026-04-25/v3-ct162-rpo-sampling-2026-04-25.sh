#!/bin/bash
# V3 drill — RPO sampling loop for ct:162
# Story 6.5 AC-3: 15-minute observation, 10s interval, 90 samples per leg
#
# IMPORTANT FINDING: replication schedule for 162-0/162-1 is */15 (NOT */1).
# This sampling captures observed reality, not the story-file's */1 hypothesis.
# Pass/fail interpreted against the actual cadence — see summary md.

set -u
EVIDENCE_DIR="/home/developer/workspace/homelab/homelab-playbook/_bmad-output/drill-evidence"
DATE="2026-04-25"
CSV="$EVIDENCE_DIR/v3-ct162-rpo-sampling-$DATE.csv"

echo "timestamp_iso,jobid,last_sync_epoch,now_epoch,age_seconds,state,fail_count" > "$CSV"

for i in $(seq 1 90); do
  NOW=$(date +%s)
  TS=$(date -u +%Y-%m-%dT%H:%M:%SZ)
  ssh -i ~/.ssh/homelab_ed25519 -o StrictHostKeyChecking=no -o BatchMode=yes \
      root@192.168.50.203 "pvesh get /nodes/pve3/replication --output-format json" 2>/dev/null \
    | jq -r --arg now "$NOW" --arg ts "$TS" '
        .[] | select(.id | startswith("162-"))
          | [$ts, .id, (.last_sync // 0), ($now | tonumber),
             (($now | tonumber) - (.last_sync // 0)),
             .state, .fail_count] | @csv' >> "$CSV"
  sleep 10
done

echo "Sampling complete: $(wc -l < "$CSV") lines (incl header)"
