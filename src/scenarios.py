"""Scenario partition + subjective event-risk sensitivity built on a stored forecast record.

Partition probabilities are MODEL-BASED (trailing-500 standardised-residual distribution of the selected close-to-close model; only the 90%/95% interval
coverage of that model was validated).  The event-risk overlay is SUBJECTIVE: the probability that a decisive SEBI settlement/CAS headline affects the
session is a judgement, and the magnitudes come from a small, hand-picked (hence biased toward large moves) set of dated analogues in research/02.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

import models as P
from common import EPS, GRID, load_bse, targets
from forecast_live import SELECT, live_sigma

rec_path = sys.argv[1] if len(sys.argv) > 1 else "results/forecast_record_2026-10-14.json"
rec = json.loads(Path(rec_path).read_text())
P0 = rec["reference_price_P0"]
d = load_bse()
if d.index[-1] < pd.Timestamp(rec["data_last_session"]):
    row = rec["last_bar"]
    d = pd.concat([d, pd.DataFrame({"prev": [d["close"].iloc[-1]], "open": [row["open"]], "high": [row["high"]], "low": [row["low"]], "close": [row["close"]], "vol": [row["vol"]]}, index=[pd.Timestamp(rec["data_last_session"])])])
t = targets(d); n = len(d)
x, v = t["R"].values, t["v"].values
s = live_sigma(x, v, SELECT["R"])
lo = max(0, n - P.Z_WINDOW)
z = x[lo:n] / s[lo:n]; z = z[np.isfinite(z)]; z = z - np.median(z)
sig = s[n]
R = sig * z                       # 500 equally weighted model outcomes for the log close-to-close return
cut = 0.015
bear, bull = R <= -cut, R >= cut
base = ~(bear | bull)
price = lambda r: P0 * np.exp(r)                                                  # noqa: E731
out = {"P0": P0, "sigma_R": float(sig), "cut_log_return": cut, "n_draws": int(len(R)), "scenarios": {}}
for name, m in (("bearish: R <= -1.5%", bear), ("base: -1.5% < R < +1.5%", base), ("bullish: R >= +1.5%", bull)):
    r = R[m]
    out["scenarios"][name] = {"model_probability": float(m.mean()), "close_range_p10_p50_p90": [round(float(price(np.quantile(r, q))), 1) for q in (0.1, 0.5, 0.9)], "close_min_max": [round(float(price(r.min())), 1), round(float(price(r.max())), 1)]}
out["tail_masses"] = {"P(R<=-4%)": float((R <= -0.04).mean()), "P(R>=+4%)": float((R >= 0.04).mean()), "P(|R|>=5%)": float((np.abs(R) >= 0.05).mean())}
# --- subjective event overlay
analog_abs = np.array([13.7, 5.98, 2.45, 16.98, 1.17, 6.56, 7.56, 4.58, 9.07, 6.33, 7.30, 3.92, 4.36, 3.14, 4.39, 3.94]) / 100.0     # dossier 02 B6, |close-to-close %|, hand-picked news days
out["analog_abs_move_quantiles_pct"] = [round(100 * float(np.quantile(analog_abs, q)), 2) for q in (0.25, 0.5, 0.75)]
rng = np.random.default_rng(14)
ov = {}
for pe in (0.0, 0.05, 0.10, 0.15):
    k = 200000
    base_draw = rng.choice(R, k)
    ev = rng.random(k) < pe
    mag = rng.choice(analog_abs, k) * rng.choice([-1, 1], k)                       # symmetric ignorance on direction
    r = np.where(ev, np.log1p(mag) + 0.3 * rng.choice(R, k), base_draw)            # event day: analog move plus a little ordinary noise
    q = np.quantile(r, [0.025, 0.05, 0.25, 0.5, 0.75, 0.95, 0.975])
    ov[f"p_event={pe:.2f}"] = {"close_quantiles(2.5,5,25,50,75,95,97.5)": [round(float(price(z_)), 1) for z_ in q], "P(|R|>=4%)": float((np.abs(r) >= 0.04).mean())}
out["event_overlay_SUBJECTIVE"] = ov
Path("results/scenarios.json").write_text(json.dumps(out, indent=1))
print(json.dumps(out, indent=1))
