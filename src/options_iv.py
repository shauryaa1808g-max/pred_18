"""EXPLORATORY (non-gating, DEVIATIONS #4): ATM implied volatility of BSE Ltd stock options from NSE F&O end-of-day files.

IV is inverted (Black-76, discount rate R_F) from the exchange *settlement* price of the out-of-the-money option at the two strikes
bracketing the futures price, then linearly interpolated in strike to the forward.  Expiry rule: nearest expiry with >= MIN_DTE calendar days.
"""
from __future__ import annotations

import glob
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import brentq
from scipy.stats import norm

R_F = 0.065
MIN_DTE = 7


def black76(F: float, K: float, T: float, sig: float, cp: str, r: float = R_F) -> float:
    d1 = (np.log(F / K) + 0.5 * sig * sig * T) / (sig * np.sqrt(T))
    d2 = d1 - sig * np.sqrt(T)
    df = np.exp(-r * T)
    return df * (F * norm.cdf(d1) - K * norm.cdf(d2)) if cp == "CE" else df * (K * norm.cdf(-d2) - F * norm.cdf(-d1))


def implied_vol(price: float, F: float, K: float, T: float, cp: str) -> float:
    intrinsic = np.exp(-R_F * T) * max(F - K, 0) if cp == "CE" else np.exp(-R_F * T) * max(K - F, 0)
    if not np.isfinite(price) or price <= intrinsic + 1e-6 or price <= 0:
        return np.nan
    try:
        return brentq(lambda s: black76(F, K, T, s, cp) - price, 1e-3, 5.0, xtol=1e-6)
    except ValueError:
        return np.nan


def day_iv(df: pd.DataFrame, asof: pd.Timestamp) -> dict | None:
    df = df.copy()
    df["XpryDt"] = pd.to_datetime(df["XpryDt"])
    opt = df[df["FinInstrmTp"] == "STO"]
    fut = df[df["FinInstrmTp"] == "STF"]
    if opt.empty:
        return None
    exps = sorted(opt["XpryDt"].unique())
    cand = [e for e in exps if (e - asof).days >= MIN_DTE]
    if not cand:
        return None
    e = cand[0]
    T = (e - asof).days / 365.0
    spot = float(opt["UndrlygPric"].iloc[0])
    f = fut[fut["XpryDt"] == e]
    F = float(f["SttlmPric"].iloc[0]) if len(f) and f["SttlmPric"].iloc[0] > 0 else spot * np.exp(R_F * T)
    o = opt[opt["XpryDt"] == e]
    strikes = np.array(sorted(o["StrkPric"].unique()))
    lo = strikes[strikes <= F]; hi = strikes[strikes >= F]
    if len(lo) == 0 or len(hi) == 0:
        return None
    k_lo, k_hi = lo.max(), hi.min()
    def iv_at(k):
        # OTM option: put below forward, call above
        cp = "PE" if k < F else "CE"
        row = o[(o["StrkPric"] == k) & (o["OptnTp"] == cp)]
        if row.empty:
            return np.nan, 0
        r = row.iloc[0]
        return implied_vol(float(r["SttlmPric"]), F, k, T, cp), int(r["TtlTradgVol"])
    ivl, vl = iv_at(k_lo)
    ivh, vh = iv_at(k_hi)
    # use both calls and puts at the bracketing strikes for ATM: average of put/call IV at the nearest strike(s)
    def iv_both(k):
        vals = []
        for cp in ("CE", "PE"):
            row = o[(o["StrkPric"] == k) & (o["OptnTp"] == cp)]
            if len(row):
                v = implied_vol(float(row.iloc[0]["SttlmPric"]), F, k, T, cp)
                if np.isfinite(v):
                    vals.append(v)
        return np.mean(vals) if vals else np.nan
    a, b = iv_both(k_lo), iv_both(k_hi)
    if k_hi == k_lo:
        atm = a
    else:
        w = (F - k_lo) / (k_hi - k_lo)
        atm = np.nansum([(1 - w) * a, w * b]) if np.isfinite(a) and np.isfinite(b) else np.nanmean([a, b])
    return {"date": asof, "spot": spot, "fut": F, "expiry": e, "dte": (e - asof).days, "k_lo": k_lo, "k_hi": k_hi,
            "iv_lo_otm": ivl, "iv_hi_otm": ivh, "iv_atm": atm, "vol_lo": vl, "vol_hi": vh}


def build() -> pd.DataFrame:
    rows = []
    for f in sorted(glob.glob("data/raw/fo_bse/*.csv")):
        asof = pd.Timestamp(Path(f).stem)
        df = pd.read_csv(f)
        if df.empty:
            continue
        r = day_iv(df, asof)
        if r:
            rows.append(r)
    out = pd.DataFrame(rows).set_index("date").sort_index()
    out.to_csv("data/processed/bse_iv_daily.csv")
    return out


if __name__ == "__main__":
    iv = build()
    print(iv[["spot", "fut", "expiry", "dte", "iv_atm"]].tail(12).round(4).to_string())
    print(iv["iv_atm"].describe().round(4))
