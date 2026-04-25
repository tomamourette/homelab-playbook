#!/usr/bin/env bash
# V3 RPO sampling loop — bounded, idempotent, with explicit timeouts
# Hard cap: 90 iterations × 10s = 900s wall-clock. Adds ~2-3s/iter SSH latency.
set -euo pipefail
trap 'echo "[$(date -u +%FT%TZ)] ERR at line $LINENO (exit=$?)" >> "${LOG:-/tmp/v3-sampler-err.log}"' ERR
EVIDENCE_DIR=/home/developer/workspace/homelab/homelab-playbook/_bmad-output/drill-evidence
DATE=$(date +%F)
CSV="$EVIDENCE_DIR/v3-ct162-rpo-${DATE}.csv"
LOG="$EVIDENCE_DIR/v3-ct162-rpo-${DATE}-loop.log"
SSH="ssh -i /home/developer/.ssh/homelab_ed25519 -o StrictHostKeyChecking=no -o ConnectTimeout=8"

echo "timestamp_iso,jobid,last_sync_epoch,now_epoch,age_seconds,state,fail_count" > "$CSV"
echo "[$(date -u +%FT%TZ)] sampler started, target 90 iterations × 10s" > "$LOG"

for i in $(seq 1 90); do
  NOW=$(date +%s)
  TS=$(date -u +%Y-%m-%dT%H:%M:%SZ)
  RAW=$(timeout 10 $SSH root@192.168.50.203 "pvesh get /nodes/pve3/replication --output-format json" 2>>"$LOG")
  if [ -z "$RAW" ]; then
    echo "[$(date -u +%FT%TZ)] iter=$i SSH timeout or empty payload" >> "$LOG"
    sleep 10
    continue
  fi
  # PVE 9 pvesh exposes .error (not .state); legacy column name kept for CSV schema continuity.
  echo "$RAW" | jq -r --arg now "$NOW" --arg ts "$TS" '
    .[] | select(.id | startswith("162-"))
      | [ $ts, .id, (.last_sync // 0), $now,
          (($now | tonumber) - (.last_sync // 0)),
          (.error // "ok"), (.fail_count // 0) ] | @csv' >> "$CSV"
  echo "[$(date -u +%FT%TZ)] iter=$i ok" >> "$LOG"
  sleep 10
done

echo "[$(date -u +%FT%TZ)] sampler complete, $(wc -l < "$CSV") CSV lines" >> "$LOG"
