"""Null/permutation test of the location pipeline: BSE returns are shuffled across days (all real exogenous features kept).
Any systematic positive OOS R^2 here would indicate leakage or an evaluation flaw."""
import sys; sys.path.insert(0, "src")
import numpy as np, pandas as pd
import location as L, models as P, run_location as RL
from common import load_bse, load_index, load_breadth, targets

d0 = load_bse(); t0 = targets(d0); ix = load_index(); br = load_breadth()
n_end = int(np.searchsorted(d0.index.values, np.datetime64(L.DEV_END), side="right"))
res = []
for seed in range(8):
    rng = np.random.default_rng(seed)
    perm = rng.permutation(len(t0))
    t = t0.copy()
    for c in ["G", "I", "R"]:
        t[c] = t0[c].values[perm]
    d = d0.copy()
    d["close"] = 1000 * np.exp(np.cumsum(t["R"].values))      # price path consistent with shuffled returns
    F, s = L.feature_frame(d, t, ix, br)
    R = t["R"].values; y_std = R / s; y_dir = (R > 0).astype(int)
    ev = np.arange(P.MIN_HIST, n_end); ok = np.isfinite(y_std[ev])
    out = {}
    for a in (10, 1000):
        pr = L.walk(F, y_std, y_dir, RL.ALL_COLS, alpha=a, C=None, t_end=n_end, kind="ridge")
        out[a] = 1 - np.mean((y_std[ev][ok] - pr[ev][ok]) ** 2) / np.mean(y_std[ev][ok] ** 2)
    res.append(out)
    print(f"seed {seed}: OOS R2 (std units) alpha=10: {out[10]:+.4f}  alpha=1000: {out[1000]:+.4f}")
r = pd.DataFrame(res)
print("mean", r.mean().round(4).to_dict(), "max", r.max().round(4).to_dict())
