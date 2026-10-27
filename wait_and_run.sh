#!/usr/bin/env bash
# args: <seed_base> <max_budget_sec> <wait_min>
set -u
SEED_BASE=${1:-0}
MAXBUDGET=${2:-420}
WAITMIN=${3:-12}
git config user.email "solver@local"; git config user.name "solver"
start_wait=$(date +%s)
deadline=""
while :; do
  git pull -q origin main 2>/dev/null || true
  if [ -f go.txt ]; then deadline=$(tr -dc '0-9' < go.txt); [ -n "$deadline" ] && break; fi
  now=$(date +%s)
  [ $((now - start_wait)) -ge $((WAITMIN * 60)) ] && { echo "wait timeout, no go.txt"; exit 0; }
  sleep 10
done
now=$(date +%s)
remain=$((deadline - now - 45))
budget=$MAXBUDGET
[ "$remain" -lt "$budget" ] && budget=$remain
echo "go received: deadline=$deadline now=$now budget=$budget"
[ "$budget" -lt 30 ] && { echo "budget too small"; exit 0; }
bash run_job.sh "$SEED_BASE" "$budget"
