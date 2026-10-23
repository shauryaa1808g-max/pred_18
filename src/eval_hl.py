"""EXPLORATORY (DEVIATIONS #5): walk-forward check of the OHLC-bootstrap forecasts of the day's high and low (H' = ln(H/P0), L' = ln(L/P0)).

For each evaluation day t, u_s = [G, H', L', R]_s / sigma_s over the trailing 500 sessions, using the *stored* out-of-sample sigma_s (S6 for the
model, an expanding RMS for the benchmark); draw_t = sigma_t * u_s.  Quantiles of H' and L' come from the draws; no information after t-1 is used.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

import metrics as M
from common import GRID, load_bse, targets

d = load_bse(); t = targets(d)
fc = pd.read_csv("results/forecasts_R.csv", parse_dates=["date"])
res = {}
for model in ("S6", "S0", "S1"):
    s = fc[fc.model == model].set_index("date")["sigma"].reindex(d.index)
    res[model] = s.values
V = t[["G", "Hp", "Lp", "R"]].values
dates = d.index
first_eval = int(np.where(np.isfinite(res["S6"]))[0].min()) + 250
rows = {m: {"Hp": [], "Lp": [], "G": [], "R": []} for m in res}
idx = []
for tt in range(first_eval, len(d)):
    idx.append(tt)
    for m, sig in res.items():
        lo = max(0, tt - 500)
        sw = sig[lo:tt]
        u = V[lo:tt] / sw[:, None]
        u = u[np.isfinite(u).all(axis=1)]
        draws = sig[tt] * u
        for j, k in enumerate(["G", "Hp", "Lp", "R"]):
            q = np.quantile(draws[:, j], GRID)
            rows[m][k].append(q)
idx = np.array(idx)
y = {"Hp": t["Hp"].values[idx], "Lp": t["Lp"].values[idx], "G": t["G"].values[idx], "R": t["R"].values[idx]}
dts = dates[idx]
windows = {"valfinal": dts >= pd.Timestamp("2024-07-01"), "final": dts >= pd.Timestamp("2025-07-01"), "all_eval": np.ones(len(dts), bool)}
print(f"evaluation sessions {dts[0].date()} -> {dts[-1].date()}  n={len(dts)}")
for w, m_ in windows.items():
    print(f"--- window {w} n={int(m_.sum())}")
    for k in ("Hp", "Lp", "G", "R"):
        base = None
        for m in ("S0", "S1", "S6"):
            q = np.array(rows[m][k])[m_]
            pl = M.pinball(y[k][m_], q)
            if m == "S0":
                base = pl
            c90, h90 = M.coverage(y[k][m_], q, 0.9)
            c50, _ = M.coverage(y[k][m_], q, 0.5)
            dm = "" if m == "S0" else f" DM-p(vs S0)={M.diebold_mariano(pl, base)[2]:.3f}"
            print(f"  {k:2s} {m}: pinball x1e4 {1e4*pl.mean():7.3f} cov50 {c50:.3f} cov90 {c90:.3f} kupiec90 {M.kupiec(h90,0.9):.3f}{dm}")
