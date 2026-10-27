#!/usr/bin/env bash
RUN=40570089799
for i in $(seq 1 40); do
  st=$(gh run view $RUN --json status,conclusion,createdAt,startedAt,updatedAt --jq '"\(.status) \(.conclusion // "-") created=\(.createdAt) started=\(.startedAt) updated=\(.updatedAt)"' 2>/dev/null)
  echo "[$(date '+%H:%M:%S')] $st"
  echo "$st" | grep -q '^completed' && break
  sleep 15
done
echo "--- JOBS ---"
gh run view $RUN --json jobs --jq '.jobs | length as $n | "jobs: \($n)", (.jobs[] | "\(.name) \(.status)/\(.conclusion // "-") queue_wait_s=\(((.startedAt|fromdateiso8601) - (.createdAt|fromdateiso8601))) run_s=\((((.completedAt // .startedAt)|fromdateiso8601) - (.startedAt|fromdateiso8601)))")' 2>&1 | head -25
echo "--- ARTIFACTS ---"
rm -rf rehearsal_out && gh run download $RUN --dir rehearsal_out 2>&1 | tail -2
find rehearsal_out -name 'solution.txt' | head; echo "solutions above (none expected)"
grep -h '"best"' rehearsal_out/*/result.txt 2>/dev/null | head -8
grep -h 'solved_by' rehearsal_out/*/result.txt 2>/dev/null | head -3
