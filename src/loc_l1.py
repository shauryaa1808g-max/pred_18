"""Post-hoc extension (DEVIATIONS #15): L1 (un-centred standardised residuals = historical-average location) vs L0 (median-centred) for G, I, R.
Same selected scale model per target; only the centring differs."""
import numpy as np, pandas as pd
import metrics as M, models as P
from common import EPS, GRID, load_bse, targets
d = load_bse(); t = targets(d)
spec = {"G": ("S4", np.clip(t["G"].values ** 2, EPS, None)), "I": ("S6", t["gk"].values), "R": ("S6", t["v"].values)}
idx = t.index[P.MIN_HIST:]
rows = []
res = {}
for tg, (m, v) in spec.items():
    x = t[tg].values
    q0 = P.run_scale_models(x, v, None, models=(m,), center=True).quantiles[m]
    q1 = P.run_scale_models(x, v, None, models=(m,), center=False).quantiles[m]
    y = x[P.MIN_HIST:]
    pl0, pl1 = M.pinball(y, q0), M.pinball(y, q1)
    for lab, lo, hi in (("dev", None, "2024-06-28"), ("val", "2024-07-01", "2025-06-30"), ("final", "2025-07-01", None), ("valfinal", "2024-07-01", None)):
        msk = np.ones(len(idx), bool)
        if lo: msk &= idx >= pd.Timestamp(lo)
        if hi: msk &= idx <= pd.Timestamp(hi)
        dm, tt, p = M.diebold_mariano(pl1[msk], pl0[msk])      # positive => L1 better
        c50_0 = M.coverage(y[msk], q0[msk], 0.5)[0]; c50_1 = M.coverage(y[msk], q1[msk], 0.5)[0]
        rows.append({"target": tg, "model": m, "window": lab, "n": int(msk.sum()), "pinball_L0_x1e4": 1e4 * pl0[msk].mean(), "pinball_L1_x1e4": 1e4 * pl1[msk].mean(),
                     "L1_gain_x1e4": 1e4 * dm, "dm_p_L1_better": p, "cov50_L0": c50_0, "cov50_L1": c50_1,
                     "median_shift_L1_vs_L0_pct": 100 * float(np.mean(q1[msk][:, list(GRID).index(0.5)]))})
    res[tg] = (q0, q1)
df = pd.DataFrame(rows)
df.to_csv("results/eval_location_L1_vs_L0.csv", index=False)
pd.set_option("display.width", 250)
print(df.round(4).to_string(index=False))
# decision rule
print()
for tg in spec:
    s = df[df.target == tg].set_index("window")
    ok = (s.loc["valfinal", "dm_p_L1_better"] < 0.05) and (s.loc["val", "L1_gain_x1e4"] > 0) and (s.loc["final", "L1_gain_x1e4"] > 0)
    print(f"{tg}: rule -> {'L1 REPLACES L0' if ok else 'L0 stays'}   (valfinal DM p={s.loc['valfinal','dm_p_L1_better']:.4f}; val gain {s.loc['val','L1_gain_x1e4']:+.3f}; final gain {s.loc['final','L1_gain_x1e4']:+.3f})")
