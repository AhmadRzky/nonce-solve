import json, time, sys
import multiprocessing as mp
sys.path.insert(0, '.')
from solvd_sat import build_clauses as dfa_clauses, verify

def densest_cells(board, k):
    w, h = board['width'], board['height']
    rowfill = [sum(r) for r in board['rows']]
    colfill = [sum(c) for c in board['cols']]
    scored = sorted(((rowfill[r] + colfill[c], r, c) for r in range(h) for c in range(w)), reverse=True)
    return [r * w + c + 1 for _, r, c in scored[:k]]

def run(job, clauses, board, assumptions, solver_name, outq):
    try:
        if solver_name == 'cadical':
            from pysat.solvers import Cadical153 as S
        elif solver_name == 'glucose':
            from pysat.solvers import Glucose4 as S
        else:
            from pysat.solvers import MapleCM as S
        with S(bootstrap_with=clauses) as s:
            ok = s.solve(assumptions=assumptions) if assumptions else s.solve()
            if ok:
                model = set(s.get_model())
                w, h = board['width'], board['height']
                grid = [[1 if (r * w + c + 1) in model else 0 for c in range(w)] for r in range(h)]
                if verify(grid, board):
                    outq.put(('SAT', grid)); return
            outq.put(('UNSAT', None))
    except Exception as e:
        outq.put(('ERR', str(e)[:200]))

def main():
    job = int(sys.argv[1]); budget = float(sys.argv[2])
    t0 = time.time()
    ch = json.load(open('board.json'))
    board = ch['boards'][0]
    if job <= 7:
        clauses, _ = dfa_clauses(board)
        cells = densest_cells(board, 3)
        assumptions = [cells[k] if (job >> k) & 1 else -cells[k] for k in range(3)]
        solver_name = 'cadical'
    elif job == 8:
        clauses, _ = dfa_clauses(board); assumptions = []; solver_name = 'glucose'
    elif job == 9:
        clauses, _ = dfa_clauses(board); assumptions = []; solver_name = 'maple'
    elif job == 10:
        clauses, _ = dfa_clauses(board); assumptions = []; solver_name = 'cadical'
    elif job == 11:
        from placement import build_clauses as pl
        clauses, _, _f = pl(board); assumptions = []; solver_name = 'cadical'
    elif job == 12:
        from placement import build_clauses as pl
        clauses, _, _f = pl(board); assumptions = []; solver_name = 'glucose'
    elif job == 13:
        from placement import build_clauses as pl
        clauses, _, _f = pl(board); assumptions = []; solver_name = 'maple'
    else:
        print('job', job, 'is CP-SAT, not fleet_solve'); return 3
    print('job %d | %s | clauses %d | assumptions %s | build %.1fs' % (job, solver_name, len(clauses), assumptions, time.time() - t0), flush=True)
    outq = mp.Queue()
    p = mp.Process(target=run, args=(job, clauses, board, assumptions, solver_name, outq))
    p.start()
    deadline = t0 + budget
    result = None
    while time.time() < deadline:
        try:
            result = outq.get(timeout=5); break
        except Exception:
            if not p.is_alive(): break
    if p.is_alive(): p.terminate()
    if result and result[0] == 'SAT':
        json.dump({'grid': result[1]}, open('grid.json', 'w'))
        open('result.txt', 'w').write('SAT job %d in %.1fs\n' % (job, time.time() - t0))
        print('SAT — grid.json written, %.1fs' % (time.time() - t0), flush=True)
        return 0
    open('result.txt', 'w').write('NORESULT job %d: %s after %.1fs\n' % (job, result, time.time() - t0))
    print('no result:', result, flush=True)
    return 2

if __name__ == '__main__':
    sys.exit(main())
