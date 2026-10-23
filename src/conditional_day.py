"""DESCRIPTIVE conditional intraday behaviour from daily OHLC (no intraday bars needed).  Nothing here is a gated/validated predictor.

For each session: gz = G / s_t where s_t is the EWMA(0.94) sigma forecast for R_t made with information <= t-1.
Reports frequencies with Wilson 95% intervals for the full sample, the Validation+Final window and the last 250 sessions.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

import metrics as M
import models as P
from common import load_bse, targets

d = load_bse(); t = targets(d)
s = pd.Series(P.sigma_ewma(t["R"].values), index=d.index)
gz = t["G"] / s
iz = t["I"] / s
pos = (d["close"] - d["low"]) / (d["high"] - d["low"]).replace(0, np.nan)
frame = pd.DataFrame({"G": t["G"], "I": t["I"], "R": t["R"], "gz": gz, "iz": iz, "pos": pos, "HO": t["HO"], "LO": t["LO"], "rho": t["rho"], "Hp": t["Hp"], "Lp": t["Lp"]}).dropna()
windows = {"full": frame, "valfinal(2024-07+)": frame.loc["2024-07-01":], "last250": frame.iloc[-250:]}
out = {}
for wn, f in windows.items():
    o = {"n": len(f)}
    # slope of intraday return on the gap (HC1 robust SE)
    X = np.column_stack([np.ones(len(f)), f["G"]]); y = f["I"].values
    b = np.linalg.lstsq(X, y, rcond=None)[0]; e = y - X @ b
    XtXi = np.linalg.inv(X.T @ X); V = XtXi @ (X.T * e ** 2) @ X @ XtXi * len(f) / (len(f) - 2)
    o["slope_I_on_G"] = float(b[1]); o["slope_se_hc1"] = float(np.sqrt(V[1, 1])); o["slope_t"] = float(b[1] / np.sqrt(V[1, 1]))
    o["corr_G_I"] = float(np.corrcoef(f["G"], f["I"])[0, 1])
    for lab, m in (("gap_up_gt_0.5sd", f["gz"] > 0.5), ("gap_up_gt_1sd", f["gz"] > 1.0), ("gap_down_lt_-0.5sd", f["gz"] < -0.5), ("gap_down_lt_-1sd", f["gz"] < -1.0), ("small_gap(|gz|<0.25)", f["gz"].abs() < 0.25), ("all", f["gz"].notna())):
        g = f[m]
        k = int((g["I"] > 0).sum()); lo, hi = M.wilson(k, len(g))
        o[lab] = {"n": int(len(g)), "P(I>0)": k / max(1, len(g)), "ci95": [round(lo, 3), round(hi, 3)], "mean_I_pct": float(100 * g["I"].mean()) if len(g) else None,
                  "median_I_pct": float(100 * g["I"].median()) if len(g) else None, "mean_closepos": float(g["pos"].mean()) if len(g) else None,
                  "P(close>prev)": float((g["R"] > 0).mean()) if len(g) else None}
    o["closepos_quartiles"] = [float(z) for z in f["pos"].quantile([.1, .25, .5, .75, .9])]
    o["P(close in top third of range)"] = float((f["pos"] > 2 / 3).mean()); o["P(close in bottom third)"] = float((f["pos"] < 1 / 3).mean())
    o["P(high>prev & low<prev)  [range straddles previous close]"] = float(((f["Hp"] > 0) & (f["Lp"] < 0)).mean())
    o["P(low<prev)"] = float((f["Lp"] < 0).mean()); o["P(high>prev)"] = float((f["Hp"] > 0).mean())
    o["mean_HO_pct"] = float(100 * (np.exp(f["HO"]).mean() - 1)); o["mean_LO_pct"] = float(100 * (np.exp(f["LO"]).mean() - 1))
    o["range_pct_quantiles(10,50,90)"] = [float(100 * (np.exp(z) - 1)) for z in f["rho"].quantile([.1, .5, .9])]
    out[wn] = o
# after a large close-near-high day with high volume (13 Oct looks like this): next-session behaviour, descriptive only
f2 = frame.copy()
f2["next_R"] = f2["R"].shift(-1); f2["next_G"] = f2["G"].shift(-1); f2["next_I"] = f2["I"].shift(-1)
cond = (f2["R"] > 0.01) & (f2["pos"] > 0.8)
g = f2[cond].dropna(subset=["next_R"])
k = int((g["next_R"] > 0).sum()); lo, hi = M.wilson(k, len(g))
out["after_up_day>1%_closing_in_top_20%_of_range"] = {"n": int(len(g)), "P(next_R>0)": k / len(g), "ci95": [round(lo, 3), round(hi, 3)], "mean_next_R_pct": float(100 * g["next_R"].mean()), "median_next_R_pct": float(100 * g["next_R"].median()),
                                                         "mean_next_G_pct": float(100 * g["next_G"].mean()), "mean_next_I_pct": float(100 * g["next_I"].mean()), "share_all_days_up": float((f2["next_R"] > 0).mean()),
                                                         "note": "descriptive; one of many conditioning choices, no multiple-testing correction, NOT used in the forecast"}
Path("results/conditional_day.json").write_text(json.dumps(out, indent=1))
for wn in windows:
    o = out[wn]
    print(f"== {wn}  n={o['n']}  slope(I on G)={o['slope_I_on_G']:.3f} (t={o['slope_t']:.2f})  corr={o['corr_G_I']:.3f}  range 10/50/90%: {[round(z,2) for z in o['range_pct_quantiles(10,50,90)']]}  P(straddle prev close)={o['P(high>prev & low<prev)  [range straddles previous close]']:.3f}  P(low<prev)={o['P(low<prev)']:.3f} P(high>prev)={o['P(high>prev)']:.3f}")
    for lab in ("gap_up_gt_0.5sd", "gap_up_gt_1sd", "gap_down_lt_-0.5sd", "gap_down_lt_-1sd", "small_gap(|gz|<0.25)", "all"):
        z = o[lab]; print(f"   {lab:22s} n={z['n']:4d}  P(I>0)={z['P(I>0)']:.3f} {z['ci95']}  mean I {z['mean_I_pct']:+.2f}%  P(close>prev)={z['P(close>prev)']:.3f}  mean close-position {z['mean_closepos']:.2f}")
print(json.dumps(out["after_up_day>1%_closing_in_top_20%_of_range"], indent=1))
