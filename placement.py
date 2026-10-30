#!/usr/bin/env python3
"""
SOLVD alternative solver: placement (order-encoded run-start) CNF + CaDiCaL.

Encoding per line (length n, runs L[0..k-1]):
  For each run j, integer start_j in [lo_j, hi_j] is represented by
  order-encoded booleans v_j[p] = (start_j <= p) for p in [lo_j, hi_j],
  with a unit forcing v_j[hi_j] and monotonicity clauses. B(j,q) denotes
  the (possibly constant) literal for (start_j <= q) under this encoding.
  Ordering:  start_{j+1} >= start_j + L_j + 1
             <=>  B(j+1, p) -> B(j, p - L_j - 1)   for all p.
  Coverage:  cell c of the line is filled iff some run covers it:
             cov_j(c) = B(j, c) AND NOT B(j, c - L_j)   (aux var if needed)
             x_c <-> OR_j cov_j(c).
Cell variables are shared between the row-line and column-line encodings,
which is the only coupling (same numbering as solvd_sat.py: r*w + c + 1).

Usage:
  python3 alt_solve.py <challenge.json> <answer_out.json> <deadline_epoch>
Writes the answer file ONLY if the grid verifies against all clues.
Exit codes: 0 solved+verified, 2 timeout, 3 build/solve error, 4 UNSAT.
"""
import json
import os
import subprocess
import sys
import time

sys.path.insert(0, "/home/hatch/workspace/tools/pysat-lib")

FALSE = 0          # literal sentinel: constant False
TRUE = 1 << 30     # literal sentinel: constant True (far above any real var)


def verify(grid, board):
    """True iff grid satisfies every row and column clue."""
    h = board["height"]
    w = board["width"]
    for r in range(h):
        runs = []
        cnt = 0
        for c in range(w):
            if grid[r][c] == 1:
                cnt += 1
            elif cnt:
                runs.append(cnt)
                cnt = 0
        if cnt:
            runs.append(cnt)
        if runs != board["rows"][r]:
            return False
    for c in range(w):
        runs = []
        cnt = 0
        for r in range(h):
            if grid[r][c] == 1:
                cnt += 1
            elif cnt:
                runs.append(cnt)
                cnt = 0
        if cnt:
            runs.append(cnt)
        if runs != board["cols"][c]:
            return False
    return True


class Builder:
    def __init__(self):
        self.clauses = []
        self.nvars = 0

    def new_var(self):
        self.nvars += 1
        return self.nvars

    def add(self, lits):
        """Add a clause of literals (ints; FALSE/TRUE sentinels allowed).
        Drops FALSE literals, skips satisfied clauses, detects tautologies."""
        out = []
        seen = set()
        for lit in lits:
            if lit == TRUE:
                return
            if lit == FALSE:
                continue
            if -lit in seen:
                return  # tautology
            if lit not in seen:
                seen.add(lit)
                out.append(lit)
        self.clauses.append(out)


def encode_line(bd, cells, runs):
    """cells: list of cell var ids (length n). runs: clue list."""
    n = len(cells)
    k = len(runs)
    add = bd.add
    if k == 0:
        for x in cells:
            add([-x])
        return
    # feasible start ranges:
    #   lo_j = sum_{i<j} (runs[i] + 1)
    #   hi_j = n - runs[j] - sum_{i>j} (runs[i] + 1)
    lo = [0] * k
    hi = [0] * k
    s = 0
    for j in range(k):
        lo[j] = s
        s += runs[j] + 1
    suf = 0
    for j in range(k - 1, -1, -1):
        hi[j] = n - suf - runs[j]
        suf += runs[j] + 1
    # order-encoded start vars
    V = []  # V[j] = dict p -> var for p in [lo_j, hi_j]
    for j in range(k):
        d = {}
        for p in range(lo[j], hi[j] + 1):
            d[p] = bd.new_var()
        V.append(d)
        add([d[hi[j]]])  # start_j <= hi_j
        for p in range(lo[j], hi[j]):
            add([-d[p], d[p + 1]])  # monotone

    def B(j, q):
        """Literal for (start_j <= q)."""
        if q < lo[j]:
            return FALSE
        if q > hi[j]:
            return TRUE
        return V[j][q]

    # ordering between consecutive runs (sentinel-safe)
    for j in range(k - 1):
        Lj = runs[j]
        for p in range(0, n):
            b_next = B(j + 1, p)
            if b_next == FALSE:
                continue
            b_prev = B(j, p - Lj - 1)
            if b_prev == TRUE:
                continue
            if b_next == TRUE:
                add([b_prev])        # unit (empty clause if b_prev == FALSE)
            elif b_prev == FALSE:
                add([-b_next])       # unit
            else:
                add([-b_next, b_prev])
    # coverage / channeling
    for c in range(n):
        x = cells[c]
        covs = []
        for j in range(k):
            Lj = runs[j]
            a = B(j, c)          # start_j <= c
            if a == FALSE:
                continue
            bb = B(j, c - Lj)    # start_j <= c - Lj
            if bb == TRUE:
                continue  # run ends before c
            # cov = a AND (not bb)
            if a == TRUE and bb == FALSE:
                add([x])  # run j forced to cover c
                covs = None
                break
            if a == TRUE:
                cov = -bb
            elif bb == FALSE:
                cov = a
            else:
                aux = bd.new_var()
                add([-aux, a])
                add([-aux, -bb])
                add([aux, -a, bb])
                cov = aux
            covs.append(cov)
            add([-cov, x])  # cov -> x
        if covs is not None:
            if not covs:
                add([-x])
            else:
                add([-x] + covs)  # x -> OR covs


def build_clauses(board, cell_offset=0):
    """Return (clauses, n_vars, cell_var_fn) for one board.
    Cell vars occupy [cell_offset+1, cell_offset + w*h]."""
    h = board["height"]
    w = board["width"]
    bd = Builder()
    bd.nvars = cell_offset + w * h  # reserve cell vars

    def cell(r, c):
        return cell_offset + r * w + c + 1

    for r in range(h):
        encode_line(bd, [cell(r, c) for c in range(w)], board["rows"][r])
    for c in range(w):
        encode_line(bd, [cell(r, c) for r in range(h)], board["cols"][c])
    return bd.clauses, bd.nvars, cell


def solve_board(board, time_budget, cell_offset=0):
    """Solve one board. Returns (grid_or_None, phase_times_dict)."""
    from pysat.solvers import Cadical153
    t0 = time.time()
    clauses, nvars, cell = build_clauses(board, cell_offset)
    t_build = time.time() - t0
    t1 = time.time()
    solver = Cadical153(bootstrap_with=clauses)
    t_boot = time.time() - t1
    t2 = time.time()
    ok = solver.solve()
    t_solve = time.time() - t2
    times = {"build": t_build, "bootstrap": t_boot, "solve": t_solve,
             "vars": nvars, "clauses": len(clauses)}
    if not ok:
        solver.delete()
        return None, times
    model = set(solver.get_model())
    solver.delete()
    w = board["width"]
    h = board["height"]
    grid = [[1 if cell(r, c) in model else 0 for c in range(w)] for r in range(h)]
    return grid, times


def worker(ch_path, out_path):
    """Subprocess entry: solve and write answer file if verified."""
    with open(ch_path) as f:
        ch = json.load(f)
    boards_out = []
    for bi, board in enumerate(ch["boards"]):
        grid, times = solve_board(board, None, cell_offset=bi * 10_000_000)
        print(f"[worker] board {bi}: " +
              " ".join(f"{k}={v:.2f}" if isinstance(v, float) else f"{k}={v}"
                       for k, v in times.items()), flush=True)
        if grid is None:
            print("[worker] UNSAT", flush=True)
            return 4
        if not verify(grid, board):
            print("[worker] MODEL FAILED VERIFICATION", flush=True)
            return 3
        boards_out.append(["".join(str(v) for v in row) for row in grid])
    ans = {"challengeId": ch["challengeId"], "encoding": "bin",
           "boards": boards_out}
    with open(out_path, "w") as f:
        json.dump(ans, f)
    print("[worker] answer written (verified)", flush=True)
    return 0


def main():
    if len(sys.argv) >= 2 and sys.argv[1] == "--worker":
        sys.exit(worker(sys.argv[2], sys.argv[3]))
    if len(sys.argv) != 4:
        print(__doc__)
        return 3
    ch_path, out_path = sys.argv[1], sys.argv[2]
    deadline = float(sys.argv[3])
    budget = deadline - time.time()
    if budget <= 5:
        print("deadline already passed")
        return 2
    t0 = time.time()
    proc = subprocess.Popen(
        [sys.executable, os.path.abspath(__file__), "--worker", ch_path, out_path])
    try:
        rc = proc.wait(timeout=budget)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()
        print(f"TIMEOUT after {time.time() - t0:.1f}s (budget {budget:.0f}s)")
        return 2
    print(f"worker rc={rc} wall={time.time() - t0:.1f}s")
    return rc


if __name__ == "__main__":
    sys.exit(main())
