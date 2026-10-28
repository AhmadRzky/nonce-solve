#!/usr/bin/env bash
# args: <seed_base> <budget_sec>
set -u
SEED_BASE=${1:-0}
BUDGET=${2:-420}
node cnf2json.mjs inst.cnf
mkdir -p out
pids=()
for k in 0 1 2 3; do
  seed=$((SEED_BASE + k))
  node probsat.js inst.json "$BUDGET" "$seed" 5.0 > "out/out_${seed}.txt" 2>&1 &
  pids+=($!)
done
solved=""
for i in $(seq 1 $((BUDGET + 30))); do
  for k in 0 1 2 3; do
    seed=$((SEED_BASE + k))
    if grep -qE '^[01]{1536}$' "out/out_${seed}.txt" 2>/dev/null; then
      grep -oE '^[01]{1536}$' "out/out_${seed}.txt" | head -1 > solution.txt
      solved=$seed
      break 2
    fi
  done
  alive=0
  for p in "${pids[@]}"; do kill -0 "$p" 2>/dev/null && alive=1; done
  [ "$alive" = "0" ] && break
  sleep 2
done
for p in "${pids[@]}"; do kill "$p" 2>/dev/null; done
wait 2>/dev/null
echo "job seed_base=$SEED_BASE solved_by=${solved:-none}" > result.txt
cat out/out_*.txt >> result.txt 2>/dev/null
ls -la solution.txt 2>/dev/null || echo "no solution"
