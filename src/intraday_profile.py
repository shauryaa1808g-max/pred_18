"""DESCRIPTIVE intraday structure from validated 15-minute bars (never used by the gated models).  Only sessions marked PASS by validate_intraday.py are used."""
from __future__ import annotations

import glob
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

b = pd.concat([pd.read_csv(f) for f in sorted(glob.glob("data/raw/intraday/*.csv"))]).drop_duplicates("ts").dropna().sort_values("ts")
b["dt"] = pd.to_datetime(b["ts"], unit="s", utc=True).dt.tz_convert("Asia/Kolkata")
b["date"] = b["dt"].dt.tz_localize(None).dt.normalize()
b["tod"] = b["dt"].dt.strftime("%H:%M")
val = pd.read_csv("data/processed/intraday_validation.csv", parse_dates=["date"]).set_index("date")["status"]
good = [dd for dd, s in val.items() if s == "PASS"]
b = b[b["date"].isin(good)].copy()
rows, vol_prof, ret_prof = [], [], []
for day, g in b.groupby("date"):
    g = g.reset_index(drop=True)
    if len(g) < 24:
        continue
    tot = g["volume"].sum()
    tp = (g["high"] + g["low"] + g["close"]) / 3
    vwap = float((tp * g["volume"]).sum() / tot)
    hi_i, lo_i = int(g["high"].idxmax()), int(g["low"].idxmin())
    rng = g["high"].max() - g["low"].min()
    fh = g.iloc[:4]; rest = g.iloc[4:]
    r_fh = float(np.log(fh["close"].iloc[-1] / fh["open"].iloc[0]))
    r_rest = float(np.log(g["close"].iloc[-1] / fh["close"].iloc[-1]))
    rng_fh = (fh["high"].max() - fh["low"].min()) / rng if rng > 0 else np.nan
    rows.append({"date": day, "n": len(g), "vol_first_bar": g["volume"].iloc[0] / tot, "vol_first_hour": fh["volume"].sum() / tot, "vol_last_hour": g["volume"].iloc[-4:].sum() / tot,
                 "vol_last_bar": g["volume"].iloc[-1] / tot, "hi_bar": hi_i, "lo_bar": lo_i, "r_fh": r_fh, "r_rest": r_rest, "range_share_by_1015": rng_fh,
                 "close_vs_vwap": float(g["close"].iloc[-1] / vwap - 1), "last_bar_move": float(np.log(g["close"].iloc[-1] / g["close"].iloc[-2])),
                 "day_ret_bars": float(np.log(g["close"].iloc[-1] / g["open"].iloc[0]))})
    vol_prof.append((g["volume"] / tot).values[:25])
    ret_prof.append(np.log(g["close"] / g["close"].shift(1).fillna(g["open"])).values[:25])
S = pd.DataFrame(rows).set_index("date")
n = len(S)
times = [f"{9 + (15 * (i + 1) - 15 + 15) // 60 + 0:02d}" for i in range(0)]  # placeholder (kept simple below)
tod = pd.date_range("09:15", periods=25, freq="15min").strftime("%H:%M")
vp = np.nanmean(np.array([v for v in vol_prof if len(v) == 25]), axis=0)
rp = np.nanstd(np.array([r for r in ret_prof if len(r) == 25]), axis=0)
prof = pd.DataFrame({"bar_start": tod, "mean_volume_share_pct": 100 * vp, "std_15m_return_pct": 100 * rp})
out = {"n_sessions": n, "first": str(S.index.min().date()), "last": str(S.index.max().date())}
out["volume_share_first_bar_pct"] = float(100 * S["vol_first_bar"].mean()); out["volume_share_first_hour_pct"] = float(100 * S["vol_first_hour"].mean())
out["volume_share_last_hour_pct"] = float(100 * S["vol_last_hour"].mean()); out["volume_share_last_bar_1515_pct"] = float(100 * S["vol_last_bar"].mean())
out["high_in_first_hour_share"] = float((S["hi_bar"] < 4).mean()); out["low_in_first_hour_share"] = float((S["lo_bar"] < 4).mean())
out["high_in_last_hour_share"] = float((S["hi_bar"] >= 21).mean()); out["low_in_last_hour_share"] = float((S["lo_bar"] >= 21).mean())
out["high_or_low_in_first_hour_share"] = float(((S["hi_bar"] < 4) | (S["lo_bar"] < 4)).mean())
out["median_range_share_formed_by_10:15"] = float(S["range_share_by_1015"].median())
r, p = stats.pearsonr(S["r_fh"], S["r_rest"]); out["corr_firsthour_vs_restofday"] = {"r": float(r), "p": float(p), "n": n}
out["P(rest-of-day continues first-hour direction)"] = float((np.sign(S["r_fh"]) == np.sign(S["r_rest"])).mean())
out["P(close above bar-VWAP)"] = float((S["close_vs_vwap"] > 0).mean())
out["last_bar_1515_abs_move_mean_pct"] = float(100 * S["last_bar_move"].abs().mean()); out["last_bar_1515_move_mean_pct"] = float(100 * S["last_bar_move"].mean())
Path("results/intraday_profile.json").write_text(json.dumps(out, indent=1))
prof.to_csv("results/intraday_time_profile.csv", index=False)
print(json.dumps(out, indent=1)); print(prof.round(3).to_string(index=False))
# the path of the most recent session (validated or provisional) for context
last = b[b["date"] == b["date"].max()]
print("\nlast session in bars:", b["date"].max().date())
