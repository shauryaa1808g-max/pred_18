"""Walk-forward scale-model forecasts for G, I, R, plus the range model.  Writes results/forecasts_*.csv.

Usage:  python3 src/walkforward.py [--upto YYYY-MM-DD]   (--upto is for debugging on the Development window only)
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

import models as P
from common import EPS, GRID, load_bse, load_index, targets

RES = Path("results")
MODELS = ("S0", "S1", "S2", "S3", "S4", "S5", "S6")


def build():
    d = load_bse()
    t = targets(d)
    ix = load_index()
    exog = P.exog_matrix(d, ix, d["turnover_cr"])
    return d, t, ix, exog


def run_targets(t: pd.DataFrame, exog: np.ndarray, n_end: int | None):
    out = {}
    spec = {"R": ("R", t["v"].values), "G": ("G", np.clip(t["G"].values ** 2, EPS, None)), "I": ("I", t["gk"].values)}
    for name, (col, v) in spec.items():
        x = t[col].values
        run = P.run_scale_models(x, v, exog, t_end=n_end, models=MODELS)
        out[name] = run
    return out


def run_range(t: pd.DataFrame, n_end: int | None):
    """Range rho = ln(H/L) >= 0.  Model: HAR on log rho^2 + FHS (no centring) vs trailing-250d empirical quantiles."""
    rho = t["rho"].values
    n = len(rho) if n_end is None else n_end
    v = np.clip(rho ** 2, EPS, None)
    ts = np.arange(P.MIN_HIST, n)
    q_har = np.full((len(ts), len(GRID)), np.nan)
    q_emp = np.full((len(ts), len(GRID)), np.nan)
    for b0 in range(P.MIN_HIST, n, P.REFIT):
        sig = P.sigma_har_block(v[:n], b0)
        for tt in range(b0, min(b0 + P.REFIT, n)):
            q_har[tt - P.MIN_HIST] = P.fhs_quantiles(rho, sig, tt, center=False)
            q_emp[tt - P.MIN_HIST] = np.quantile(rho[max(0, tt - 250):tt], GRID)
    return {"HAR": q_har, "EMP250": q_emp}


def ohlc_bootstrap(t: pd.DataFrame, sigma_R: np.ndarray, tt: int, window: int = P.Z_WINDOW):
    """Joint empirical draws of (G, Hp, Lp, R) scaled by the forecast sigma: u_s = [G,Hp,Lp,R]_s / sigma_s ; draw = sigma_tt * u_s."""
    lo = max(0, tt - window)
    cols = ["G", "Hp", "Lp", "R"]
    u = t[cols].values[lo:tt] / sigma_R[lo:tt, None]
    u = u[np.isfinite(u).all(axis=1)]
    return sigma_R[tt] * u  # [m, 4]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--upto", default=None)
    a = ap.parse_args()
    RES.mkdir(exist_ok=True)
    d, t, ix, exog = build()
    n_end = None if a.upto is None else int(np.searchsorted(t.index.values, np.datetime64(a.upto), side="right"))
    ev_idx = t.index[P.MIN_HIST:n_end]
    runs = run_targets(t, exog, n_end)
    for name, run in runs.items():
        frames = []
        for m in MODELS:
            q = pd.DataFrame(run.quantiles[m], index=ev_idx, columns=[f"q{g:g}" for g in GRID])
            q["sigma"] = run.sigma[m]
            q["model"] = m
            q["y"] = t[name].values[P.MIN_HIST:n_end]
            frames.append(q.reset_index())
        pd.concat(frames).to_csv(RES / f"forecasts_{name}.csv", index=False)
        print(name, run.notes)
    rg = run_range(t, n_end)
    frames = []
    for k, q in rg.items():
        df = pd.DataFrame(q, index=ev_idx, columns=[f"q{g:g}" for g in GRID]); df["model"] = k
        df["y"] = t["rho"].values[P.MIN_HIST:n_end]
        frames.append(df.reset_index())
    pd.concat(frames).to_csv(RES / "forecasts_rho.csv", index=False)
    print("done; evaluation dates", ev_idx[0].date(), "->", ev_idx[-1].date(), len(ev_idx))


if __name__ == "__main__":
    main()
