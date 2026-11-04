"""Build the v2 forecast record (information cutoff 2026-10-13 22:00 IST) from the frozen v1 record plus the adjustments that pass a fixed adoption rule.

Adoption rule (written before the record was built): an input changes the v1 distribution only if (i) a workstream labels it validated_out_of_sample under a
fixed chronological protocol, (ii) an independent verifier reproduced the number from raw data without the analyst's code, and (iii) it also passes the frozen
v1 Validation+Final window gate or is not a regime artefact.  Everything else is reported as a sensitivity, not applied.

Passes: previous US session S&P 500 -> opening gap G (slope 0.2755) and -> close-to-close R (slope 0.305); research/v2/03_market_linkages.md and verify_linkages.md.
Fails (not applied): BSE own lagged return (fails Validation+Final: -0.70%), peers' lags, regime-conditional scale (whole-registry Holm not significant), event overlay
changes (unquantifiable).  The v1 record is never modified; this writes results/forecast_record_2026-10-14_v2.json.

Usage (repo root): python3 src/finalize_v2.py
"""
from __future__ import annotations

import copy
import datetime as dt
import json
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd

import models as P
from common import load_bse, targets
from forecast_live import SELECT, live_sigma

V1 = "results/forecast_record_2026-10-14.json"
OUT = "results/forecast_record_2026-10-14_v2.json"
rec1 = json.loads(Path(V1).read_text())
rec = copy.deepcopy(rec1)
P0 = rec1["reference_price_P0"]

# ---- adjustment (all inputs time-stamped before the 22:00 IST cutoff; see research/v2/03_market_linkages.md, live_state)
SPX_LAST, SPX_PREV = 7797.72, 7807.24                  # 21:47 IST snapshot (Yahoo 5-min bars, unofficial) vs 12-Oct close (FRED/Yahoo)
x_spx = float(np.log(SPX_LAST / SPX_PREV))
SPX_MEAN = 0.00053                                      # sample mean daily S&P log return used by the analyst (0.053%)
SLOPE_G, SLOPE_R = 0.2755, 0.305                         # verifier's independent re-estimates (analyst: 0.276 / 0.304)
dG = SLOPE_G * (x_spx - SPX_MEAN)
dR = SLOPE_R * (x_spx - SPX_MEAN)

# ---- model draws exactly as in src/scenarios.py (500 equally weighted standardised-residual outcomes)
d = load_bse()
t = targets(d); n = len(d)
x, v = t["R"].values, t["v"].values
s = live_sigma(x, v, SELECT["R"])
lo = max(0, n - P.Z_WINDOW)
z = x[lo:n] / s[lo:n]; z = z[np.isfinite(z)]; z = z - np.median(z)
sig = float(s[n])
R0 = sig * z
R2 = R0 + dR
price = lambda r: P0 * np.exp(r)  # noqa: E731
grid = [0.025, 0.05, 0.1, 0.25, 0.5, 0.75, 0.9, 0.95, 0.975]
keys = [f"q{g:g}" for g in grid]

for key in ("R", "G"):
    sh = dR if key == "R" else dG
    q = rec["log_return_quantiles"][key]
    rec["log_return_quantiles"][key] = {k: (val + sh if k.startswith("q") else val) for k, val in q.items()}
    rec["price_quantiles"][key] = {k: round(float(price(rec["log_return_quantiles"][key][k])), 2) for k in keys}
# I (open-to-close, conditional on the open) is unchanged by an overnight shift; the day's high/low move with the level (approximation: shift by dR)
for k in ("Hp", "Lp"):
    q = rec["ohlc_bootstrap_log_quantiles"][k]
    rec["ohlc_bootstrap_log_quantiles"][k] = {kk: val + dR for kk, val in q.items()}
    rec["ohlc_bootstrap_price_quantiles"][k] = {kk: round(float(price(val)), 2) for kk, val in rec["ohlc_bootstrap_log_quantiles"][k].items()}

# ---- probabilities and scenarios from the shifted draws
cut = 0.015
bear, bull = R2 <= -cut, R2 >= cut
base = ~(bear | bull)
sc = {}
for name, m in (("bearish (R <= -1.5%, close <= 3324.8)", bear), ("base (-1.5% < R < +1.5%, close 3324.8-3426.0)", base), ("bullish (R >= +1.5%, close >= 3426.0)", bull)):
    r = R2[m]
    sc[name] = {"model_probability": round(float(m.mean()), 4), "close_p10_p50_p90": [round(float(price(np.quantile(r, q))), 1) for q in (0.1, 0.5, 0.9)]}
rec["scenarios"] = sc
rec["probabilities"] = {
    "P(close>P0) [shift only; still NOT a validated directional claim]": round(float((R2 > 0).mean()), 3),
    "P(|R|<0.5%)": round(float((np.abs(R2) < 0.005).mean()), 3), "P(|R|<1%)": round(float((np.abs(R2) < 0.01).mean()), 3),
    "P(R>+2%)": round(float((R2 > 0.02).mean()), 3), "P(R<-2%)": round(float((R2 < -0.02).mean()), 3),
    "P(R>+4%)": round(float((R2 > 0.04).mean()), 3), "P(R<-4%)": round(float((R2 < -0.04).mean()), 3),
    "note": rec1["probabilities"]["note"],
}

# ---- sensitivities that are reported but NOT applied
sens = {}
for lab, mult in (("regime_stressed_sigma_x1.045", 1.045), ("events_catalyst_lands_x1.18_to_1.37", 1.18)):
    r = R2 * mult
    sens[lab] = {"close_quantiles(2.5,5,25,50,75,95,97.5)": [round(float(price(np.quantile(r, q))), 1) for q in (0.025, 0.05, 0.25, 0.5, 0.75, 0.95, 0.975)]}
sens["own_lag_not_applied"] = "BSE R(13 Oct) = +1.35%; coefficient ~0.105 would shift the mean by +0.14 pp (= 0.06 sigma); fails the frozen Validation+Final gate (OOS R2 -0.70%) so NOT applied."

def git(*a): return subprocess.run(["git", *a], capture_output=True, text=True).stdout.strip()

rec.update({
    "forecast_record_version": "2.0",
    "supersedes_but_does_not_replace": V1,
    "information_cutoff_ist": "2026-10-13T22:00:00+05:30",
    "generated_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
    "TIMESTAMP_LIMITATION": "Written and committed AFTER the 2026-10-14 open (sandbox idle overnight). The information set is restricted to <= 2026-10-13 22:00 IST by rule and by instruction to every workstream, not by the clock; v2 is therefore NOT an independently timestamped pre-session forecast. The scorable pre-session forecast of record is v1 (commit e8a0f22, 2026-10-13 21:11 IST). The lead analyst looked at no 14-Oct price, volume or headline before this file was committed.",
    "inputs_changed_vs_v1": [
        {"input": "previous US session S&P 500 (7,797.72 at 21:47 IST vs 7,807.24)", "log_move": round(x_spx, 6), "shift_gap_log": round(dG, 6), "shift_close_log": round(dR, 6),
         "price_effect_rs": round(float(P0 * (np.exp(dR) - 1)), 2), "evidence": "research/v2/03_market_linkages.md (walk-forward OOS R2 +7.85% for G, +1.70% for R) reproduced independently in research/v2/verify_linkages.md (WF 7.854%, split 6.785%; misaligned placebo fails; passes the frozen v1 Val+Final gate); slope unstable (0.03 in 2019, 0.68 in 2026) so the effect is bounded by -0.05..-0.10 pp"},
    ],
    "inputs_checked_and_not_applied": sens,
    "inputs_unchanged": ["scale models S6/S4/HAR and the sigma forecasts (v1 sigma_R 2.478%)", "location L0 otherwise (no model passed)", "subjective event overlay (p_event 0-15%)", "reference price P0 3,375.40"],
    "new_facts_since_v1": ["Q2 FY27 board meeting Wed 4 Nov 2026 (filed 13 Oct 16:02 IST; not in window)", "no SEBI CAS/settlement circular as of 22:00 IST (listing/RSS)", "official 13 Oct Nifty 22,721.95, India VIX 14.12", "Groww Q2 results 14 Oct (call 16:00 IST); Angel One 15 Oct; 20 Oct holiday", "13 Oct 14:15 volume spike (8.9x slot median) has no identified cause (not_found)"],
    "directional_verdict": "Range/volatility forecast only. No directional skill demonstrated by any workstream under the frozen gate; the only validated linkage (prior-US-session S&P -> gap) moves the centre by about -0.05% (Rs 1.7), 0.02 sigma.",
    "code_commit": git("rev-parse", "HEAD"), "code_tree_dirty": bool(git("status", "--porcelain", "--untracked-files=no")),
})
Path(OUT).write_text(json.dumps(rec, indent=1))
print("wrote", OUT, "dG=%.5f dR=%.5f shift_rs=%.2f" % (dG, dR, P0 * (np.exp(dR) - 1)))
print(json.dumps({"price_R": rec["price_quantiles"]["R"], "scenarios": sc, "probs": rec["probabilities"]}, indent=1))
