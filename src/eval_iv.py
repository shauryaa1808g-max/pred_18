"""EXPLORATORY (DEVIATIONS #4): does ATM implied vol add information about next-session |R|?  Non-gating.

sigma_iv[t] = iv_atm(date t-1) / sqrt(252), standardised residuals via the same FHS machinery (window = all available up to 500, min 120).
Compared on common dates with S0/S1/S4/S6 from results/forecasts_R.csv.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

import metrics as M
import models as P
from common import GRID, load_bse, targets

d = load_bse(); t = targets(d)
iv = pd.read_csv("data/processed/bse_iv_daily.csv", parse_dates=["date"]).set_index("date")["iv_atm"]
s_iv = (iv.reindex(d.index).shift(1) / np.sqrt(252)).values
R = t["R"].values
n = len(R)
first = np.where(np.isfinite(s_iv))[0].min()
out = {}
qs = np.full((n, len(GRID)), np.nan)
for tt in range(first + 120, n):
    lo = max(first, tt - 500)
    z = R[lo:tt] / s_iv[lo:tt]
    z = z[np.isfinite(z)]
    if len(z) < 120:
        continue
    qs[tt] = s_iv[tt] * (np.quantile(z, GRID) - np.median(z))
dates = d.index
fc = pd.read_csv("results/forecasts_R.csv", parse_dates=["date"])
piv = {m: g.set_index("date")[[f"q{g:g}" for g in GRID]] for m, g in fc.groupby("model")}
ok = np.isfinite(qs).all(axis=1)
common = dates[ok].intersection(piv["S0"].index)
y = pd.Series(R, index=dates).loc[common].values
pl = {"S7_iv": M.pinball(y, pd.DataFrame(qs, index=dates).loc[common].values)}
for m in ("S0", "S1", "S4", "S6"):
    pl[m] = M.pinball(y, piv[m].loc[common].values)
print(f"common dates {common[0].date()} -> {common[-1].date()}  n={len(common)}")
for m, v in pl.items():
    print(f"  {m:6s} mean pinball x1e4 = {1e4*v.mean():7.3f}")
for m in ("S0", "S1", "S4", "S6"):
    dm, tt_, p = M.diebold_mariano(pl["S7_iv"], pl[m])
    print(f"  DM S7_iv vs {m}: mean gain x1e4 = {1e4*dm:+.3f}  one-sided p(S7 better) = {p:.3f}")
for lev in (0.5, 0.8, 0.9, 0.95):
    c, h = M.coverage(y, pd.DataFrame(qs, index=dates).loc[common].values, lev)
    print(f"  S7 coverage {int(lev*100)}%: {c:.3f}")
# realised vs implied level: ratio of mean |R| to implied daily sigma
sv = pd.Series(s_iv, index=dates).loc[common].values
print("  mean |R| / (sigma_iv*sqrt(2/pi)) =", round(float(np.mean(np.abs(y)) / np.mean(sv * np.sqrt(2 / np.pi))), 3), "(1.0 would mean IV unbiased for |R| under normality)")
print("  corr(|R|, sigma_iv) =", round(float(np.corrcoef(np.abs(y), sv)[0, 1]), 3))
# latest implied reading
print("latest iv_atm:", iv.index[-1].date(), round(float(iv.iloc[-1]), 4), "=> daily sigma", round(float(iv.iloc[-1] / np.sqrt(252)), 4))
