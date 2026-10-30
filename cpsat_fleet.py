#!/usr/bin/env python3
"""
SOLVD alternative solver #2: OR-Tools CP-SAT with per-line automaton
constraints (regular constraint over each row/column of bool cell vars).

Usage: python3 cpsat_solve.py <challenge.json> <answer_out.json> <deadline_epoch>
Writes the answer ONLY if the grid verifies against all clues.
Exit codes: 0 solved+verified, 2 timeout, 3 error, 4 infeasible/unknown.
"""
import json
import sys
import time

sys.path.insert(0, "/home/hatch/workspace/tools/ortools-lib")
sys.path.insert(0, "/home/hatch/workspace/solvd-work/alt")
from alt_solve import verify  # noqa: E402


def line_automaton(model, vars_line, runs):
    """Add an automaton constraint forcing vars_line to match `runs`."""
    k = len(runs)
    # states: (j, 0) = gap before run j (j in 0..k); (j, t) = inside run j, t filled
    ids = {}

    def sid(state):
        if state not in ids:
            ids[state] = len(ids)
        return ids[state]

    triples = []
    for j in range(k + 1):
        triples.append((sid((j, 0)), 0, sid((j, 0))))  # stay in gap on 0
    for j in range(k):
        L = runs[j]
        triples.append((sid((j, 0)), 1, sid((j, 1))))  # start run j
        for t in range(1, L):
            triples.append((sid((j, t)), 1, sid((j, t + 1))))
        triples.append((sid((j, L)), 0, sid((j + 1, 0))))  # gap after full run
    finals = {sid((k, 0))}
    if k >= 1:
        finals.add(sid((k - 1, runs[k - 1])))
    model.add_automaton(vars_line, sid((0, 0)), list(finals), triples)


def main():
    if len(sys.argv) != 4:
        print(__doc__)
        return 3
    ch_path, out_path = sys.argv[1], sys.argv[2]
    deadline = time.time() + float(sys.argv[3])
    seed = int(sys.argv[4]) if len(sys.argv) > 4 else 1
    from ortools.sat.python import cp_model
    with open(ch_path) as f:
        ch = json.load(f)
    boards_out = []
    for bi, board in enumerate(ch["boards"]):
        w, h = board["width"], board["height"]
        t0 = time.time()
        model = cp_model.CpModel()
        x = [[model.new_bool_var(f"x_{r}_{c}") for c in range(w)] for r in range(h)]
        for r in range(h):
            line_automaton(model, x[r], board["rows"][r])
        for c in range(w):
            line_automaton(model, [x[r][c] for r in range(h)], board["cols"][c])
        t_build = time.time() - t0
        budget = deadline - time.time()
        if budget <= 5:
            print("deadline passed during build")
            return 2
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = budget
        solver.parameters.num_search_workers = 4
        solver.parameters.random_seed = seed
        t1 = time.time()
        status = solver.solve(model)
        t_solve = time.time() - t1
        print(f"[cpsat] board {bi}: build={t_build:.2f}s solve={t_solve:.2f}s "
              f"status={solver.status_name(status)}", flush=True)
        if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            return 4 if status == cp_model.INFEASIBLE else 2
        grid = [[1 if solver.value(x[r][c]) else 0 for c in range(w)] for r in range(h)]
        if not verify(grid, board):
            print("[cpsat] MODEL FAILED VERIFICATION")
            return 3
        boards_out.append(["".join(str(v) for v in row) for row in grid])
    with open("grid.json", "w") as f:
        json.dump({"grid": grid}, f)
    ans = {"challengeId": ch["challengeId"], "encoding": "bin", "boards": boards_out}
    with open(out_path, "w") as f:
        json.dump(ans, f)
    print("[cpsat] answer written (verified)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
