"""Assemble the dated forecast record: base record (forecast_live.py) + scenarios (scenarios.py) + provenance, invalidation conditions and honesty labels.
The record is written once; src/score_forecast.py scores it afterwards and never edits it."""
import json
import sys
from pathlib import Path

base = json.loads(Path(sys.argv[1]).read_text())
sc = json.loads(Path(sys.argv[2]).read_text())
out_path = sys.argv[3]
cutoff = sys.argv[4]
P0 = base["reference_price_P0"]
q = base["price_quantiles"]; hl = base["ohlc_bootstrap_price_quantiles"]; pr = base["probabilities"]
S = sc["scenarios"]; names = list(S)
rec = dict(base)
rec["forecast_record_version"] = "1.0"
rec["information_cutoff_ist"] = cutoff
rec["market_status_at_forecast"] = "NSE cash market closed (13-Oct-2026 15:30 IST); no pre-open yet; target session 14-Oct-2026 09:15-15:30 IST (pre-open 09:00-09:08); closing price = closing-auction price since 3-Aug-2026"
rec["horizon"] = "one session: 2026-10-14 (Wed), open gap G, open-to-close I, close-to-close R, high/low vs P0"
rec["method"] = ("Pre-registered (docs/PREREGISTRATION.md, commit 711805d): filtered-historical-simulation quantiles = sigma_t x median-centred trailing-500 standardised residuals; "
                 "sigma from S6 (geometric blend of GARCH(1,1)-t and HAR on gap^2+Garman-Klass) for R and I, S4 (HAR-GK) for G, HAR for the range; location L0 (median = P0) because no location model passed its gate; "
                 "high/low from a joint OHLC bootstrap scaled by the S6 sigma (exploratory, evaluated walk-forward). Parameters refit on all sessions through 2026-10-13.")
rec["predictive_value_statement"] = {
    "scale/volatility": "Demonstrated against the pre-registered expanding-RMS benchmark (Final window DM p=0.0006) but NOT distinguishable from a one-parameter rescale of that benchmark in Final (p=0.44) and only weakly better than a trailing-250-day untimed benchmark (p=0.084); evidence of true day-to-day timing is moderate and strongest on the pooled Dev+Val sample.",
    "direction": "NOT found. Ridge/logit location models failed every pre-registered gate on Validation+Final (OOS R2 negative, accuracy below the best constant). There is insufficient evidence for a reliable directional forecast.",
    "gap_location": "A positive median gap (+0.3%) held 2019-2025 (post-hoc rule selected it) but disappeared after the closing-auction change of 2026-08-03; the gap median is set to zero by judgement.",
    "intraday_path": "Not modelled. Conditional descriptions use daily-OHLC frequencies and 36 validated post-CAS 15-minute sessions; first-hour direction did not predict the rest of the day (r=-0.11).",
}
def band(name):
    s = S[name]; lo, med, hi = s["close_range_p10_p50_p90"]
    return {"model_probability": round(s["model_probability"], 3), "close_p10_p50_p90": [lo, med, hi]}
rec["scenarios"] = {
    f"bearish (R <= -1.5%, close <= {P0 * 0.985:.1f})": {
        **band(names[0]), "probability_status": "model-based (calibrated only at the 90% interval level); event overlay is subjective",
        "trigger_or_assumption": "Risk-off spill-over (Asia/KOSPI chip rout, crude/US-yield shock), a disappointing SEBI settlement headline (blended VWAP or CAS retained), weak retail-broker read-through (Groww Q2), or profit-taking after the +10.8% bounce from the 1-Oct close.",
        "opening_behaviour": f"Flat-to-lower open; a gap below roughly -0.5% (< {P0 * 0.995:.0f}) would be consistent with this path.",
        "conditional_intraday": "If early (first-hour) volume is >1.5x normal and price loses the 13-Oct low (3,290) the next descriptive zone is the 3,159-3,216 volume node; most of the day's range is usually set by 10:15 (median 77%, 36 post-CAS sessions).",
        "supporting_evidence": "Beta~0.8-1.4 to a market that is -15% from its peak; 12 of the last 50 sessions moved >=3%; sell-the-news after Nifty-50 inclusion; valuation ~49x TTM; analysts split Rs2,820-4,850.",
        "invalidation": "Pre-open indicative price > P0+0.5% with peers (Angel One, MCX, CDSL) firm, or a SEBI circular adopting pure last-30-minute VWAP."},
    f"base (-1.5% < R < +1.5%, close {P0 * 0.985:.1f}-{P0 * 1.015:.1f})": {
        **band(names[1]), "probability_status": "model-based", "trigger_or_assumption": "No decisive SEBI/CAS news during the session; stock trades on market beta, sector tone and retail-activity data; WPI/Groww results are the only scheduled items.",
        "opening_behaviour": f"Open within about +/-0.5% of P0 (gap 50% interval {q['G']['q0.25']:.0f}-{q['G']['q0.75']:.0f}).",
        "conditional_intraday": "Range-bound; day range median ~2.9% of price (50% interval 2.2%-3.9%); high or low usually set in the first hour; late-session volume rises into 15:00-15:15 before the closing auction.",
        "supporting_evidence": "Model sigma 2.48% matches options-implied 2.43%/day; volume ratio on 13-Oct was low-to-normal; delivery share 41% vs 41% 60-day mean.",
        "invalidation": "A first-hour move beyond +/-1.5% on volume >2x normal, or a regulatory headline."},
    f"bullish (R >= +1.5%, close >= {P0 * 1.015:.1f})": {
        **band(names[2]), "probability_status": "model-based; event overlay is subjective",
        "trigger_or_assumption": "Clear pro-BSE regulatory outcome or credible report (pure 30-minute VWAP settlement, CAS delinked from expiry), strong Groww/Angel One read-through, or broad risk-on rotation into India after the Asian sell-off.",
        "opening_behaviour": f"Gap-up above roughly +0.5% (> {P0 * 1.005:.0f}).",
        "conditional_intraday": "Holding above the 13-Oct high zone (3,400-3,405) with rising volume makes a move toward 3,470-3,540 plausible; failure to hold it makes a round trip into base more likely (the 5-7 Oct rally lost ground the next sessions).",
        "supporting_evidence": f"Prior CAS headlines produced +3.1% to +4.4% days; options-implied vol 38.5% leaves room for 4-5% upside tails (model P(R>=+4%) = {100 * sc['tail_masses']['P(R>=+4%)']:.1f}%).",
        "invalidation": "Open at or below P0 with peers weak, or a SEBI text that keeps CAS for expiry settlement."},
}
rec["invalidation_conditions_whole_forecast"] = [
    "Session 2026-10-14 is not a normal full trading day (holiday notice, market-wide halt, or BSE Ltd-specific trading halt).",
    "Official NSE close of 2026-10-13 differs from the provisional 3,375.40 by more than 0.3% (prices are then re-based from the return quantiles; the return forecast itself is unchanged).",
    "SEBI issues its settlement/CAS circular or a regulator/exchange announces a fee, tax or expiry change before the open: the distribution then no longer applies (event overlay in results/scenarios.json is the only guide, and it is subjective).",
    f"A gap larger than 3 sigma_G (about +/-2.8%) at the open: the stock is in a different information state; condition on the observed open (close = open x exp(I), sigma_I = {100 * base['log_return_quantiles']['I']['sigma']:.2f}%).",
]
rec["event_overlay_subjective"] = sc["event_overlay_SUBJECTIVE"]
rec["known_limitations"] = [
    "No order-book, bid-ask, short-interest, securities-lending, FII/DII daily flow or GIFT-Nifty data were available.",
    "Intraday bars come from Yahoo through a summarising fetch and only descriptively; the gated models use daily exchange data.",
    "Closing price definition changed on 2026-08-03 (VWAP -> closing auction): only 49 sessions of the new regime exist.",
    "Prices are price returns (no dividend re-basing); the Rs10 dividend went ex on 2026-07-10, none is due on 2026-10-14.",
    "Scenario thresholds (+/-1.5%) and the event-hazard overlay are my choices; the probabilities are not calibrated for the three-way partition.",
]
rec["reassessment"] = "Scheduled by the user/analyst only: pre-open indicative price (09:08 IST), 10:15 IST, close. No automatic monitoring exists in this session."
Path(out_path).write_text(json.dumps(rec, indent=1))
print("written", out_path)
