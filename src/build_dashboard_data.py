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

# --- live close replay (results/nowcast_replay_latest.csv from `python3 src/live_nowcast.py --replay`) vs the final close of that session
from pathlib import Path as _P
rp = pd.read_csv("results/nowcast_replay_latest.csv")
extra = _P("data/processed/bse_daily_extra.csv")
FINAL, SRC = 3428.0, "Yahoo last print 15:28 IST (unofficial; NSE official file due about 16:34 IST)"
if extra.exists():
    e = pd.read_csv(extra, index_col=0, parse_dates=True)
    if pd.Timestamp("2026-10-15") in e.index:
        FINAL, SRC = float(e.loc["2026-10-15", "close"]), "NSE official bhavcopy 2026-10-15"
rows = []
for _, r in rp.iterrows():
    rows.append({"asof": r["asof"], "price_then": round(float(r["price_then"]), 1), "close_50_lo": round(float(r["close_50_lo"]), 1), "close_50_hi": round(float(r["close_50_hi"]), 1),
                 "close_90_lo": round(float(r["close_90_lo"]), 1), "close_90_hi": round(float(r["close_90_hi"]), 1), "typical_miss_rs": round(float(r["typical_miss_rs"]), 1),
                 "final_close": FINAL, "inside_50": "yes" if r["close_50_lo"] <= FINAL <= r["close_50_hi"] else "no", "inside_90": "yes" if r["close_90_lo"] <= FINAL <= r["close_90_hi"] else "no",
                 "error_rs": round(FINAL - float(r["price_then"]), 1), "session": "2026-10-15", "final_source": SRC})
dump("nowcast_replay", rows)

# --- scoreboard (summary row first, then one row per scored day)
sb = _P("results/scoreboard/scoreboard.csv")
S = pd.read_csv(sb) if sb.exists() else pd.DataFrame()
n = len(S)
def _m(c): return round(float(np.mean(np.abs(S[c]))), 1) if n else None
h = S["lean_hit"].dropna().astype(bool) if n else pd.Series(dtype=bool)
summ = {"kind": "summary", "scored_sessions": n, "open_miss_rs": _m("open_miss_rs"), "open_miss_unchanged_rs": _m("open_miss_unchanged_rs"), "close_miss_rs": _m("close_miss_rs"), "close_miss_unchanged_rs": _m("close_miss_unchanged_rs"),
        "lean_right": int(h.sum()) if n else 0, "lean_n": int(len(h)), "pt1_trades": int(S["PT1_net_pct"].notna().sum()) if n else 0, "pt1_avg_net_pct": round(float(S["PT1_net_pct"].mean()), 3) if n and S["PT1_net_pct"].notna().any() else None,
        "pt2_trades": int(S["PT2_net_pct"].notna().sum()) if n else 0, "pt2_avg_net_pct": round(float(S["PT2_net_pct"].mean()), 3) if n and S["PT2_net_pct"].notna().any() else None,
        "note": "The Fri 16 Oct entry was issued at 08:36 IST and committed at 08:36:41 IST (commit 40ab965), before the open: lean up for the close and down from open to close; PT1 short at the open, PT2 no trade. It is scored after the official file at about 16:34 IST." if not n else "Running totals over all scored sessions."}
days = [] if not n else [{"kind": "day", "date": r["date"], "open": r["open"], "close": r["close"], "open_miss_rs": round(r["open_miss_rs"], 1), "close_miss_rs": round(r["close_miss_rs"], 1), "close_inside_90": "yes" if r["close_in90"] else "no",
                           "lean": r["lean_close"], "lean_hit": "yes" if r["lean_hit"] is True or str(r["lean_hit"]) == "True" else "no", "pt1_net_pct": None if pd.isna(r["PT1_net_pct"]) else round(float(r["PT1_net_pct"]), 2), "pt2_net_pct": None if pd.isna(r["PT2_net_pct"]) else round(float(r["PT2_net_pct"]), 2)} for _, r in S.iterrows()]
dump("scoreboard", [summ] + days)


# --- NSE pre-open price vs the official open (one row per session with a saved pre-open snapshot)
import glob as _g, json as _j
rows = []
for f in sorted(_g.glob("results/preopen/BSE_*.jsonl")):
    snaps = [_j.loads(l) for l in _P(f).read_text().splitlines() if l.strip()]
    fin = [z for z in snaps if float(z["pre"].get("finalPrice") or 0) > 0 and float(z["pre"].get("finalQuantity") or 0) > 0]   # FINAL = NSE filled finalPrice (never by the clock)
    if not fin: continue
    z = fin[-1]; day = pd.to_datetime(z["pre"]["lastUpdateTime"][:11]).strftime("%Y-%m-%d")
    off = float(e.loc[day, "open"]) if extra.exists() and pd.Timestamp(day) in e.index else None
    rows.append({"date": day, "preopen_price": float(z["pre"]["finalPrice"]), "previous_close": float(z["pre"]["prevClose"]), "buy_qty": int(z["pre"]["totalBuyQuantity"]), "sell_qty": int(z["pre"]["totalSellQuantity"]),
                 "read_at_ist": z["pre"]["lastUpdateTime"][-8:], "official_open": off, "miss_rs": None if off is None else round(off - float(z["pre"]["IEP"]), 2)})
rows = rows[::-1]
dump("preopen", rows if rows else [{"date": "none yet", "preopen_price": None, "previous_close": None, "buy_qty": None, "sell_qty": None, "read_at_ist": None, "official_open": None, "miss_rs": None}])


# --- today's session: the calls made before the open against what has happened so far (rebuilt through the day)
import sys as _sys
_sys.path.insert(0, "src")
from hl_model import hl_forecast
ent_files = sorted(_g.glob("results/scoreboard/entries/*.json"))
if ent_files:
    ent = _j.loads(_P(ent_files[-1]).read_text()); D = ent["target_session"]
    hp = _j.loads(_P(f"results/hl_dayahead_{D}.json").read_text()); pre = hp["pre_open"]
    nl = [_j.loads(l) for l in _P("results/nowcast_log.jsonl").read_text().splitlines() if l.strip()]
    nl = [z for z in nl if z["asof_ist"][:10] == D]
    last = nl[-1] if nl else None
    pf = [r for r in (_j.loads(l) for f in _g.glob(f"results/preopen/BSE_{D}.jsonl") for l in _P(f).read_text().splitlines() if l.strip()) if r["pre"]["lastUpdateTime"][-8:] >= "09:08:00" and float(r["pre"].get("finalPrice") or 0) > 0]
    pre_open_price = float(pf[-1]["pre"]["finalPrice"]) if pf else None
    official = e.loc[D] if extra.exists() and pd.Timestamp(D) in e.index else None
    open_now = float(official["open"]) if official is not None else pre_open_price
    hh = last["asof_ist"][11:16] if last else None
    def _land(v, lo50, hi50, lo90, hi90, settled):
        if v is None: return "not known yet"
        w = "inside the half-the-time range" if lo50 <= v <= hi50 else ("inside the 9-in-10 range, outside the half-the-time range" if lo90 <= v <= hi90 else "outside the 9-in-10 range")
        return w if settled else w + " (so far)"
    def _row(measure, q, best, actual, status, asof, settled):
        return {"measure": measure, "best_guess": round(best, 1), "lo50": round(q["q25"] if "q25" in q else q["q0.25"], 1), "hi50": round(q["q75"] if "q75" in q else q["q0.75"], 1), "lo90": round(q["q5"] if "q5" in q else q["q0.05"], 1),
                "hi90": round(q["q95"] if "q95" in q else q["q0.95"], 1), "actual": None if actual is None else round(actual, 1), "status": status, "as_of": asof,
                "landed": _land(actual, *( (q["q25"] if "q25" in q else q["q0.25"]), (q["q75"] if "q75" in q else q["q0.75"]), (q["q5"] if "q5" in q else q["q0.05"]), (q["q95"] if "q95" in q else q["q0.95"]) ), settled)}
    oq, cq = ent["open"]["price"], ent["close"]["price"]
    hq, lq = pre["high"]["price_quantiles"], pre["low"]["price_quantiles"]
    if official is not None:
        rows = [_row("Open", oq, oq["q0.5"], float(official["open"]), "final (official)", "NSE bhavcopy", True), _row("High", hq, hq["q50"], float(official["high"]), "final (official)", "NSE bhavcopy", True),
                _row("Low", lq, lq["q50"], float(official["low"]), "final (official)", "NSE bhavcopy", True), _row("Close", cq, cq["q0.5"], float(official["close"]), "final (official)", "NSE bhavcopy", True)]
    else:
        hi_sf = max([x for x in (last["day_high_so_far"] if last else None, open_now) if x is not None], default=None)
        lo_sf = min([x for x in (last["day_low_so_far"] if last else None, open_now) if x is not None], default=None)
        rows = [_row("Open", oq, oq["q0.5"], open_now, "final (pre-open auction)" if open_now else "not yet", "NSE pre-open, 09:09", True), _row("High", hq, hq["q50"], hi_sf, "so far", f"{hh} IST, Yahoo plus the open", False),
                _row("Low", lq, lq["q50"], lo_sf, "so far", f"{hh} IST, Yahoo plus the open", False), _row("Close", cq, cq["q0.5"], last["price_now"] if last else None, "price now, not final", f"{hh} IST", False)]
    dump("today_check", rows)

    # the live close readings of the day (green dot = pinpoint estimate)
    seen = {}
    for z in nl:
        seen[z["asof_ist"][11:16]] = z
    fin = float(official["close"]) if official is not None else None
    lt = []
    for k in sorted(seen):
        z = seen[k]
        lt.append({"asof": k, "price_then": round(z["price_now"], 1), "close_50_lo": round(z["close_50"][0], 1), "close_50_hi": round(z["close_50"][1], 1), "close_90_lo": round(z["close_90"][0], 1), "close_90_hi": round(z["close_90"][1], 1),
                   "typical_miss_rs": round(z["typical_miss_rs"], 1), "final_close": fin, "inside_50": "pending" if fin is None else ("yes" if z["close_50"][0] <= fin <= z["close_50"][1] else "no"),
                   "inside_90": "pending" if fin is None else ("yes" if z["close_90"][0] <= fin <= z["close_90"][1] else "no"), "error_rs": None if fin is None else round(fin - z["price_now"], 1), "session": D,
                   "final_source": "not final yet: NSE official file due about 16:34 IST" if fin is None else "NSE official bhavcopy " + D})
    dump("live_today", lt if lt else [{"asof": "none yet", "price_then": None, "close_50_lo": None, "close_50_hi": None, "close_90_lo": None, "close_90_hi": None, "typical_miss_rs": None, "final_close": None, "inside_50": "pending", "inside_90": "pending", "error_rs": None, "session": D, "final_source": ""}])

    # high and low forecasts: before the open and, once the open is known, after it
    def _hl(stage, key, side, blk, post=False):
        q = blk["price_quantiles"]
        wide = (f"19 days in 20 at or below ₹{q['q95']:,.0f}; about 1 day in 25 the open itself is the high" if post and side == "High" else f"₹{q['q5']:,.0f} to ₹{q['q95']:,.0f} (9 times in 10)")
        return {"key": key, "stage": stage, "side": side, "best_guess": round(q["q50"], 1), "typical_miss_rs": round(blk["typical_miss_rs"], 1), "half_miss_rs": round(blk["half_the_time_within_rs"], 1),
                "lo50": round(q["q25"], 1), "hi50": round(q["q75"], 1), "wide": wide, "sessions": blk["miss_measured_on_sessions"]}
    hl_rows = [_hl("Before the open", "pre_high", "High", pre["high"]), _hl("Before the open", "pre_low", "Low", pre["low"])]
    if open_now is not None:
        po = hl_forecast(D, open_price=open_now)["post_open"]
        st = f"After the open (open ₹{open_now:,.1f})"
        hl_rows += [_hl(st, "post_high", "High", po["high"], True), _hl(st, "post_low", "Low", po["low"])]
    dump("hl_forecast", hl_rows)

    # evidence behind the high/low numbers (curated from research/hl/*.md and the three independent verification reports)
    EV = [
     ("Typical miss of the best guess, before the open", "High ₹43, low ₹48 (half the time within ₹34 / ₹32); 'price stays' would miss by ₹63 / ₹61", "320 sessions, 1 Jul 2025 to 15 Oct 2026", "tested", "Out of sample; independent check reproduced it from the raw files"),
     ("Typical miss once the official open is known (09:08)", "High ₹35, low ₹37; pinball loss 23% lower than before the open (Holm p < 0.001)", "320 sessions; 52 since the closing auction (same direction)", "tested", "The gain comes from the open's level, not from the gap's size or sign (those added nothing, Holm p >= 0.48)"),
     ("Do the bands hold?", "90% bands held 90.3% (high) and 88.8% (low); the after-open high band is really a 19-in-20 band (the open is the high on about 4% of days)", "320 sessions", "tested", "Wording fixed after the independent check"),
     ("Since the closing auction began", "50% bands held only about 40% of the time; the real high fell below its own 5% line on 15% of days (8 of 52)", "52 sessions", "caution", "Small sample, suggestive; the high is the shakier of the two numbers"),
     ("Any extra variable (gap, weekday, range model, Garman-Klass)", "None beat the project baseline; the volatility model helps the high against raw history, ties for the low", "34 variant-target pairs, Holm-corrected", "not_found", "Gain is in the band shape, not the best guess"),
     ("More parameters (study D): India VIX, US overnight, Indian market and peers, BSE own history, calendar, option-implied volatility", "None made the high or low more precise: 0 of 46 variant-target pairs passed the pre-fixed rule. Best pair: pre-open high 2.4% lower loss, typical miss ₹41.8 against ₹42.7. After the open, adding inputs made the low worse (typical miss ₹38.6 against ₹37.4)", "320 sessions; 46 pairs, Holm-corrected", "not_found", "A true gain of 1% to 3% (₹0.4 to ₹1.3) can be neither confirmed nor excluded; independent check found no look-ahead"),
     ("Flexible models (study E): quantile regression, boosting, forest, conformal, stacks on the same inputs", "0 of 72 pairs passed; no eligible variant gained more than 1.5%; every variant within about ₹1.5 of the baseline's typical miss", "320 sessions; 72 pairs, Holm-corrected", "not_found", "Reads as 'no gain shown' (power about 23% against a true 2% gain), not 'no gain exists'"),
     ("Comparable past days (study G, 'watch the past to shape the future')", "0 of 172 pairs passed. The median of the five most similar past days misses by ₹46 / ₹52 / ₹41 / ₹42 against ₹43 / ₹48 / ₹35 / ₹37 for the model: worse", "320 sessions; 172 pairs; 80 nearest days are only about 27 separate episodes", "not_found", "The context adds nothing beyond the volatility the model already uses"),
     ("One lead, not a finding: the S&P 500's last session shifting the whole pre-open range", "About 2% to 3% lower loss in two studies, in the same direction; not significant after correcting for the number of things tried (Holm 0.25 to 1.0)", "320 sessions; chosen after looking, so optimistic", "caution", "Not used in any forecast; needs forward testing before use"),
     ("Live running high and low: do the printed bands hold?", "Final high / low 'half the time' bands held 54% / 57%; 'nine times in ten' held 88% / 88%", "39 sessions, 8 checkpoints each (strongly dependent)", "tested", "Real uncertainty is about +-16 points on a 50% cell; the tool ignores the official open, so the high floor can be a few rupees low"),
     ("'The high is already in' probability", "Conservative: stated 62% was followed by 81% (15-minute data) and 61% by 72% (hourly)", "167 and 918 states", "tested", "Fails in the 90-100% bin (stated 97.5%, observed 91.3%, two sessions)"),
     ("The live tool's 'another Rs X-Y is typical' line and 'chance of at least Rs 5/10/20/40'", "The typical-extension line contained the real extension only 33-36% of the time (intended 50%); the chance of a given extension runs 4-9 points too high", "80 high and 141 low extension states", "caution", "Do not rely on these two lines"),
     ("Yahoo against the NSE official high and low", "Official high above Yahoo's by ₹0.2 typically (mean 0.9, 95th percentile 4.0); official low below by ₹0.7 (mean 1.1, 95th percentile 3.9)", "39 sessions of 15-minute bars", "tested", "A few rupees either way; on gap-open days the official open can sit outside every Yahoo bar"),
     ("Trade a limit buy at the estimated low, exit at the close", "Lost ₹14 a share net of a 0.10% round-trip cost (85 fills of 320)", "320 sessions", "not_found", "The level is reached as often as promised (26.6%) but the price does not turn there"),
     ("Trade a limit sell at the estimated high, exit at the close", "Lost ₹9.9 a share net of cost (78 fills of 320)", "320 sessions", "not_found", "Same: reached 24.4% of days against 25% promised"),
     ("Follow a break of the first-hour range to the close", "+0.47% a trade in one six-month window, +0.04% after, -0.14% since the closing auction", "daily and hourly history", "not_found", "Looks like an edge in one window, then fades; not usable"),
    ]
    dump("hl_evidence", [{"item": a, "result": b, "sample": c, "status": st_, "caveat": d_} for a, b, c, st_, d_ in EV])


    # the hour-by-hour tables given to the user today (one row per live table) and how each one's next-hour call turned out once its own window ended
    hl = [_j.loads(l) for l in _P("results/hourly_table_log.jsonl").read_text().splitlines() if l.strip()] if _P("results/hourly_table_log.jsonl").exists() else []
    hl = [z for z in hl if z["date"] == D and z["mode"] == "live"]
    sc = pd.read_csv("results/hourly_table_scored.csv") if _P("results/hourly_table_scored.csv").exists() else pd.DataFrame()
    sc = sc[sc["date"].astype(str) == D] if len(sc) else sc
    rows = []
    for z in hl:
        nh = z.get("next_hour"); r = None if not len(sc) else sc[sc["asof"].astype(str) == z["asof"]]
        done = r is not None and len(r) > 0
        rows.append({"time": z["asof"], "close_pin": z["close_pin"], "close_50_lo": z["close_50"][0], "close_50_hi": z["close_50"][1], "close_90_lo": z["close_90"][0], "close_90_hi": z["close_90"][1],
                     "window": f"{nh['window_start']}-{nh['window_end']}" if nh else "market closes", "high_pin": nh["high"]["0.5"] if nh else None, "low_pin": nh["low"]["0.5"] if nh else None,
                     "act_high": float(r.act_high.iloc[0]) if done else None, "act_low": float(r.act_low.iloc[0]) if done else None,
                     "high_error": round(float(r.act_high.iloc[0] - r.pred_high.iloc[0]), 1) if done else None, "low_error": round(float(r.act_low.iloc[0] - r.pred_low.iloc[0]), 1) if done else None,
                     "status": ("scored after its window ended" if done else ("no next-hour call (market closes)" if not nh else "window not over or not scored yet"))})
    dump("hourly_rows", rows if rows else [{"time": "none yet", "close_pin": None, "close_50_lo": None, "close_50_hi": None, "close_90_lo": None, "close_90_hi": None, "window": "", "high_pin": None, "low_pin": None, "act_high": None, "act_low": None, "high_error": None, "low_error": None, "status": "no live table yet"}])
