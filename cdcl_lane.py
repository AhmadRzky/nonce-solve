#!/usr/bin/env python3
# CDCL lane for the NONCE GH fleet (BP-guided fixed-var CaDiCaL, after the user's
# fixcdcl.py / cdcl_attack.py). Usage: python3 cdcl_lane.py <inst.json> <budget_sec> [status_file]
# - Runs BP (bp5.py, q=0.618 weights recipe) in-process; if BP alone solves -> solution.txt.
# - Else fixes top-|H| variables as CaDiCaL assumptions over a frac ladder (0.2..0.8, then
#   pure CDCL); on SAT merges the full model, verifies 0-unsat LOCALLY, and only then
#   writes solution.txt (atomic rename). UNSAT/timeout: solution.txt is never touched.
# - Status is written to a side file / stdout log only -- nothing here is appended to the
#   probSAT output stream, so result.txt's "best": parsing stays intact.
import json, os, sys, time
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
STATUS = {"state": "init"}


def set_status(path, **kw):
    STATUS.update(kw)
    if path:
        try:
            with open(path, "w") as f:
                f.write("cdcl_lane " + " ".join(f"{k}={v}" for k, v in STATUS.items()) + "\n")
        except Exception:
            pass


def write_solution(sol):
    tmp = "solution.txt.tmp"
    with open(tmp, "w") as f:
        f.write(sol + "\n")
    os.replace(tmp, "solution.txt")


def main():
    inst_path = sys.argv[1]
    budget = float(sys.argv[2]) if len(sys.argv) > 2 else 420
    status_file = sys.argv[3] if len(sys.argv) > 3 else "cdcl_status.txt"
    t0 = time.time()

    def left():
        return budget - (time.time() - t0)

    d = json.load(open(inst_path))
    cl = d["clauses"]
    n = int(d["variables"])
    C = np.array(cl)
    V = np.abs(C) - 1
    S = C > 0

    def unsat_of(a):
        x = np.array([int(c) for c in a], dtype=np.int8)
        return int((~((x[V] == 1) == S).any(1)).sum())

    set_status(status_file, state="bp", n=n)
    # ---- 1) BP in-process (bp5 module globals bind to sys.argv[1] = this instance) ----
    H = None
    try:
        sys.path.insert(0, HERE)
        import bp5
        x_best, us_best = bp5.bp(0.618, iters=120)
        print("bp unsat", us_best, "elapsed", round(time.time() - t0, 1), flush=True)
        if us_best == 0:
            a = "".join(map(str, [int(v) for v in x_best.tolist()]))
            if len(a) == n and unsat_of(a) == 0:
                write_solution(a)
                set_status(status_file, state="SAT_BP")
                return 0
        if os.path.exists("/tmp/bp_H.npy"):
            H = np.load("/tmp/bp_H.npy")
    except Exception as e:
        print("bp phase failed:", repr(e), flush=True)
    if H is None or len(H) != n:
        # fallback polarity: per-variable majority sign across the clause set
        H = np.zeros(n)
        for c in cl:
            for lit in c:
                H[abs(lit) - 1] += 1.0 if lit > 0 else -1.0
        print("bp fields unavailable; majority-sign fallback", flush=True)
    order = np.argsort(-np.abs(H))

    # ---- 2) CaDiCaL assumption ladder (fixcdcl approach) ----
    try:
        from pysat.solvers import Solver
    except Exception as e:
        set_status(status_file, state="NO_PYSAT", err=type(e).__name__)
        print("pysat unavailable:", repr(e), flush=True)
        return 4
    solver_name = None
    for cand in ("cadical195", "cadical153", "cd", "cadical"):
        try:
            with Solver(name=cand) as _s:
                pass
            solver_name = cand
            break
        except Exception:
            continue
    if not solver_name:
        set_status(status_file, state="NO_SOLVER")
        return 4
    set_status(status_file, state="cdcl", solver=solver_name)
    rate = 7000.0  # conflicts/sec estimate, recalibrated after each limited solve
    for frac in (0.2, 0.35, 0.5, 0.65, 0.8, 0.0):
        if left() < 25:
            set_status(status_file, state="TIMEOUT")
            print("cdcl budget exhausted", flush=True)
            return 5
        nf = int(frac * n)
        fixed = order[:nf]
        assum = [int(v + 1) if H[v] > 0 else -int(v + 1) for v in fixed]
        allow = max(20.0, min(left() - 20.0, 240.0))
        conf = int(rate * allow)
        t = time.time()
        try:
            with Solver(name=solver_name, bootstrap_with=cl) as s:
                s.conf_budget(conf)
                r = s.solve_limited(assumptions=assum)
                el = max(time.time() - t, 0.1)
                try:
                    used = s.accum_stats().get("conflicts")
                    if used:
                        rate = used / el
                except Exception:
                    pass
                print("frac", frac, "result", r, "elapsed", round(el, 1), "conf", conf, flush=True)
                if r:
                    mdl = s.get_model()
                    if mdl is None or len(mdl) < n:
                        continue
                    a = "".join("1" if mdl[i] > 0 else "0" for i in range(n))
                    bad = unsat_of(a)
                    print("verify unsat", bad, flush=True)
                    if bad == 0 and len(a) == n:
                        write_solution(a)
                        set_status(status_file, state="SAT_CDCL", frac=frac)
                        return 0
        except Exception as e:
            print("cdcl frac", frac, "failed:", repr(e), flush=True)
            continue
    set_status(status_file, state="NO_SAT")
    return 3


if __name__ == "__main__":
    sys.exit(main())
