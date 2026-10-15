# BSE Ltd (NSE: BSE) — integrated v2 report: inputs, behaviour, methodology audit, 14-Oct-2026 forecast and its scoring

Tags: **[V]** verified against a primary or reproduced source · **[C]** calculated by code in this repo · **[I]** interpretation · **[U]** unknown / not found.
Times IST. P0 = ₹3,375.40 (official NSE close, 13-Oct-2026). v1 cutoff 13-Oct 16:55 (record `results/forecast_record_2026-10-14.json`, commit e8a0f22, 21:11 IST on 13-Oct, **frozen**). v2 information cutoff 13-Oct 22:00 (record `results/forecast_record_2026-10-14_v2.json`, commit dfb99f1, **written 21:00 IST on 14-Oct, after the session** — see §8). Nothing here is investment advice.

---

## 0. Verdict

* **Evidence supports a volatility / range forecast only.** It does not support a directional forecast: *there is insufficient evidence for a reliable directional forecast.* No model, pattern, linkage or event rule in v1 or v2 passed the pre-fixed out-of-sample gate for predicting the sign or centre of the next close. The one validated input — the previous US session's S&P 500 move, which predicts the opening gap — moved the centre by **−0.053% (−₹1.8)**, i.e. 0.02 σ. [C][V]
* **v2 changed v1 by that one input** and nothing else. The scale model (σ_R = 2.478%), location (zero) and the subjective event overlay are unchanged. [C]
* **Scored after the session** (this is the first time the outcome was looked at; the v2 record was committed first): official 14-Oct **O 3,375.40 · H 3,408.30 · L 3,320.00 · C 3,338.00** (R = −1.114% = 0.45 σ; volume 3.00 M). The close, high, low and open all fell inside the 50% intervals of both records; it landed in the base scenario (−1.5% < R < +1.5%). One session says nothing about skill (§3.5). [V][C]
* **Input honesty.** The workbook the user supplied as "TradingView" is **Yahoo Finance API data**, per its own Notes sheet. **No TradingView chart, screenshot, indicator or export was inspected**; the Claude-in-Chrome tools were not available. A 30-session export cannot support a comprehensive back-test, and none is claimed.

---

## 1. Verified input and coverage summary

### 1.1 The supplied workbook (`data/raw/tradingview/BSE_intraday_30d_1.xlsx`; full audit in `docs/INPUT_AUDIT.md`, code `src/audit_xlsx.py`) [V][C]

| Item | Finding |
|---|---|
| Source | Yahoo Finance chart API (Notes sheet). Not TradingView. Identity (NSE:BSE, INR, EQ) established by data: 20/20 session closes equal official NSE closes to the paisa |
| Timeframes / range | 15 min (495 rows), 30 min (255), 1 h (135); 20 sessions 15-Sep → 13-Oct; time labels are bar **start**, IST |
| Latest candle | 13-Oct 15:15–15:30, complete (market closed; close = official close); static snapshot, not live |
| Session / adjustment / chart type | Regular session only; unadjusted (no corporate action in window); ordinary OHLC time bars (all prices on the ₹0.05 tick; bar opens continue from previous closes) |
| Indicators / volume type | None supplied. Volume = Yahoo feed shares, **87–100% (mean 95%) of NSE daily volume**, cause not established; 1 h volume sheet defective (zeros) |
| Integrity | sorted, 0 duplicates, 0 nulls, 0 OHLC-inconsistent bars; 30 min / 1 h reproduce exactly from 15 min (volumes aside); **5 sessions lack the 15:15 bar**; first-bar open ≠ NSE pre-open auction open (up to ₹11.7) |
| Match to exchange | Closes 20/20 identical; highs ≤ NSE high by up to ₹4.0, lows ≥ NSE low by up to ₹4.2 |

### 1.2 Data inventory and gaps

| Need | Held | Gap and effect |
|---|---|---|
| Long-term trend / regime | NSE daily OHLCV 2017-02 → 2026-10-13 (2,388 sessions), bonus-adjusted; Nifty/sector/VIX, peers, breadth, delivery, F&O (IV) | none material |
| Recent daily behaviour | same; official 13-Oct bhavcopy and index file | none |
| Intraday structure | 37 validated 15-min sessions (20 workbook + 17 earlier Yahoo fetch; 18-Aug → 13-Oct), all post-closing-auction | **low power** (≈ 37 sessions); no pre-open prices, no order book, no auction-price series → descriptive patterns only |
| Event reactions | 7–10 earnings, ≈ 45 pre-specified events | tiny samples; consensus is vendor-dependent |
| Overnight / cross-asset | FRED (stale 1–7 business days) + live Yahoo/ECB snapshots at 21:47 IST | **GIFT Nifty, Asian closes feed, FII/DII daily, short interest, securities lending: not obtainable** |
| Model training / evaluation | daily walk-forward, 1,887 forecasts | intraday models cannot be trained on 37 sessions; none is claimed |
| TradingView-specific (indicators, technical rating, annotations) | one summarised public page (internally inconsistent) | **not supplied, not used** |

---

## 2. Behavioural profile (definition · n · period · benchmark · exceptions · status)

Sources: `research/v2/03`–`06` and their JSON/code under `src/behaviour/`, with the lead's reconciliation and spot-checks. **Association is not causation; no intent or manipulation is inferred.** Status labels: `validated_out_of_sample` (fixed chronological protocol, family-adjusted, beat benchmark), `descriptive_only`, `not_found`, `untested`.

| # | Pattern | Result | n / period | Benchmark | Exceptions / limits | Status |
|---|---|---|---|---|---|---|
| 1 | Follows, does not lead, the market | same-day β to Nifty 50 = 0.89 (HAC CI 0.77–1.01), corr 0.35 | 2,388 · 2017-02→2026-10 | β = 1 | yearly β 0.28 (2019) → 1.82 (2025); rolling-250 = 1.38 now, last 120 = 0.75; a real break ≈ 2021-03 (β 0.64 → 1.27; verifier sup-Wald p < 0.01) | descriptive; **β as scenario mapping validated** (given the same-day Nifty move, OOS R² 12.6%, positive every year) — it does not forecast the index |
| 2 | Mostly idiosyncratic | idiosyncratic variance share 87.5% (CI 83–91); 80.7% since 2025; 75.9% last 250 | same | — | — | descriptive |
| 3 | Sector co-movement | β to Nifty Capital Markets 1.47, corr 0.81 | 513 · 2024-09→ | β = 1 | BSE is a constituent: ≈ 34–51% (data-implied ≈ 44%) of the covariance is mechanical; ex-BSE corr 0.56–0.67 | descriptive |
| 4 | Lead/lag | no index or India-VIX lag survives Holm; CDSL ±1 (r 0.09–0.10) and Angel One −1 (0.12) do | 130 cells | chance (16 raw hits vs 6.5 expected) | independent check: after controlling for each peer's own lag, BSE adds only +0.05% OOS R² to CDSL (p 0.09); persistence explains about half of the cross-lag → **"BSE leads peers" not established** | descriptive; leadership `not_found` |
| 5 | Overnight global cue → gap | previous US session S&P 500 → BSE gap G: slope 0.276 pp/1% (CI 0.215–0.337); walk-forward OOS R² +7.85%, fixed split +6.79% | 2,313 · 2017→2026 | expanding mean | **slope unstable**: 0.03 (2019) → 0.68 (2026), break ≈ 2020-03 (p < 0.01); misaligned-window placebo fails (only the stated alignment works); passes the frozen v1 Val+Final gate; effect on close R: +1.7% OOS R² | **validated_out_of_sample** (independently reproduced); economically small for 14-Oct (−0.05 pp) |
| 6 | Sensitivity to declines / VIX | down-market β 1.00 vs up 0.76 (Holm p 0.61); β by VIX tercile 1.07/1.04/0.85 (p 0.30); stress-correlation rise 0.49 vs 0.22 is a variance artefact (Forbes–Rigobon 0.24) | 2,388 | symmetric β | — | `not_found` |
| 7 | Rates / FX / commodities | US 10y, Brent: no association (Holm 1.0); USD/INR → gap +0.91% OOS but not incremental to the S&P (pooled Holm 0.10) | 2,300+ | mean | FRED lags; Brent series is Dated spot, a different instrument from futures | `not_found` (INR: descriptive) |
| 8 | Momentum vs mean reversion | lag-1 autocorrelation +0.105; VR(5) 1.21; yesterday's return walk-forward OOS R² +0.95% | 2,388 | expanding mean | **fails the pre-fixed gate**: Validation −0.71%, Final −0.68% (pooled −0.70%, CW p 0.30); carried by 2019–2023; the "VWAP-close" mechanism explains ≤ 12% (refuted as the main cause); implied shift +0.13 pp = 0.05 σ | `descriptive_only`; **not applied** |
| 9 | Gap continuation vs reversal (gap-up ≥ 0.5 σ) | share with same-sign intraday move: 33% (n 234) before 2024-07, **70%** (n 37) 2024-07→2026-08-02, 50% (n 4) in the auction era | 275 | 50% | the flip is real as a period difference (Fisher p 6e-5, whole-registry Holm 0.015) but not a stable rule; 4 auction-era cases; lead recomputation agrees (32.6/69.4 by the agent, 33.3/70.3 by the lead) | `descriptive_only` |
| 10 | Gap behaviour since the closing auction (3-Aug-2026) | open == previous close on 8 of 50 sessions (125 of 2,388 overall); positive-gap share −20 pp vs the prior 250 sessions (post-hoc; Holm-12 0.49) | 50 | prior 250 | already 0 vs Nifty in July 2026 so the cause date is not identified | `not_found` after correction |
| 11 | Volume / liquidity vs breakouts | close beyond prior-20-day high/low with or without volume or delivery confirmation: no effect; volume–|return| Spearman 0.42, same across liquidity states | 158 up / 165 down breakouts | all days | cells degenerate for all-day terciles (amended before looking at returns) | `not_found` (breakouts); volume–|R| descriptive |
| 12 | Event reactions (earnings, regulatory, market structure) | event sessions larger: mean |z₀| 1.78 (CI 1.39–2.18) vs 0.75; volume 1.8× (earnings 2.5×) | 27 gated non-earnings, 7–10 earnings; 2024→2026 | ordinary days (n 1,702) | selection-light subset (scheduled n 9, earnings n 7) ≈ 1.3 and fails Holm; **sign rule hit 14/20 but 12/14 vs 2/6 depending on how well the release time is documented → do not use for direction**; PAT grew 7/7 and EPS beat 5/5, yet next-session R > 0 only 3/7; no asymmetry positive vs negative; formal documents vs reports indistinguishable (|z| 2.23 vs 2.06) | magnitude `descriptive_only`; direction `not_found` |
| 13 | Regimes (calm / trending / stressed / event) | 13-Oct is "stressed" via the Nifty-drawdown prong only (−13.7% from the 250-day high; VIX 14.12; BSE vol percentile 0.56) | 2,388 | v1 calibration | S6 90% interval needs κ ≈ 1.04 (at most +4–5%); 50% body narrow (κ₅₀ 1.10 overall, 1.26 stressed; family Holm 0.041, whole-registry 0.34) | σ unchanged; widening reported as sensitivity |
| 14 | Opening / midday / closing | volume U-shaped: first hour 26.5% (CI 23–30) vs 16% uniform; first hour carries 46.7% of realised variance; closing-auction bar |move| 0.131% (6/29 exactly 0) | 37 sessions | uniform | v1's "86% of highs/lows in the first hour" = a random walk with this variance profile (83.8% observed, 84.9% simulated; lead recomputed 31/37) — **not a distinct pattern**; v1's 0.20% auction move mixed two bars | `descriptive_only`; first-hour direction vs rest of day r = −0.06 (`not_found`, power 44%) |
| 15 | Prior-day levels | previous-day high touched 71% vs 73% random-walk; lows: persistence of breaks | 2,368 | volatility-scaled random walk | the "persistence at lows" label comes from a specialist and is **pending independent verification** | highs `not_found`; lows flagged, unverified |
| 16 | Structural change (ownership, leverage, market structure) | 0 of 54 pre-specified break cells survive Holm/BH; largest: turnover ×5.6 at 2024-10-01 (Holm 0.12); no debt; FPI 16.3% → 21.3%; Nifty 50 membership since 30-Sep | 54 tests | placebo dates | block permutation alone has 39% size under persistent vol (self-test); relationships estimated before 3-Aug-2026 may not hold | `not_found`; association only |

---

## 3. Methodology and actual validation results

### 3.1 Pipeline (pre-registered; `docs/PREREGISTRATION.md`, commit 711805d, before any BSE return statistic; deviations #1–#26 in `docs/DEVIATIONS.md`)

Data (NSE bhavcopy, bonus factors verified) → company/market context → behavioural hypotheses → measurable signals → filtered-historical-simulation quantiles: σₜ (S6 = geometric blend of GARCH(1,1)-t and HAR on gap²+Garman–Klass for close and intraday; S4 for the gap; HAR for the range) × median-centred trailing-500 standardised residuals → expanding walk-forward (refit every 20 sessions; Dev 2019-02→2024-06, Validation 2024-07→2025-06, **Final 2025-07→2026-10, n = 317**) → pinball/coverage/Kupiec/Christoffersen/DM tests against simple benchmarks.

### 3.2 Results [C] (v1, frozen; details `FORECAST_REPORT.md` §8)

| Question | Result |
|---|---|
| Scale vs benchmark | S6 beats the expanding-RMS S0 in Final (DM p 0.0006, Holm 0.004); 90% coverage 91.8% (Kupiec p 0.27). **Caveats:** S6/S4/S1 are a statistical tie; S0 rescaled by one ex-post constant matches S6 in Final (p 0.44); vs a trailing-250-day benchmark the Final gain is weak (p 0.084); Validation alone shows no significant gain; Kupiec power in Final ≈ 22% |
| Direction / location | ridge and logit, Val+Final: OOS R² −2.2%, Clark–West p 0.41, accuracy 51.2/51.9% vs 52.9% constant → **not found**. A post-hoc positive gap median (+0.3%) is overridden because the closing-auction regime (since 3-Aug) removed it |
| Gap, intraday, range | beat S0/EMP250 in Final (p 0.006 / 0.0001 / 0.03), 90% coverage ≈ 91%; the gap interval is the least reliable (under-covered in Dev 86.5%, Val 83.9%) |
| High / low (OHLC bootstrap) | Final 90% coverage 90.2% / 88.6% |
| v2 additions | S&P → gap/close validated and reproduced (§2 row 5); everything else in §2 reported, none applied |

### 3.3 Leakage and reproducibility [C]

Expanding windows only; same-row perturbation tests on real data (47 series × 4 rows, max |A−B| = 0) with an injected-leak positive control (the original truncation/shuffle tests were found too weak by the independent audit and replaced); verifiers re-implemented the S&P-alignment test with a deliberately mis-aligned placebo (fails) and found no look-ahead. Code commits, data hashes and `requirements.txt` are stored in the records; fixed seeds.

### 3.4 Adoption rule used to build v2 (fixed before building the record, `src/finalize_v2.py`)

An input changes the distribution only if (i) a workstream labels it `validated_out_of_sample`, (ii) an independent verifier reproduced it from raw data, and (iii) it also passes the frozen v1 Validation+Final gate or is not a regime artefact. **Passes:** previous-US-session S&P 500 → gap and close. **Fails:** BSE's own lagged return (Val+Final −0.70%), peer lags, regime-conditional scale (whole-registry Holm 0.34), unquantifiable event news.

### 3.5 Scoring the single realised session [C]

| Target | Realised | v1 pinball ×10⁴ | v2 pinball ×10⁴ | Inside 50 / 80 / 90 / 95% |
|---|---|---|---|---|
| Close R | −1.114% (C 3,338.0) | 28.64 | **28.34** | yes / yes / yes / yes (both) |
| Gap G | 0.000% (open 3,375.40) | **5.49** | 5.76 | yes (both) |
| Open→close I | −1.114% | 26.50 | 26.50 | yes |
| Range ρ | 2.62% (model median 2.86%) | 12.79 | 12.79 | yes (90%) |
| High / low | 3,408.3 / 3,320.0 (bootstrap medians 3,421.8 / 3,334.7) | 16.23 / 18.18 | 15.93 / 17.88 | yes (50%) |

v2 vs v1 differ by ≈ 0.3 in pinball ×10⁴ on one draw — noise. Brier score of P(close > P0) = 0.5 is 0.25 by construction. **n = 1 cannot demonstrate or refute skill**; the interval-coverage claims rest on the 1,887-forecast walk-forward, not on this day. The cause of the −1.1% was not investigated (one web search found no coverage of 14-Oct) — no story is offered.

---

## 4. Next-session estimates (v2 record, cutoff 13-Oct 22:00) [C]

Model-based, conditional on the information set; centre = P0 shifted by the S&P input.

| Quantity | 2.5% | 5% | 10% | 25% | **50%** | 75% | 90% | 95% | 97.5% |
|---|---|---|---|---|---|---|---|---|---|
| Opening price (gap) | 3,313.7 | 3,332.2 | 3,346.3 | 3,366.6 | **3,373.8** | 3,385.1 | 3,396.8 | 3,411.9 | 3,435.2 |
| Close | 3,227.1 | 3,245.1 | 3,265.7 | 3,320.6 | **3,373.6** | 3,427.0 | 3,473.5 | 3,506.1 | 3,534.6 |
| Day high (bootstrap) | 3,354.4 | 3,366.4 | 3,377.1 | 3,395.5 | **3,421.8** | 3,459.7 | 3,502.7 | 3,541.9 | 3,561.3 |
| Day low (bootstrap) | 3,180.0 | 3,211.3 | 3,247.4 | 3,295.8 | **3,334.7** | 3,364.2 | 3,386.2 | 3,396.1 | 3,413.2 |

* **Close vs range:** the 90% close interval (3,245–3,506) is narrower than the typical high–low range because the close is one point inside it. Range (high/low − 1) quantiles 5/25/50/75/95% = 1.62 / 2.21 / 2.86 / 3.85 / 5.83%. σ_R = 2.478%; options cross-check ATM IV 38.5% ≈ 2.43%/day. **90% close-interval width ≈ 7.8%.**
* **Probabilities** (500 residual draws, ± ~1–2 pp resolution; centre/tail masses not separately validated): P(close > P0) = 48.6% (shift only, not a directional claim); P(|R| < 1%) 34%; P(R > +2%) 18%; P(R < −2%) 21%; P(R > +4%) 4.4%; P(R < −4%) 4.8%.
* **Precision.** Prices are quoted to ₹0.1 but are meaningful to roughly ±₹2: the ₹1.8 shift is below the grid noise. Do not read the median as a call.

---

## 5. Conditional trajectories (scenarios, not forecasts of the path)

Partition of the model close distribution at ±1.5% (my choice; not separately calibrated). The **intraday path is not forecast**; closing price is the auction price (15:15–15:35).

| Scenario | Model prob. | Close p10 / p50 / p90 | Conditions that would favour it (observable) |
|---|---|---|---|
| Bearish: R ≤ −1.5% (≤ 3,324.8) | 27.2% | 3,229.8 / 3,278.1 / 3,320.3 | SEBI keeps CAS for expiry settlement or blends it (large down-event, arithmetic: giving back half the 5–7 Oct rally ≈ 3,201); pre-open price below ~3,334 with peers weak; S&P/Asia sell-off; Groww Q2 (14-Oct, in-session) shows weak retail-derivatives activity |
| Base: −1.5% < R < +1.5% | 47.6% | 3,335.6 / 3,374.3 / 3,412.4 | no circular; ordinary market; open near 3,375 (the v1/v2 centre; zero-gap sessions are common since 3-Aug) |
| Bullish: R ≥ +1.5% (≥ 3,426.0) | 25.2% | 3,433.4 / 3,464.2 / 3,534.5 | SEBI circular adopting last-30-minute VWAP for derivative settlement (but ≈ +10.8% since 1-Oct is already priced; five October-style reaction days were +4.4/+3.9/+1.5%, diminishing); pre-open > +0.5% with peers firm |

**Realised:** base scenario (R = −1.11%, close in the lower half of the base band).

---

## 6. Strongest supporting and opposing evidence

**For a range-only, unchanged-centre forecast:** (1) every directional model failed the pre-fixed gate on unseen data; (2) the lone validated cue shifts the centre by 0.02 σ; (3) σ models beat naive benchmarks on Final with ≈ 91% coverage; (4) 87.5% of variance is idiosyncratic and unpredictable by indices; (5) the news channel is mostly stale/syndicated (one Reuters story counted once, not ten); (6) the realised session landed inside every 50% interval.

**Against (what could make the forecast wrong):** (1) the decisive binary event — SEBI's settlement/CAS circular ("about a week" from 10-Oct) — is unscored in the model (subjective overlay only, p_event 0–15%) and could land any day; (2) the closing-auction regime has only ~50 sessions so volatility timing and gap relationships may have changed; (3) the 13-Oct 14:15 volume spike (8.9× its slot median, rank 3 of 495 bars) has **no identified cause** [U]; (4) the S&P slope is unstable (0.03 → 0.68) and the 13-Oct US session was only 2h47m old at the cutoff; (5) 50% intervals ran narrow in Final (0.464); (6) Kupiec tests have low power at n = 317; (7) GIFT Nifty and flow data were unavailable.

---

## 7. Developments that would invalidate or update the forecast (scheduled reassessment only — no automatic monitoring exists)

Anything dated before the open: (a) **SEBI circular** adopting pure last-30-min VWAP (shift weight to base/bull, widen σ; bear case dies per v1 rule) or retaining/blending CAS (bull case dies, bear weight up; analogue magnitudes −4.6% to −7.6%, selected after the fact and biased large); (b) any tax/fee/expiry/margin action on exchanges (tail: P(R ≤ −4%) above 4.4%); (c) pre-open indicative price (09:08) outside the 5–95% gap band 3,332–3,412 → condition on the open (close ≈ open × exp(I), σ_I 2.2%); (d) overnight S&P / Asia move x: gap shifts 0.28 pp per 1% (bounded to ≈ 0.6 pp per 1% by the 2026 slope); (e) GIFT Nifty (not observed); (f) holiday/halt notice (whole forecast void); (g) BSE Ltd or peer filings (Groww Q2 on 14-Oct, call 16:00; Angel One 15-Oct; BSE Q2 board **4-Nov**, filed 13-Oct 16:02); (h) a wire story that dates the 14:15 spike. **Does not warrant an update:** KOSPI/Nikkei (already in P0), mixed US bank results, delivery 36.07%, the rally itself (two post-rally clusters went −3.1% and +0.6%).

---

## 8. Timestamped forecast records

| Record | File | Commit (time) | Cutoff | Status |
|---|---|---|---|---|
| v1 | `results/forecast_record_2026-10-14.json` | e8a0f22 (13-Oct 21:11 IST) | 13-Oct 16:55 | **Pre-session, immutable, the forecast of record** |
| v2 | `results/forecast_record_2026-10-14_v2.json` | dfb99f1 (14-Oct 21:00 IST) | 13-Oct 22:00 | **Late, rule-restricted update.** Information set restricted by rule, not by clock; the lead looked at no 14-Oct data before committing it (DEVIATIONS #25). Not an independently timestamped pre-session forecast |
| Scores | `results/forecast_score_2026-10-14[_v2].json` | after the record commits | — | produced by `src/score_forecast.py` from the official UDiFF bhavcopy |

Charts: `results/forecast_chart_v2_forecast_only.png` (as of the record) and `results/forecast_chart_v2.png` (realised candle overlaid after scoring, in black). History is drawn as solid candles; the forecast is a shaded, conditional distribution with 50/80/90/95% bands and median high/low markers — **no future path is drawn**.

---

## 9. Coverage audit (link by link)

| Requirement | Evidence available | Checks performed | Remaining gap | Effect on forecast |
|---|---|---|---|---|
| Company research | FY26 annual report, Q1 FY27 filing/XBRL, SHP XBRL, NSE feeds, dossiers 01/02 | **24 claims re-checked against primary sources: 17 verified, 5 qualified, 2 contradicted** (e.g. Q2 board = 4-Nov, not "~6-Nov"; ₹40 cr provision booked in Q4, not reversed); independent verifier: severity minor | NSE bulk-deal record not retrievable; Reuters original not read | none for next session (descriptive knowledge) |
| Earnings | 8 quarters reported + vendor consensus (Investing.com / TradersUnion / PL) | surprises tabulated; TradingView 21.40 reconciled to vendor share count (company EPS 21.22); beat quality (non-operating income ₹140.7 cr vs ₹78.5 cr average) | consensus vendor-dependent; n = 7–8 | none (next result is 4-Nov) |
| Governance | filings, AGM votes, SEBI orders, PIT/SAST feeds | lists compiled; GST order ₹7.25 cr found | — | none |
| Technical structure | 2,388 daily bars, 37 intraday sessions | adjusted-close features; breakouts, gaps, levels tested with family correction | intraday low power; no order book | none (nothing validated) |
| Sentiment | news, analyst actions, management tone | four channels separated; one Reuters story = one signal; 10+ syndications collapsed | social feeds blocked (Reddit 403, StockTwits, Trends 429); no sentiment model (Bigdata connector failed) | none |
| Macro | FRED, ECB, live snapshots | alignment placebo; 10y/Brent null; USD/INR not incremental | FRED stale; GIFT Nifty absent | −0.05 pp gap shift |
| Regimes | 4-class ex-ante classification, breaks | calibration per regime; 54 break tests; independent β-break test | 50 auction-era sessions | σ unchanged; sensitivity table in record |
| Catalysts | SEBI listings/RSS, NSE filings, calendars | negatives checked against primary listings; **news-feed lag found and corrected** (DEVIATIONS #26) | unscheduled SEBI timing; wires behind paywalls | subjective overlay only |
| Data integrity | NSE bhavcopy, workbook audit | bonus re-basing (PREV_CLOSE bug), weekend sessions, short sessions, 3 vendors for the 13-Oct close, workbook/NSE matches | volume shortfall cause unknown | none |
| Leakage prevention | — | same-row perturbation with positive control; mis-aligned placebo; cutoff rules enforced on every workstream; two agent runs interrupted and restarted without exposure (DEVIATIONS #24) | v2 committed after the open (#25) | v2 labelled non-ex-ante |
| Benchmark comparison | S0, EMP250/500, S0×c | all scale gains reported with ties and caveats | Validation-alone gain not significant | range claim modest |
| Calibration | coverage, Kupiec, Christoffersen, PIT | done at 50/80/90/95 | 50% bands narrow; low Kupiec power | stated in report |
| Reproducibility | code, seeds, hashes, commits, `requirements.txt` | records name the commit; tree clean at generation | external APIs change | — |
| TradingView inputs | one workbook (Yahoo data) | full integrity audit | **no TradingView chart, indicator or screenshot seen** | none |

### Audit questions

1. **Facts available at the cutoff?** Yes for v1 (16:55) and for v2 by rule (22:00) — every workstream asserted no data after the cutoff and the 14-Oct session was unseen until after the v2 commit; v2 is nonetheless late by the clock. The news workstream's claim "BSE made 0 filings on 13-Oct" was wrong (feed lag) — corrected from the primary PDF.
2. **Descriptive knowledge mistaken for predictive evidence?** Avoided: valuation (49.1× TTM, 8th percentile of own history), earnings quality and governance are labelled descriptive and not applied.
3. **Correlated signals counted twice?** Counted once: one Reuters story (not ten); S&P, US VIX and USD/INR as one global risk signal; BSE own-lag/peers' lags/residual as one persistence signal; MA/RSI/ATR not independent. Agreement among agents was not treated as confirmation.
4. **Beats simple benchmarks on unseen data?** Scale: yes against S0 but only weakly against a rescaled/trailing benchmark. Direction: no.
5. **Probabilities and ranges calculated?** Yes — every number comes from stored code/results; the ±1.5% partition and event overlay are my choices and labelled.
6. **Could a regime change invalidate relationships?** Yes: closing-auction regime (3-Aug), β break (2021), S&P-slope drift, SEBI settlement decision. Treated as the main uncertainty.
7. **Is the precision justified?** Only to about ₹2 on the centre and ±1–2 pp on probabilities; intervals are the product.
8. **What would reverse the conclusion?** A directional rule passing a chronological gate on the closing-auction era; a stable slope on a GIFT-Nifty/overnight feed; or the SEBI circular.

### Unresolved limitations (not fixed)
No TradingView chart/indicator/screenshot; no order book, short-interest, flow or GIFT-Nifty data; only ~50 auction-era sessions and ~37 intraday sessions; SEBI settlement decision unquantifiable; v2 written after the open; cause of the 13-Oct 14:15 volume spike and of the 14-Oct −1.1% not established.

---

## 10. Verification status of the multi-agent work (lead reconciliation)

| Workstream | Output | Independent verifier | Result |
|---|---|---|---|
| linkages | `research/v2/03`, `src/behaviour/linkages.py` | done (`verify_linkages.md`) | S&P→gap/close, β, lead-lag, Capital Markets overlap **confirmed**; own-lag/peer "validated" labels **downgraded**; VWAP-mechanism sentence **refuted** |
| fundamentals | `research/v2/01` | done (`verify_fundamentals.md`) | numbers match primary sources; severity minor; "predates the Reuters report" is an inference (Reuters original unread); news-workstream contradiction resolved in its favour |
| news | `research/v2/02` | VERIFIER_NEWS | VERIFIER_NEWS_RESULT |
| patterns | `research/v2/04` | VERIFIER_PATTERNS | VERIFIER_PATTERNS_RESULT |
| intraday | `research/v2/05` | VERIFIER_INTRADAY | VERIFIER_INTRADAY_RESULT |
| events | `research/v2/06` | VERIFIER_EVENTS | VERIFIER_EVENTS_RESULT |

Lead spot-checks on unverified items: gap-up continuation flip (agrees: 33.3% vs 70.3%); first-hour high/low share 31/37 = 83.8% (agrees). Agents' independent re-computations inside their own reports are not independent confirmation. Specialist and verifier raw outputs are committed unedited; this report and the records are the lead analyst's.
