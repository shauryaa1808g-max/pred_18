"""Integrity audit of the user-supplied workbook data/raw/tradingview/BSE_intraday_30d_1.xlsx (self-described as Yahoo Finance chart API data, NOT a TradingView export).

Checks: structure, timestamps/ordering/duplicates, missing bars, session boundaries, OHLC consistency, tick size, bar-to-bar continuity, cross-timeframe consistency
(15m -> 30m -> 1h), match to the NSE exchange daily OHLCV, and match to the 15m bars fetched earlier through a summarising fetch tool (data/raw/intraday).
Writes results/xlsx_audit.json and data/processed/xlsx_15m_clean.csv.  Prints a summary."""
from __future__ import annotations

import glob
import json
from pathlib import Path

import numpy as np
import pandas as pd

from common import load_bse

XL = "data/raw/tradingview/BSE_intraday_30d_1.xlsx"
out: dict = {"file": XL}
sheets = {s: pd.read_excel(XL, sheet_name=s) for s in ("15 min", "30 min", "1 hour")}
notes = pd.read_excel(XL, sheet_name="Notes", header=None)[0].dropna().tolist()
out["notes_sheet"] = notes
bars: dict[str, pd.DataFrame] = {}
for name, df in sheets.items():
    df = df.copy()
    df.columns = ["date", "time", "open", "high", "low", "close", "volume"]
    df["ts"] = pd.to_datetime(df["date"].astype(str) + " " + df["time"].astype(str))
    bars[name] = df
    rep: dict = {"rows": len(df), "first": str(df.ts.min()), "last": str(df.ts.max()), "sessions": int(df.date.nunique()),
                 "sorted": bool(df.ts.is_monotonic_increasing), "duplicate_timestamps": int(df.ts.duplicated().sum()),
                 "nulls": int(df.isna().sum().sum()), "zero_volume_bars": int((df.volume == 0).sum()),
                 "weekend_sessions": [str(d) for d in sorted(df.date.unique()) if pd.Timestamp(d).dayofweek >= 5]}
    rep["bars_per_session"] = df.groupby("date").size().value_counts().sort_index().to_dict()
    rep["ohlc_inconsistent_rows"] = int(((df.low > df[["open", "close"]].min(axis=1) + 1e-9) | (df.high < df[["open", "close"]].max(axis=1) - 1e-9) | (df.high < df.low)).sum())
    # tick size: NSE equities trade in 0.05 (or 0.10 for some); check multiples of 0.05
    rep["prices_not_multiple_of_0.05"] = int((((df[["open", "high", "low", "close"]] * 20).round(6) % 1).abs() > 1e-6).sum().sum())
    cont = (df.groupby("date").apply(lambda g: (g.open.iloc[1:].values / g.close.iloc[:-1].values - 1), include_groups=False))
    allc = np.concatenate(cont.values)
    rep["bar_open_vs_prev_close_abs_max_pct"] = float(100 * np.abs(allc).max()); rep["bar_open_vs_prev_close_gt0.4pct"] = int((np.abs(allc) > 0.004).sum())
    exp = {"15 min": pd.date_range("09:15", "15:15", freq="15min"), "30 min": pd.date_range("09:15", "15:15", freq="30min"), "1 hour": pd.date_range("09:15", "15:15", freq="60min")}[name].strftime("%H:%M")
    exp = list(exp) + (["15:15"] if name == "1 hour" and "15:15" not in exp else [])
    miss = {}
    for d, g in df.groupby("date"):
        m = [t for t in exp if t not in set(g.time.astype(str))]
        if m:
            miss[str(d)] = m
    rep["missing_bars_vs_expected_grid"] = miss
    out[name] = rep

# --- session boundaries / timezone sanity
b15 = bars["15 min"]
out["first_bar_times"] = sorted(b15.groupby("date").time.min().astype(str).unique().tolist()); out["last_bar_times"] = sorted(b15.groupby("date").time.max().astype(str).unique().tolist())
out["sessions_list"] = [str(d) for d in sorted(b15.date.unique())]

# --- match to NSE exchange daily data
d = load_bse()
rows = []
for name, df in bars.items():
    for day, g in df.groupby("date"):
        dd = pd.Timestamp(day)
        if dd not in d.index:
            rows.append({"tf": name, "date": str(day), "status": "no NSE daily row"}); continue
        r = d.loc[dd]
        rows.append({"tf": name, "date": str(day), "open": float(g.open.iloc[0] - r.open), "high": float(g.high.max() - r.high), "low": float(g.low.min() - r.low), "close": float(g.close.iloc[-1] - r.close),
                     "vol_ratio": float(g.volume.sum() / r.vol), "n": len(g)})
m = pd.DataFrame(rows)
mm = m[m["status"].isna()] if "status" in m else m
out["nse_daily_match"] = {tf: {"sessions": int(len(g)), "close_diff_max_abs": float(g.close.abs().max()), "open_diff_max_abs": float(g.open.abs().max()), "high_diff_min": float(g.high.min()), "high_diff_max": float(g.high.max()),
                                "low_diff_min": float(g.low.min()), "low_diff_max": float(g.low.max()), "vol_ratio_min": float(g.vol_ratio.min()), "vol_ratio_max": float(g.vol_ratio.max()), "vol_ratio_mean": float(g.vol_ratio.mean())} for tf, g in mm.groupby("tf")}
out["nse_daily_unmatched"] = m[m.get("status").notna()].to_dict("records") if "status" in m else []

# --- cross-timeframe consistency: rebuild 30m and 1h from 15m
def agg(g):
    return pd.Series({"open": g.open.iloc[0], "high": g.high.max(), "low": g.low.min(), "close": g.close.iloc[-1], "volume": g.volume.sum(), "n": len(g)})
def rebuild(df15, minutes):
    x = df15.copy(); x["bucket"] = x.ts.dt.floor(f"{minutes}min") if minutes == 15 else None
    start = x.ts.dt.normalize() + pd.Timedelta(hours=9, minutes=15)
    k = ((x.ts - start).dt.total_seconds() // (minutes * 60)).astype(int)
    x["bucket"] = start + pd.to_timedelta(k * minutes, unit="min")
    return x.groupby("bucket").apply(agg, include_groups=False)
for name, minutes in (("30 min", 30), ("1 hour", 60)):
    rb = rebuild(b15, minutes); sh = bars[name].set_index("ts")
    j = sh.join(rb, rsuffix="_rb", how="inner")
    full = j[j["n"] == (minutes // 15)]
    out[f"consistency_{name}_vs_15m"] = {"bars_compared": int(len(j)), "bars_with_complete_15m_set": int(len(full)),
        "close_mismatch": int((full.close.sub(full.close_rb).abs() > 0.051).sum()), "open_mismatch": int((full.open.sub(full.open_rb).abs() > 0.051).sum()),
        "high_mismatch": int((full.high.sub(full.high_rb).abs() > 0.051).sum()), "low_mismatch": int((full.low.sub(full.low_rb).abs() > 0.051).sum()),
        "volume_mismatch_gt1pct": int(((full.volume / full.volume_rb - 1).abs() > 0.01).sum()), "volume_zero_in_sheet_but_not_in_15m": int(((full.volume == 0) & (full.volume_rb > 0)).sum())}

# --- compare with 15m bars previously fetched through a summarising tool
prev = pd.concat([pd.read_csv(f) for f in sorted(glob.glob("data/raw/intraday/*.csv"))]).drop_duplicates("ts").dropna().sort_values("ts")
prev["dt"] = pd.to_datetime(prev.ts, unit="s", utc=True).dt.tz_convert("Asia/Kolkata").dt.tz_localize(None)
cmp_ = b15.set_index("ts").join(prev.set_index("dt"), rsuffix="_prev", how="inner")
if len(cmp_):
    out["vs_earlier_fetched_yahoo_bars"] = {"bars_compared": int(len(cmp_)), "first": str(cmp_.index.min()), "last": str(cmp_.index.max()),
        **{f"{c}_mismatch_gt0.051": int((cmp_[c] - cmp_[c + "_prev"]).abs().gt(0.051).sum()) for c in ("open", "high", "low", "close")},
        "volume_mismatch_gt1pct": int(((cmp_.volume / cmp_.volume_prev - 1).abs() > 0.01).sum())}
    bad = cmp_[((cmp_.open - cmp_.open_prev).abs() > 0.051) | ((cmp_.high - cmp_.high_prev).abs() > 0.051) | ((cmp_.low - cmp_.low_prev).abs() > 0.051) | ((cmp_.close - cmp_.close_prev).abs() > 0.051) | ((cmp_.volume / cmp_.volume_prev - 1).abs() > 0.01)]
    out["vs_earlier_fetched_yahoo_bars"]["mismatching_bars_sample"] = [{"ts": str(i), "xlsx": [r.open, r.high, r.low, r.close, int(r.volume)], "earlier": [r.open_prev, r.high_prev, r.low_prev, r.close_prev, int(r.volume_prev)]} for i, r in bad.head(12).iterrows()]
    out["earlier_fetched_sessions_not_in_xlsx_window"] = int(prev.dt.dt.normalize().nunique() - cmp_.index.normalize().nunique())
Path("results/xlsx_audit.json").write_text(json.dumps(out, indent=1, default=str))
b15.drop(columns=["ts"]).to_csv("data/processed/xlsx_15m_clean.csv", index=False)
print(json.dumps({k: v for k, v in out.items() if k not in ("notes_sheet", "sessions_list")}, indent=1, default=str)[:9000])
