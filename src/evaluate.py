"""Evaluate walk-forward scale forecasts by period / regime.  Reads results/forecasts_*.csv, writes results/eval_*.csv.

Usage: python3 src/evaluate.py [--periods dev|all]   ('dev' restricts to the Development window so the Validation/Final windows stay unseen)
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

import metrics as M
from common import GRID, load_bse, targets

RES = Path("results")
PERIODS = {
    "dev": (None, "2024-06-28"), "val": ("2024-07-01", "2025-06-30"), "final": ("2025-07-01", None),
    "devval": (None, "2025-06-30"), "valfinal": ("2024-07-01", None), "all": (None, None),
}
REGIMES = {
    "pre-covid": (None, "2020-02-19"), "covid": ("2020-02-20", "2020-12-31"), "2021-22": ("2021-01-01", "2022-12-31"),
    "2023": ("2023-01-01", "2023-12-31"), "2024": ("2024-01-01", "2024-12-31"), "2025+": ("2025-01-01", None),
}
LEVELS = (0.5, 0.8, 0.9, 0.95)
QCOLS = [f"q{g:g}" for g in GRID]


def slice_dates(idx: pd.DatetimeIndex, lo, hi) -> np.ndarray:
    m = np.ones(len(idx), bool)
    if lo:
        m &= idx >= pd.Timestamp(lo)
    if hi:
        m &= idx <= pd.Timestamp(hi)
    return m


def holm(p: dict[str, float]) -> dict[str, float]:
    items = sorted(((k, v) for k, v in p.items() if np.isfinite(v)), key=lambda kv: kv[1])
    out, m, run = {}, len(items), 0.0
    for i, (k, v) in enumerate(items):
        run = max(run, min(1.0, (m - i) * v))
        out[k] = run
    return out


def eval_target(name: str, fc: pd.DataFrame, bench: str, v_proxy: pd.Series | None, mask_fn, label: str) -> list[dict]:
    # v_proxy: realised variance proxy aligned to dates -> adds QLIKE (secondary metric of PREREGISTRATION s4); None for the range target
    rows = []
    piv_q = {m: g.set_index("date")[QCOLS] for m, g in fc.groupby("model")}
    y_all = fc[fc.model == bench].set_index("date")["y"]
    dates = y_all.index
    msk = mask_fn(dates)
    if msk.sum() < 30:
        return rows
    y = y_all.values[msk]
    pl = {m: M.pinball(y, q.loc[dates].values[msk]) for m, q in piv_q.items()}
    pvals = {}
    stats_ = {}
    qls = {}
    for m, q in piv_q.items():
        qq = q.loc[dates].values[msk]
        row = {"target": name, "period": label, "model": m, "n": int(msk.sum()), "pinball_x1e4": 1e4 * pl[m].mean()}
        for lev in LEVELS:
            c, hit = M.coverage(y, qq, lev)
            row[f"cov{int(lev*100)}"] = c
            row[f"kupiec{int(lev*100)}"] = M.kupiec(hit, lev)
            row[f"christ{int(lev*100)}"] = M.christoffersen_ind(hit)
            row[f"width{int(lev*100)}"] = float(np.mean(qq[:, list(GRID).index(M.CENTRAL[lev][1])] - qq[:, list(GRID).index(M.CENTRAL[lev][0])]))
        if v_proxy is not None and "sigma" in fc.columns:
            sg = fc[fc.model == m].set_index("date")["sigma"].loc[dates].values[msk]
            vp = v_proxy.reindex(dates).values[msk]
            ql = M.qlike(sg ** 2, vp)
            row["qlike_mean"] = float(np.mean(ql))
            qls[m] = ql
        if m != bench:
            dm, t, p = M.diebold_mariano(pl[m], pl[bench])
            row["dm_mean_gain_vs_bench_x1e4"] = 1e4 * dm
            row["dm_t"] = t
            row["dm_p_better"] = p
            pvals[m] = p
        rows.append(row)
        stats_[m] = row
    hp = holm(pvals)
    for r in rows:
        r["dm_p_holm"] = hp.get(r["model"], np.nan)
        if r["model"] in qls and bench in qls and r["model"] != bench:
            dmq, tq, pq = M.diebold_mariano(qls[r["model"]], qls[bench])
            r["qlike_dm_p_better_than_bench"] = pq
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--periods", default="dev")
    a = ap.parse_args()
    d = load_bse(); t = targets(d)
    allrows = []
    # volatility regime (information at t-1): expanding-median split of trailing-60d realised vol
    rv = t["R"].rolling(60).std().shift(1)
    hi_vol = rv > rv.expanding(120).median().shift(1)
    for name in ("R", "G", "I"):
        fc = pd.read_csv(RES / f"forecasts_{name}.csv", parse_dates=["date"])
        proxy = {"R": t["v"], "G": t["G"].pow(2).clip(lower=1e-8), "I": t["gk"]}[name]
        sets = {k: v for k, v in PERIODS.items() if a.periods == "all" or k == "dev"}
        for lab, (lo, hi) in sets.items():
            allrows += eval_target(name, fc, "S0", proxy, lambda ix, lo=lo, hi=hi: slice_dates(ix, lo, hi), lab)
        if a.periods == "all" and name == "R":
            for lab, (lo, hi) in REGIMES.items():
                allrows += eval_target(name, fc, "S0", None, lambda ix, lo=lo, hi=hi: slice_dates(ix, lo, hi), f"regime:{lab}")
            for lab, flag in (("highvol", True), ("lowvol", False)):
                allrows += eval_target(name, fc, "S0", None, lambda ix, flag=flag: (hi_vol.reindex(ix).fillna(False).values == flag), f"regime:{lab}")
    rg = pd.read_csv(RES / "forecasts_rho.csv", parse_dates=["date"])
    sets = {k: v for k, v in PERIODS.items() if a.periods == "all" or k == "dev"}
    for lab, (lo, hi) in sets.items():
        allrows += eval_target("rho", rg, "EMP250", None, lambda ix, lo=lo, hi=hi: slice_dates(ix, lo, hi), lab)
    out = pd.DataFrame(allrows)
    out.to_csv(RES / ("eval_scale_dev.csv" if a.periods == "dev" else "eval_scale_all.csv"), index=False)
    pd.set_option("display.width", 220)
    cols = ["target", "period", "model", "n", "pinball_x1e4", "cov50", "cov80", "cov90", "cov95", "kupiec90", "christ90", "dm_mean_gain_vs_bench_x1e4", "dm_p_better", "dm_p_holm"]
    print(out[cols].round(4).to_string(index=False))


if __name__ == "__main__":
    main()
