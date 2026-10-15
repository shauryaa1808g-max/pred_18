"""Write the datasets behind the BSE prediction dashboard (dashboard/data/*.json) from the stored records, scores and the lead's reconciliation tables.

Run from the repo root:  python3 src/build_dashboard_data.py
Inputs: results/forecast_record_2026-10-14[_v2].json, results/forecast_score_2026-10-14[_v2].json, data/processed/bse_daily.csv (bonus-adjusted).
Curated tables (behaviour, verification, records) are transcribed from FORECAST_REPORT_V2.md sections 2, 8 and 10; they are labelled as such in the dashboard.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from common import load_bse

OUT = Path("dashboard/data")
OUT.mkdir(parents=True, exist_ok=True)
rec = {v: json.loads(Path(p).read_text()) for v, p in (("v1", "results/forecast_record_2026-10-14.json"), ("v2", "results/forecast_record_2026-10-14_v2.json"))}
sco = {v: json.loads(Path(p).read_text()) for v, p in (("v1", "results/forecast_score_2026-10-14.json"), ("v2", "results/forecast_score_2026-10-14_v2.json"))}
P0 = rec["v1"]["reference_price_P0"]
QS = ["0.025", "0.05", "0.1", "0.25", "0.5", "0.75", "0.9", "0.95", "0.975"]


def dump(name, rows):
    (OUT / f"{name}.json").write_text(json.dumps(rows, indent=0, ensure_ascii=False))
    print(name, len(rows))


# --- daily bars, bonus-adjusted (last 80 sessions)
d = load_bse()
f = d["ca_factor"].fillna(1.0).values
suf = np.concatenate([np.cumprod(f[::-1])[::-1][1:], [1.0]])
adj = pd.DataFrame({k: d[k].values / suf for k in ("open", "high", "low", "close")}, index=d.index)
adj["volume"] = d["vol"].values
bars = adj.iloc[-80:]
dump("daily_bars", [{"date": ix.strftime("%Y-%m-%d"), **{k: round(float(r[k]), 2) for k in ("open", "high", "low", "close")}, "volume": int(r["volume"])} for ix, r in bars.iterrows()])

# --- quantile ladder
rows = []
for v in ("v1", "v2"):
    r = rec[v]
    for measure, node in (("open", r["price_quantiles"]["G"]), ("close", r["price_quantiles"]["R"]), ("high", r["ohlc_bootstrap_price_quantiles"]["Hp"]), ("low", r["ohlc_bootstrap_price_quantiles"]["Lp"])):
        for q in QS:
            rows.append({"record": v, "measure": measure, "q": float(q), "price": round(float(node[f"q{q}"]), 2)})
dump("quantiles", rows)

# --- summary (one row per record)
rl = sco["v2"]["realised"]
rows = []
for v in ("v1", "v2"):
    r = rec[v]
    pq = r["price_quantiles"]["R"]
    rows.append({"record": v, "version": r["forecast_record_version"], "p0": P0, "close_p05": pq["q0.05"], "close_p25": pq["q0.25"], "close_median": pq["q0.5"], "close_p75": pq["q0.75"], "close_p95": pq["q0.95"],
                 "sigma_r_pct": round(100 * r["log_return_quantiles"]["R"]["sigma"], 3), "range_median_pct": round(r["price_quantiles"]["rho_pct_of_price"]["q0.5"], 2),
                 "p_up": list(r["probabilities"].values())[0] if v == "v1" else list(r["probabilities"].values())[0]})
dump("summary", rows)

# --- realised session (one row)
R = sco["v2"]["targets"]["R"]["y"]
sig = rec["v2"]["log_return_quantiles"]["R"]["sigma"]
dump("realised", [{"date": "2026-10-14", "open": rl["open"], "high": rl["high"], "low": rl["low"], "close": rl["close"], "volume": int(rl["volume"]), "r_pct": round(100 * (np.exp(R) - 1), 3), "abs_r_over_sigma": round(abs(R) / sig, 3), "scenario": "base", "source": "NSE CM UDiFF bhavcopy 2026-10-14"}])

# --- scenarios
trig = {"bearish": "SEBI keeps or blends the closing-auction price for expiry settlement; weak open with peers; global sell-off; weak Groww Q2 read-through.",
        "base": "No circular; ordinary market; open near the reference price.",
        "bullish": "SEBI adopts last-30-minute VWAP for derivative settlement (largely priced after +10.8% since 1 Oct); pre-open above +0.5% with peers firm."}
rows = []
for v in ("v1", "v2"):
    for name, s in rec[v]["scenarios"].items():
        key = name.split(" ")[0]
        rows.append({"record": v, "scenario": key, "definition": name.split("(", 1)[1].rstrip(")") if "(" in name else name, "probability": round(s["model_probability"], 4),
                     "close_p10": s.get("close_p10_p50_p90", s.get("close_range_p10_p50_p90"))[0], "close_p50": s.get("close_p10_p50_p90", s.get("close_range_p10_p50_p90"))[1], "close_p90": s.get("close_p10_p50_p90", s.get("close_range_p10_p50_p90"))[2],
                     "favoured_by": trig[key]})
dump("scenarios", rows)

# --- scorecard
rows = []
labels = {"R": "Close (close-to-close)", "G": "Open gap", "I": "Open-to-close", "rho": "Day range", "Hp": "Day high", "Lp": "Day low"}
for t in ("R", "G", "I", "rho", "Hp", "Lp"):
    a, b = sco["v1"]["targets"][t], sco["v2"]["targets"][t]
    rows.append({"target": labels[t], "realised_log_pct": round(100 * a["y"], 3), "v1_pinball_e4": round(1e4 * a["pinball"], 2), "v2_pinball_e4": round(1e4 * b["pinball"], 2),
                 "inside_50": "yes" if a.get("inside_50") else ("n/a" if "inside_50" not in a else "no"), "inside_90": "yes" if a.get("inside_90") else "no"})
dump("scorecard", rows)

# --- behaviour profile (transcribed from FORECAST_REPORT_V2.md section 2)
B = [
 ("Follows the market", "Same-day beta to Nifty 50 = 0.89 (CI 0.77-1.01), corr 0.35; yearly beta 0.28 to 1.82, break near 2021-03", "2,388 sessions, 2017-2026", "descriptive", "Beta as a scenario mapping given the same-day index move is validated (OOS R2 12.6%); it does not forecast the index"),
 ("Mostly idiosyncratic", "87.5% of daily variance is not explained by Nifty (75.9% in the last 250 sessions)", "2,388", "descriptive", ""),
 ("Sector co-movement", "Beta to Nifty Capital Markets 1.47, corr 0.81", "513, 2024-09 on", "descriptive", "BSE is a constituent: about 44% of the covariance is mechanical"),
 ("Lead or lag", "No index or VIX lag survives Holm; CDSL and Angel One lags do, but BSE adds only +0.05% OOS R2 once the peer's own lag is controlled", "130 cells", "not_found", "Leadership not established; persistence explains about half"),
 ("Overnight cue to gap", "Previous US session S&P 500 predicts BSE's opening gap: slope 0.276 pp per 1%, OOS R2 +7.85% (walk-forward), +6.79% (split)", "2,313", "validated_out_of_sample", "Independently reproduced; slope unstable (0.03 in 2019, 0.68 in 2026); effect on the 14 Oct centre about -0.05 pp"),
 ("Declines and VIX", "Down-market beta 1.00 vs up 0.76 (Holm p 0.61); beta by VIX tercile 1.07 / 1.04 / 0.85", "2,388", "not_found", "Stress correlation rise is a variance artefact"),
 ("Rates, FX, commodities", "US 10-year and Brent: no association; USD/INR predicts the gap but is not incremental to the S&P", "2,300+", "not_found", "Brent series is Dated spot, not futures"),
 ("Momentum vs mean reversion", "Lag-1 autocorrelation +0.105; yesterday's return OOS R2 +0.95%", "2,388", "descriptive", "Fails the fixed gate in Validation (-0.71%) and Final (-0.68%); VWAP-close explanation refuted; not applied"),
 ("Gap continuation vs reversal", "After gap-ups of 0.5 sigma or more the intraday move continued 33% (n 234) before 2024-07, 70% (n 37) to 2026-08-02, 50% (n 4) since", "275 gap-ups", "descriptive", "Period difference is real but gradual; not a stable rule"),
 ("Gaps since the closing auction", "Open equals previous close on 8 of 50 sessions (125 of 2,388 overall); the 14 Oct open was exactly the previous close", "50 sessions", "not_found", "Cause date not identified"),
 ("Volume vs breakouts", "Closes beyond the prior 20-day high or low, with or without volume or delivery confirmation: no persistence or reversal", "158 up, 165 down", "not_found", "Volume and absolute return correlate (Spearman 0.42) in every liquidity state"),
 ("Event reactions", "Event sessions move more (|z| 1.78 vs 0.75), but 15 of 27 events were dated from the dossier's reaction day", "27 events, 7-10 earnings", "descriptive", "Selection-light premium about 1.1-1.3; sign rule not usable (12/14 vs 2/6 by timing evidence)"),
 ("Regimes", "13 Oct is 'stressed' only through the Nifty-drawdown prong; S6 90% interval needs about +4-5% at most", "2,388", "descriptive", "50% body narrow (kappa 1.10; whole-registry Holm 0.34); sigma unchanged"),
 ("Opening, midday, closing", "First hour: 26.5% of volume, 46.7% of variance; highs or lows set in the first hour 83.8% vs 84.9% for a random walk with the same variance clock", "37 sessions", "descriptive", "Not a distinct pattern; first-hour direction does not predict the rest of the day"),
 ("Prior-day levels", "Previous-day high touched 71% vs 73% random walk; the specialist's 'persistence at prior lows' label was refuted by the verifier", "2,368", "descriptive", "Drift artefact, downgraded"),
 ("Structural change", "0 of 54 pre-specified break cells survive family correction; largest: turnover x5.6 near 2024-10-01 (Holm 0.12)", "54 tests", "not_found", "Association only; no cause is inferred"),
]
dump("behaviour", [{"pattern": a, "result": b, "sample": c, "status": s, "caveat": e} for a, b, c, s, e in B])

# --- verification (counts from the verifier result files; headline corrections from FORECAST_REPORT_V2.md section 10)
V = [
 ("Market linkages", "minor", 11, 2, 2, "S&P to gap/close, beta, lead-lag confirmed; own-lag and peer 'validated' labels downgraded; VWAP-mechanism sentence refuted"),
 ("Fundamentals", "minor", 4, 3, 1, "Numbers match primary sources; 'predates the Reuters report' is an inference; news contradiction resolved in its favour"),
 ("News and catalysts", "major", 4, 3, 1, "'0 filings / no Q2 intimation' refuted (Q2 board is 4 Nov); cutoff claim only partly true; 5 Oct attribution unproven"),
 ("Momentum, gaps, volume", "minor", 9, 2, 1, "Point estimates exact; VWAP mechanism refuted; era decline and momentum decay not statistically established"),
 ("Intraday structure", "major", 16, 3, 1, "'Validated' prior-low persistence refuted (drift artefact); threshold computed over 37 sessions incl. zeros; 10-Sep exclusion rule too blunt"),
 ("Events and breaks", "minor", 9, 5, 0, "15 of 27 events outcome-dated, premium falls to about 1.1-1.3; catalyst sigma multipliers untested; centre unchanged"),
]
dump("verification", [{"workstream": a, "severity": s, "confirmed": c, "partial": p, "refuted": r, "headline": h} for a, s, c, p, r, h in V])

# --- records and provenance
dump("records", [
 {"record": "v1", "role": "Forecast of record", "file": "results/forecast_record_2026-10-14.json", "commit": "e8a0f22", "committed_ist": "2026-10-13 21:11", "cutoff_ist": "2026-10-13 16:55", "status": "Pre-session, frozen"},
 {"record": "v2", "role": "Late update", "file": "results/forecast_record_2026-10-14_v2.json", "commit": "dfb99f1", "committed_ist": "2026-10-14 21:00", "cutoff_ist": "2026-10-13 22:00", "status": "Committed after the session; information set limited by rule, not by clock"},
 {"record": "score", "role": "Scoring", "file": "results/forecast_score_2026-10-14[_v2].json", "commit": "3603234", "committed_ist": "after both records", "cutoff_ist": "n/a", "status": "Official NSE bhavcopy, 14 Oct"},
])
