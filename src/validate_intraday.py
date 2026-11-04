"""Validate Yahoo 15-minute bars (fetched through a summarising WebFetch) against the exchange-sourced daily OHLCV.
A session passes only if open/high/low/close match to within TOL rupees and volume to within VOL_TOL; failures are excluded downstream."""
import glob, sys
import numpy as np, pandas as pd
sys.path.insert(0, "src")
from common import load_bse
CLOSE_TOL, HL_TOL, VOL_LO, VOL_HI = 0.0002, 0.0025, 0.80, 1.02   # tiers per DEVIATIONS #17; open is reported but NOT tested (pre-open auction price vs first continuous trade)
d = load_bse()
frames = [pd.read_csv(f) for f in sorted(glob.glob("data/raw/intraday/*.csv"))]
b = pd.concat(frames).drop_duplicates("ts").dropna().sort_values("ts")
b["dt"] = pd.to_datetime(b["ts"], unit="s", utc=True).dt.tz_convert("Asia/Kolkata")
b["date"] = b["dt"].dt.tz_localize(None).dt.normalize()
b["tod"] = b["dt"].dt.strftime("%H:%M")
rows = []
for day, g in b.groupby("date"):
    if day not in d.index:
        rows.append((day, "NO DAILY ROW", None)); continue
    r = d.loc[day]
    agg = dict(open=g.iloc[0]["open"], high=g["high"].max(), low=g["low"].min(), close=g.iloc[-1]["close"], vol=g["volume"].sum(), n=len(g))
    ok = (abs(agg["close"]-r["close"]) <= CLOSE_TOL * r["close"] and abs(agg["high"]-r["high"]) <= HL_TOL * r["close"]
          and abs(agg["low"]-r["low"]) <= HL_TOL * r["close"] and VOL_LO <= agg["vol"]/r["vol"] <= VOL_HI and agg["n"] >= 24)
    # row-level integrity (guards against the summarising fetch layer shifting/garbling columns): OHLC consistency and bar-to-bar continuity
    g2 = g.reset_index(drop=True)
    bad_rows = int(((g2["low"] > g2[["open", "close"]].min(axis=1) + 0.06) | (g2["high"] < g2[["open", "close"]].max(axis=1) - 0.06) | ((g2["volume"] <= 0) & (g2.index < len(g2) - 1))).sum())   # last (15:15) bar may legitimately show 0 volume: closing-auction window
    cont = (g2["open"].iloc[1:].values / g2["close"].iloc[:-1].values - 1)
    bad_cont = int((np.abs(cont) > 0.004).sum())
    ok = ok and bad_rows == 0 and bad_cont == 0
    rows.append((day, "PASS" if ok else "FAIL", dict(n=agg["n"], d_open=round(agg["open"]-r["open"],2), d_high=round(agg["high"]-r["high"],2),
                 d_low=round(agg["low"]-r["low"],2), d_close=round(agg["close"]-r["close"],2), vol_ratio=round(agg["vol"]/r["vol"],4), bad_ohlc_rows=bad_rows, bad_continuity=bad_cont)))
for day, st, info in rows: print(day.date(), st, info)
pd.DataFrame([(str(a.date()), s) for a, s, _ in rows], columns=["date", "status"]).to_csv("data/processed/intraday_validation.csv", index=False)
print("sessions:", len(rows), "pass:", sum(s == "PASS" for _, s, _ in rows))
