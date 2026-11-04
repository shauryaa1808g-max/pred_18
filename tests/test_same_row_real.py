"""Same-row perturbation test on REAL data (replaces the weaker truncation/shuffle tests as the leakage guard; audit finding F1).
For several rows t: history up to t-1 is real, row t is replaced by two different garbage versions (A, B).  Every forecast for row t
(scale models S0-S6 for R/G/I, range models, location features, ridge, logit) must be IDENTICAL across A and B.
Positive control: with a deliberately injected same-session leak the forecasts must DIFFER, otherwise the test is blind.
Run: python3 tests/test_same_row_real.py   (about 5-8 minutes)"""
import pickle, subprocess, sys
from pathlib import Path
import numpy as np
repo = Path(__file__).resolve().parents[1]; tmp = Path("/tmp/same_row_test"); tmp.mkdir(exist_ok=True)
rows = [1100, 1500, 2100, 2386]            # incl. rows around the 2022 and 2025 bonus dates and the last row
def launch(i0, v, inject=False):
    name = f"r{i0}_{v}{'_inj' if inject else ''}"
    cmd = [sys.executable, "-I", str(repo / "tests" / "_same_row_runner.py"), str(i0), v, str(tmp / name)] + (["inject"] if inject else [])
    return name, subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
def run_all(inject):
    procs = [launch(i, v, inject) for i in rows for v in ("A", "B")]
    for n, p in procs:
        o = p.communicate()[0]
        assert p.returncode == 0, f"{n} failed:\n{o[-800:]}"
    res = {}
    for i in rows:
        a = pickle.load(open(tmp / f"r{i}_A{'_inj' if inject else ''}.pkl", "rb")); b = pickle.load(open(tmp / f"r{i}_B{'_inj' if inject else ''}.pkl", "rb"))
        res[i] = {k: float(np.nanmax(np.abs(np.asarray(a[k], float) - np.asarray(b[k], float)))) if np.isfinite(np.asarray(a[k], float)).any() else 0.0 for k in a}
    return res
clean = run_all(False)
worst = max(v for r in clean.values() for v in r.values())
print(f"CLEAN pipeline: max |A-B| over {len(next(iter(clean.values())))} series x {len(rows)} rows = {worst:.3e}")
assert worst < 1e-12, "same-row dependence detected (look-ahead)"
leaky = run_all(True)
n_flag = sum(1 for r in leaky.values() for k, v in r.items() if v > 1e-9)
print(f"POSITIVE CONTROL (injected leak): {n_flag} series-row pairs differ -> test {'detects' if n_flag > 0 else 'IS BLIND'}")
assert n_flag > 0, "test cannot detect an injected same-session leak"
print("PASS")
