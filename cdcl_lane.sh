#!/usr/bin/env bash
# CDCL lane launcher: deps (numpy + python-sat) -> cdcl_lane.py. Best-effort Kissat
# binary is fetched for the log/fallback record; the fixcdcl mode needs python-sat
# assumptions, so CaDiCaL via python-sat is the working backend.
# args: <budget_sec>
set -u
BUDGET=${1:-420}
T0=$(date +%s)
python3 -c 'import numpy' 2>/dev/null || pip install -q numpy 2>&1 | tail -1
python3 -c 'from pysat.solvers import Solver' 2>/dev/null || pip install -q python-sat 2>&1 | tail -1
# Kissat prebuilt (linux-amd64) -- fetched opportunistically; not required by the lane.
if [ ! -x ./kissat ]; then
  ( curl -sL --max-time 60 -o /tmp/kissat.zip https://github.com/arminbiere/kissat/releases/download/rel-4.0.4/kissat-4.0.4-linux-amd64.zip \
    && python3 -m zipfile -e /tmp/kissat.zip /tmp/kissat_x && cp /tmp/kissat_x/kissat ./kissat && chmod +x ./kissat && echo "kissat ready: $(./kissat --version 2>/dev/null | head -1)" ) 2>/dev/null \
    || echo "kissat fetch skipped/failed (lane continues on CaDiCaL)"
fi
NOW=$(date +%s)
REM=$((BUDGET - (NOW - T0) - 5))
[ "$REM" -lt 30 ] && { echo "cdcl lane: no time left after setup"; echo "cdcl_lane state=NO_TIME" > cdcl_status.txt; exit 0; }
timeout --signal=TERM $((REM + 15)) python3 cdcl_lane.py inst.json "$REM" cdcl_status.txt
echo "cdcl lane exit=$?"
