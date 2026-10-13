"""Chart: historical prices (solid) vs the CONDITIONAL forecast distribution for the next session (shaded, separated).  No future path is drawn.

Usage: python3 src/plot_forecast.py results/forecast_record_2026-10-14.json results/forecast_chart.png
"""
import json
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from common import load_bse

rec = json.load(open(sys.argv[1]))
outp = sys.argv[2]
P0 = rec["reference_price_P0"]
d = load_bse()
f = d["ca_factor"].fillna(1.0).values
suf = np.concatenate([np.cumprod(f[::-1])[::-1][1:], [1.0]])
adj = pd.DataFrame({k: d[k].values / suf for k in ("open", "high", "low", "close")}, index=d.index)
hist = adj.iloc[-70:]
q = rec["price_quantiles"]
hl = rec["ohlc_bootstrap_price_quantiles"]
cols = {"hist": "#1f3b5c", "up": "#2a7f62", "dn": "#b5483a", "fc": "#d98324", "fc2": "#f2c27b", "grey": "#8a8f98"}

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(13, 10.5), gridspec_kw={"height_ratios": [1.15, 1]})
# ---------------- panel 1: daily history + conditional close distribution
x = np.arange(len(hist))
for i, (dt, r) in enumerate(hist.iterrows()):
    c = cols["up"] if r.close >= r.open else cols["dn"]
    ax1.vlines(i, r.low, r.high, color=c, lw=1)
    ax1.add_patch(plt.Rectangle((i - 0.3, min(r.open, r.close)), 0.6, abs(r.close - r.open) or 0.5, color=c))
xf = len(hist) + 2.5
ax1.axvline(len(hist) - 0.3, color=cols["grey"], ls="--", lw=1)
ax1.text(len(hist) - 0.6, ax1.get_ylim()[1], "cutoff: 13-Oct close", ha="right", va="top", fontsize=8, color=cols["grey"], rotation=90)
bands = [("95%", q["R"]["q0.025"], q["R"]["q0.975"], 0.18), ("90%", q["R"]["q0.05"], q["R"]["q0.95"], 0.22), ("80%", q["R"]["q0.1"], q["R"]["q0.9"], 0.28), ("50%", q["R"]["q0.25"], q["R"]["q0.75"], 0.38)]
for lab, lo, hi, a in bands:
    ax1.add_patch(plt.Rectangle((xf - 0.9, lo), 1.8, hi - lo, color=cols["fc"], alpha=a, lw=0, hatch="///" if lab == "95%" else None))
    ax1.text(xf + 1.0, hi, f"{lab}: {lo:,.0f}-{hi:,.0f}", fontsize=8, va="center", color="#6b4410")
ax1.hlines(P0, xf - 1.2, xf + 1.2, color=cols["fc"], lw=2)
ax1.errorbar([xf - 1.5], [hl["Hp"]["q0.5"]], yerr=[[hl["Hp"]["q0.5"] - hl["Hp"]["q0.05"]], [hl["Hp"]["q0.95"] - hl["Hp"]["q0.5"]]], fmt="v", color=cols["up"], capsize=3, ms=5)
ax1.errorbar([xf - 1.5], [hl["Lp"]["q0.5"]], yerr=[[hl["Lp"]["q0.5"] - hl["Lp"]["q0.05"]], [hl["Lp"]["q0.95"] - hl["Lp"]["q0.5"]]], fmt="^", color=cols["dn"], capsize=3, ms=5)
ax1.text(xf - 1.5, hl["Hp"]["q0.95"] + 8, "day high\n(median, 90%)", fontsize=7, ha="center", color=cols["up"])
ax1.text(xf - 1.5, hl["Lp"]["q0.05"] - 22, "day low\n(median, 90%)", fontsize=7, ha="center", color=cols["dn"])
ax1.set_xlim(-1, xf + 8.5)
ax1.set_xticks(list(x[::10]) + [xf]); ax1.set_xticklabels([hist.index[i].strftime("%d-%b") for i in x[::10]] + ["14-Oct\n(forecast)"], fontsize=8)
ax1.set_ylabel("Rs (bonus-adjusted)")
ax1.set_title("BSE Ltd (NSE:BSE) — history (solid candles) vs CONDITIONAL distribution of the 14-Oct-2026 close (shaded; not a path)", fontsize=11, loc="left")
ax1.text(0.01, 0.02, f"Reference P0 = Rs {P0:,.2f} (official NSE close 13-Oct). Shaded boxes: model-based central intervals of the close. Directional skill NOT demonstrated; centre = unchanged.", transform=ax1.transAxes, fontsize=8, color=cols["grey"])
ax1.grid(alpha=0.2)

# ---------------- panel 2: last sessions intraday (15m closes) + same bands for the next session
x15 = pd.read_csv("data/processed/xlsx_15m_clean.csv")
x15["ts"] = pd.to_datetime(x15["date"].astype(str) + " " + x15["time"].astype(str))
days = sorted(x15.date.unique())[-3:]
xs, ys, ticks = [], [], []
pos = 0
for dd in days:
    g = x15[x15.date == dd]
    xs += list(range(pos, pos + len(g))); ys += list(g.close.values)
    ticks.append((pos, pd.Timestamp(dd).strftime("%d-%b")))
    pos += len(g) + 2
for dd, (t0, _) in zip(days, ticks):
    g = x15[x15.date == dd]
    ax2.plot(range(t0, t0 + len(g)), g.close.values, color=cols["hist"], lw=1.2, marker="o", ms=2.5)
for t0, lab in ticks:
    ax2.axvline(t0 - 1, color=cols["grey"], lw=0.5, ls=":")
x0 = pos + 1; w = 25
ax2.axvline(pos - 1, color=cols["grey"], ls="--", lw=1)
for lab, lo, hi, a in bands:
    ax2.add_patch(plt.Rectangle((x0, lo), w, hi - lo, color=cols["fc"], alpha=a, lw=0))
ax2.hlines(P0, x0, x0 + w, color=cols["fc"], lw=2)
ax2.text(x0 + w / 2, q["R"]["q0.025"] - 14, "14-Oct session: unconditional CLOSE bands (50/80/90/95%); the intraday PATH is not forecast", ha="center", fontsize=8, color="#6b4410")
sc = rec["scenarios"]
# draw the three scenario bars side by side
xb = x0 + w + 2
for i, ((name, s), colr) in enumerate(zip(sc.items(), (cols["dn"], cols["grey"], cols["up"]))):
    lo, med, hi = s["close_p10_p50_p90"]
    xx = xb + i * 3.2
    ax2.vlines(xx, lo, hi, color=colr, lw=7, alpha=0.85)
    ax2.plot([xx], [med], marker="_", ms=14, color="k")
    ax2.text(xx, hi + 6, f"{name.split(' ')[0]}\n{100*s['model_probability']:.0f}%", fontsize=8, ha="center", color=colr)
ax2.set_xlim(-1, xb + 11); ax2.set_ylim(q["R"]["q0.025"] - 45, q["R"]["q0.975"] + 45)
ax2.set_xticks([t[0] for t in ticks] + [x0 + w / 2]); ax2.set_xticklabels([t[1] for t in ticks] + ["14-Oct"], fontsize=8)
ax2.set_ylabel("Rs (15-minute closes)")
ax2.set_title("Last three sessions (15-minute closes, Yahoo API workbook) | conditional close bands and scenario close ranges (10-50-90th pct) for 14-Oct", fontsize=10, loc="left")
ax2.grid(alpha=0.2)
fig.text(0.01, 0.005, f"Generated from {sys.argv[1]} (commit {rec.get('code_commit','?')[:7]}). Model-based and uncertain; scenario probabilities come from the close distribution partition at +/-1.5%. Not investment advice.", fontsize=7, color=cols["grey"])
plt.tight_layout(rect=(0, 0.015, 1, 1))
plt.savefig(outp, dpi=140)
print("saved", outp)
