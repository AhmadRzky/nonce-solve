#!/usr/bin/env bash
RUN=40571939357
for i in $(seq 1 16); do
  sleep 30
  n=$(gh api repos/AhmadRzky/nonce-solve/actions/runs/$RUN/jobs --jq '[.jobs[] | select(.status=="completed")] | length' 2>/dev/null)
  s=$(gh api repos/AhmadRzky/nonce-solve/actions/runs/$RUN/jobs --jq '[.jobs[] | select(.status=="in_progress")] | length' 2>/dev/null)
  a=$(gh api repos/AhmadRzky/nonce-solve/actions/runs/$RUN/artifacts --jq '.total_count' 2>/dev/null)
  echo "[$(date '+%H:%M:%S')] completed_jobs=$n in_progress=$s artifacts=$a"
done
rm -rf test_out && gh run download $RUN --dir test_out 2>&1 | tail -1
echo "--- sample results (sec should be ~30) ---"
grep -h '"sec"' test_out/*/result.txt 2>/dev/null | head -6
find test_out -name solution.txt | head -3
