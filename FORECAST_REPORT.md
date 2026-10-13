# BSE Ltd (NSE: BSE) — next-session forecast for Wed 14 Oct 2026

Prepared Tue 13 Oct 2026, information cutoff **16:55 IST** (11:25 UTC). Evidence tags: **[V]** verified from a cited source · **[C]** calculated by code in this repo · **[I]** my interpretation · **[U]** unknown / unverified.
Everything numeric below is reproducible from `src/` and `results/`; the machine-readable record is `results/forecast_record_2026-10-14.json`.

---

## 0. Forecast summary

| Quantity (target session 14-Oct-2026) | Estimate | Status |
|---|---|---|
| Reference price P0 (official NSE close, 13-Oct) | **₹3,375.40** | **[V]** NSE CM bhavcopy; equals Google Finance, stockanalysis, Yahoo |
| Opening gap (median / 50% / 90% interval) | ≈ unchanged: ₹3,375 / ₹3,368–3,387 / ₹3,334–3,414 (−1.2% … +1.1%) | **[C]** model S4, tested, gap intervals least reliable |
| Central closing estimate (median) | **₹3,375 (unchanged)** | **[C]** no location model passed its gate |
| Close, 50% interval | ₹3,322 – ₹3,429 | **[C]** |
| Close, 80% interval | ₹3,267 – ₹3,475 | **[C]** |
| Close, 90% interval | **₹3,247 – ₹3,508** (−3.8% … +3.9%) | **[C]** coverage tested, see §8 |
| Close, 95% interval | ₹3,229 – ₹3,536 | **[C]** |
| Day range (high − low) median / 90% interval | 2.9% of price (≈ ₹97) / 1.6% – 5.8% | **[C]** |
| Likely high / low (median; 90% band) | high ₹3,424 (₹3,368–3,544) · low ₹3,336 (₹3,213–3,398) | **[C]** exploratory bootstrap, walk-forward tested |
| P(close > P0) | **50%** by construction — *not* a directional claim | **[C]** unconditional up-share: 47.8% since 2017, 53.1% last 565 sessions, 48.3% last 60 |
| "Broadly unchanged" = \|R\| < 0.62% (¼ σ) | 24% | **[C]** |
| P(\|R\| ≥ 2%) / P(\|R\| ≥ 4%) | 41% / 8.8% | **[C]**; recent frequencies 41.5% / 4.6–7.2% |

**Honest verdict.** *There is insufficient evidence for a reliable directional forecast.* The tests I ran found no model that predicts the sign or the centre of tomorrow's return better than "unchanged". What the evidence does support is a **risk range**: volatility-adaptive scale models produced better-calibrated, sharper intervals than the pre-registered untimed benchmark on unseen 2025-26 data, and an independent options-implied estimate (2.43%/day) agrees with the model's 2.48%/day. The central price is therefore the unchanged price and all the information is in the width.

**What could overwhelm this forecast.** SEBI's chairman said on 10 Oct that final closing-auction (CAS) / expiry-settlement guidelines would come "in about a week". That decision is the single largest stock-specific catalyst, its timing is unknown, and a good outcome is partly priced already (+10.8% from the 1-Oct close). I put **subjective** 5–15% on a decisive headline affecting this particular session; with 10% the 95% interval widens to ≈ ₹3,150 – ₹3,600 (§9C). That weight is a judgement, not an estimate.

---

## 1. Forecast boundary

| Item | Value | Source |
|---|---|---|
| Company / ticker / venue | BSE Ltd, NSE symbol `BSE`, series EQ, ISIN INE118H01025. Listed on **NSE only** (an exchange cannot list on itself; NSE's own shares list on BSE, the exchange) | **[V]** NSE bhavcopy; BSE bhavcopy has no BSE Ltd row; dossier 01 |
| Currency / timezone | INR / Asia/Kolkata (UTC+5:30) | **[V]** |
| Forecast timestamp / cutoff | Tue 2026-10-13 16:55 IST | — |
| Market status at forecast | Cash market **closed** (closed 15:30 IST). Pre-open for 14-Oct is 09:00–09:08, continuous 09:15–15:15 then closing auction (CAS) | **[V]** dossier 02 |
| Target session | **Wed 2026-10-14**, normal full day — absent from every 2026 NSE/BSE holiday list; next holiday Tue 20 Oct (Dussehra). NSE's own circular text was not retrievable | **[V]** (multi-source), **[U]** primary circular |
| Latest verified price | **₹3,375.40**, official NSE close of 13-Oct (open 3,332.00, high 3,403.20, low 3,290.20, prev close 3,330.20, volume 4,119,552, 185,203 trades, turnover ₹1,377 cr). File `BhavCopy_NSE_CM_0_0_0_20261013_F_0000.csv.zip`, published ≈16:34 IST — **end-of-day, not a live feed** | **[V]** NSE archive |
| Cross-checks of that price | Google Finance 15:30 IST "+45.20 → 3,375.40"; stockanalysis (15:28 IST, status closed); Yahoo `regularMarketPrice` 3,375.4 | **[V]** three vendors agree |
| Reference price for forecasting | **P0 = ₹3,375.40.** The market is closed so no live price exists; the closing price of the target session is unknown | — |
| Closing-price definition | Since 3-Aug-2026 the NSE close for these stocks is the **closing-auction price** (bhavcopy `LAST == CLOSE` on 49/49 sessions since; before, close = 30-minute VWAP) | **[C]**, dossier 02 |
| Targets | G = ln(Open/P0), I = ln(Close/Open), R = G + I, H′ = ln(High/P0), L′ = ln(Low/P0), ρ = ln(High/Low) | pre-registered |
| Information rule | Only data published ≤ cutoff. **Scheduled** items (not assumed): SEBI circular (any time), India WPI (≈12:00 IST, soft), Groww Q2 results (soft), US CPI 18:00 IST (after the close), Sensex weekly expiry Thu 15-Oct, Angel One Q2 results 15-Oct | **[V]/[U]** dossier 02 |

---

## 2. Data inventory and quality

| Dataset | Source | Coverage · frequency · latest | Limitations |
|---|---|---|---|
| Daily OHLCV, turnover, trades, prev close (BSE + all EQ stocks) | NSE archives: legacy `cm…bhav.csv.zip` (Feb-2017→Sep-2019), `sec_bhavdata_full` (Oct-2019→12-Oct-2026), UDiFF CM (13-Oct-2026) | 2,388 sessions 2017-02-06 → 2026-10-13 · daily | NSE `PREV_CLOSE` is **not** re-based on bonus ex-dates (found in QA); I apply verified 2:1 bonuses ex 2022-03-21 and 2025-05-23 myself. Price returns only (no dividend re-basing). 12 special short sessions dropped (volume rule), 4 weekend sessions kept |
| Delivery % | `sec_bhavdata_full` | Oct-2019 → 12-Oct-2026 · daily | Not published yet for 13-Oct; not used by gated models |
| Indices, India VIX | NSE `ind_close_all` | 2017 → **12-Oct-2026** · daily | 13-Oct file published ≈23:20 IST (after cutoff). Capital Markets index only from Sep-2024 |
| Peers (CDSL, MCX, Angel One, Nuvama, CAMS, KFin …) | same bhavcopy | → 13-Oct | Raw prev close (corporate actions not cleaned) |
| Options / futures (BSE stock F&O) | NSE F&O UDiFF bhavcopy, BSE rows | 469 sessions Nov-2024 → **12-Oct-2026** · daily EOD | Settlement prices, OI and volume by strike only; no bid-ask, no Greeks, no intraday. 13-Oct file due 18:48 IST (after cutoff) |
| Intraday 15-minute bars | Yahoo chart API via a summarising fetch tool | 36 validated sessions 18-Aug → 12-Oct-2026 (+13-Oct unvalidated) | Third-party; first-bar open ≠ NSE open (pre-open auction), highs miss some ticks, volume 83–99% of NSE's. The fetch layer sometimes garbled rows — row- and session-level validation added. **Descriptive only; never enters a gated model** |
| Financials, filings, calls | FY26 annual report (NSE archive), Kotak Neo result tables, broker PDFs, press — dossier 01 | Q4-FY25 → Q1-FY27 | Some figures single-source; no call transcript |
| News, regulation, macro, calendar | dossier 02 (SEBI listing pages, Reuters via Outlook Money/Kotak Neo, PTI/IANS, Business Standard…) | Jul–13-Oct-2026 | NSE/BSE circular pages blocked; 13-Oct Nifty/VIX/FX from one Yahoo feed |
| Analyst views | dossier 01 (Business Today, stockanalysis, Trendlyne) | Aug–Sep 2026 | Dates of some notes unverified |
| Social-media sentiment, order book, short interest, securities lending, FII/DII daily flows, GIFT Nifty, US futures | **Not available** | — | No conclusion in this report depends on them |

Data QA performed **[C]**: 49/49 recent sessions match stockanalysis exactly on open/high/low/close/volume; 52-week high ₹4,446.8 (27-May-2026) and both quoted lows reproduce; a research agent's 64-row close series and 12 dated analogue moves match the NSE data to ±0.02 pp. Older history rests on the NSE archive alone (bit-for-bit rebuilt by the auditor).

---

## 3. What this company is and what moves it

**Business [V]** — Asia's oldest exchange (1875). FY26 consolidated revenue from operations ₹4,834 cr: transaction charges 78.5%, listing services 10.7%, treasury income on clearing funds 3.5%, other (co-location, data, index services, software) 7.2%. In Q1 FY27 transaction charges were 84.8% of operating revenue, i.e. **earnings are an options-volume story**. Derivative activity centres on weekly Sensex options (Thursday expiry). Owns 15% of CDSL (≈2.9% of BSE's market cap), India INX/ICC, BSE Index Services, StAR MF. No promoter; FPIs 21.3%, DIIs 24.2% (LIC 5.57%), public 54.4% (Jun-2026). No debt; FY26 PAT ₹2,487 cr; core SGF ₹1,233 cr (ring-fenced). Sources: FY26 annual report (`archives.nseindia.com/annual_reports/AR_29957_BSE_2025_2026…pdf`), dossier 01.

**Financial condition [V]** — Q1 FY27 (announced 4-Aug after market): revenue from ops ₹1,566 cr (+63.5% y/y but only +0.2% q/q), PAT ₹873 cr (+62% y/y, +9.7% q/q), EPS ₹21.22. Trailing EPS ₹68.74 → **≈49× trailing, ≈42× forward**, 20.6× book; 24% below its 27-May high (₹4,446.8), 61% above its 31-Oct-2025 low (₹2,326.1). Consensus target ₹3,704 (19 analysts), but ratings are split: Buy/Outperform (PL ₹4,850, Macquarie ₹4,000, JPM ₹3,950, HDFC Sec ₹3,850) · Hold (MOSL, ICICI Sec, Nuvama ₹3,240, UBS) · Underperform (Jefferies ₹2,940, Bernstein ₹2,820).

**Why the stock is where it is [V/I]** — it trades on **regulation and volume trend, not on the Q1 print** (stock −6.7% since results). Headwinds already in estimates: STT hike (futures 0.02→0.05%, options 0.10→0.15%, effective 1-Apr-2026; stock −7.8% close on Budget Sunday 1-Feb); RBI curbs on bank funding of proprietary trading (effective 1-Jul; Jefferies: 10–12% of options turnover); and SEBI's **closing auction session** since 3-Aug, which cut index-option premium turnover (BSE ADTV ₹29,615 cr in Q1 → ₹18,100 cr in Aug, Nuvama). Q2-FY27 transaction income therefore looks more likely to fall than rise q/q **[I]**. Offsets: BSE joined the **Nifty 50** (30-Sep; passive buying done, stock "sold the news": −3.4%, −1.5%), cash-market share rising (≈8.8% in Sep), NSE has now listed (24-Sep, ₹1,800, trading below issue).

**Management and governance [V]** — MD & CEO Sundararaman Ramamurthy (since Jan-2023), Chairman Prof. Subhasis Chaudhuri; no leadership change found in 2026. Auditor S.R. Batliboi; KKC & Associates approved by the board 4-Aug-2026 (shareholder step pending). Small SEBI penalties (₹25 lakh Jun-2025; one SAT appeal), no 2026 order, no related-party issue found. Goldman Sachs and BNP Paribas sold 1.67% (₹2,186 cr) on the Nifty-inclusion day; UTI and Nippon MF bought 52 lakh shares. **[U]** September-quarter shareholding pattern (due 21 Oct) and Q2 board-meeting date (likely 4–12 Nov) not yet published.

**Long-term vs next-session relevance [I]** — *Long-term only:* direct global market-data licensing from Jan-2027, co-location pricing (≈20% of market rates), cash-share target "double-digit by CY2027", new indices/derivatives, IIBH stake, valuation vs NSE. *Could change expectations tomorrow:* (1) SEBI settlement/CAS circular or a credible leak; (2) a regulator/finance-ministry headline on expiry, fees or STT; (3) broader risk appetite (Nifty is ≈14–15% below its peak, US–Iran/crude, Fed/RBI hikes, FPI outflows); (4) read-through from Groww's Q2 numbers (14-Oct) and Angel One (15-Oct); (5) first hints of September volumes. No ex-dividend date, AGM, lock-in or index event falls on 14-Oct **[V]**.

---

## 4. Price action and market structure ([C] from `results/snapshot.json`)

| Measure | Value | Reading |
|---|---|---|
| Close vs MAs | 20d ₹3,236 (+4.3%) · 50d ₹3,329 (+1.4%) · 100d ₹3,602 (−6.3%) · 200d ₹3,325 (+1.5%) | rebounding inside a lower-high structure |
| RSI(14) / ATR(14) | 55.6 / ₹106 (3.1% of price) | neutral momentum; wide ATR |
| Returns | 5d +2.1% · 20d −0.3% · 60d −5.8% · from 1-Oct low +10.8% | |
| 52-week position | 54% of range; 24% below high | |
| Realised vol (daily) | 20d 2.40% · 60d 2.17% · 250d 2.43% · Garman-Klass 20d 1.93% | in line with the model's 2.48% |
| Gaps / range | mean \|gap\| 0.50%, mean range 3.2%, 12 of last 50 sessions \|move\| ≥ 3% | high idiosyncratic risk |
| Volume | 13-Oct volume 0.71× its 20-day mean (20d mean inflated by 30m-share 29-Sep), 0.90× 60-day | not a high-conviction rally |
| Delivery % | 40.9% on 12-Oct vs 41.3% 60-day mean; no predictive value found (§8) | |
| Relative strength (to 12-Oct) | vs Nifty 50: 20d +5.8%, 60d −2.7%; vs Capital Markets: 20d +2.5% | outperforming in 2026 (to 8-Oct: BSE ≈ +25% YTD, Nifty −15.6%) |
| Market sensitivity | β to Nifty: 60d 0.61 (corr 0.19), 250d 1.39 (corr 0.49); full-sample 0.89 (corr 0.35) | unstable, low correlation → stock-specific |
| Peers on 13-Oct | Angel One +2.6%, CDSL +2.1%, CAMS +3.2%, KFin +2.8%, MCX −2.4%, Nuvama −3.3% | sector not moving as one block |

**Support / resistance zones [C], descriptive and untested as predictors.** *Resistance:* 3,400–3,405 (13-Oct high 3,403.2, set in the 14:15–14:30 spike), 3,474 (swing high 7-Sep), 3,540–3,670 (3-Aug high 3,671). *Support:* 3,290–3,330 (13-Oct low 3,290.2; volume node 3,272–3,329, 11.6% of the last 120 sessions' volume), 3,159–3,216 (largest node, 12.1%), 3,000–3,131 (1-Oct and 2-Sep lows). *Evidence:* swing pivots (±5 sessions) and volume-by-price over 120 sessions. Several indicators (MAs, RSI, ATR) derive from the same price series and are **not** independent confirmations.

**Options and positioning [C].** ATM implied vol 38.5% annualised on 12-Oct (33rd percentile of its 461-day history; 20-day mean 36.6%) → 2.43%/day; 20-day realised/implied ≈ 0.99. Skew is flat (5%-OTM put 39.8% vs call 38.7%). Put/call OI ratio 0.68 for the 27-Oct series; largest OI at the 3,500 call and 3,000 put. Next stock-F&O expiry 27-Oct; Sensex weekly 15-Oct. **[U]** short interest, order book and bid-ask spread are unavailable; no hidden buying, manipulation or dealer positioning is inferred.

**Intraday structure ([C], 36 validated post-CAS sessions, descriptive).** Volume is U-shaped: first hour 26.7%, the 15:00–15:15 bar alone ≈ 9% (the last continuous bar before the closing auction). The day's **high or low is set in the first hour on 86% of sessions**, and a median 77% of the day's range exists by 10:15. First-hour direction did **not** predict the rest of the day (r = −0.11, p = 0.53, n = 36). Close above bar-VWAP on 44% of days. On 13-Oct the stock was quiet until 14:15, then printed a 1.08m-share bar (14:15–14:30, high ₹3,400.9) and closed in the upper quarter of its range (Nifty +1.6% per a single Yahoo feed).

---

## 5. News, sentiment and catalysts (details and URLs: `research/02_regulatory_macro_catalysts.md`)

| Item | Event date · published | Status | Mechanism | Already priced? |
|---|---|---|---|---|
| SEBI CAS rollback: Reuters (sources) says derivatives settlement will revert to last-30-minute VWAP for ≥ 1 year, effective by end-Oct | 5–6 Oct | single-source | restores expiry-day volumes | **Largely**: BSE +4.4%, +3.9%, +1.5% (5–7 Oct), +10.8% from 1-Oct |
| SEBI chairman: guidelines "in about a week" | 10 Oct (Sat) | confirmed (2 outlets) | timing of the above | partly (+1.3%, +1.4% on 12–13 Oct, cause not found) |
| SEBI consultation paper on CAS/timings/settlement (≈20,000 comments) | 12 Sep; closed 3 Oct | confirmed | defines the outcome tree: pure 30-min VWAP / blended VWAP / CAS retained | partly |
| NSE listed at ₹1,800 (24-Sep), now ≈ below issue | 24 Sep | confirmed | valuation anchor, loses scarcity | yes (−2.7% that day) |
| BSE added to Nifty 50 (30-Sep) | 29 Sep | confirmed | passive flow done; GS/BNP sold 1.67% | yes (+3.3%, then −3.4%, −1.5%) |
| Macro: Nifty ≈14–15% below its 2-Jan peak; US–Iran conflict, Brent ≈ $104, Fed hike (16-Sep), RBI hike to 5.50% (7-Oct), rupee ≈ 95–97, FPI outflows ₹44k cr in Oct; KOSPI −5.5% on 13-Oct | Sep–Oct | confirmed/single-source | risk appetite and FPI flows | market-level yes; Asia's 14-Oct reaction **not yet** |
| Analysts: Jefferies/Bernstein Underperform, Nuvama Hold, Macquarie/JPM positive | Aug–Sep | confirmed | share-gain ceiling vs recovery debate | yes |
| Q2-FY27 results (estimated 4–12 Nov), trading window closed from 1-Oct | — | **[U]** date not announced | volumes weaker than Q1 | partly |

*Sentiment separation.* **News flow** since 1-Oct is improving on the CAS headline; **analyst sentiment** since mid-Aug is cautious on volume durability; **management tone** (Q1 call) is confident but explicitly watchful on regulation; **social-media sentiment** could not be retrieved and is not used. *Surprise vs reaction:* a "less bad than feared" outcome has lifted BSE before (Oct-2024 +2.5%, Mar-2025 +17%); a fee/tax/verbal curb has cut it (−13.7% 29-Apr-2024, −7.3% 16-Feb-2026, −7.6% 21-Aug-2025). The same CAS catalyst produced a rally that fully reversed once already (3–4 Sep +7.6% → 9 Sep −4.5%).

---

## 6. Behaviour across conditions and crises (rules fixed before outcomes; `src/episodes.py`; **small samples**)

| Episode set (rule) | n | BSE day-0 median | β-adjusted excess | Next-day return median [90% CI] · share up | Next-day \|R\| vs 60d σ | 20-day fwd median [CI] |
|---|---|---|---|---|---|---|
| E1 Nifty ≤ −2.5% day | 31 | −3.8% | −1.0% [−1.6, −0.3] | +0.4% [−0.6, +1.4] · 58% | 0.75× | +5.4% [−2.7, +19] |
| E2 VIX ≥ 25 (episode start) | 10 | −2.1% | −0.1% | −0.1% · 50% | 0.31× | −2.2% [−4.1, +11] |
| E3 Nifty ≥ 10% below 250d high (start) — **today's regime** | 20 | −1.7% | −0.4% | −0.1% [−1.1, +0.6] · 45% | 0.57× | +4.2% [−1.3, +8.6] |
| E4a \|BSE return\| ≥ 8% | 35 | +9.4% | +8.8% | −0.1% [−1.2, +0.7] · 49% | 0.64× | +5.0% [+2.8, +8.9] |
| E4b idiosyncratic ≥ 3σ | 44 | +7.2% | +6.7% | −0.4% [−1.1, +0.1] · 43% | 0.66× | +1.7% [−0.6, +5.9] |
| E5 results reaction session | 7 | −1.4% | −0.4% | +0.1% · 71% | — | −1.7% [−11, +23] |

*Measured facts [C]:* COVID crash 20-Feb→23-Mar-2020 BSE −45% vs Nifty −37%; tariff shock 2→7-Apr-2025 −8.4% vs −5.0%; **but** Sep-2024→Mar-2025 correction BSE **+22%** vs Nifty −15.6%, and 2026 YTD BSE ≈ +25% vs Nifty −15.6%. β to the Nifty rose from 0.76 (2020) to 1.25 (2022) to 1.46 (since Jul-2024) while correlation stayed between 0.35 and 0.57, and the gap-fade pattern flips sign across regimes (P(intraday up | gap-up > ½σ) = 0.36 full-sample vs 0.71 since Jul-2024). *Interpretation [I]:* BSE does **not** repeat its crisis behaviour; its drivers shifted from market beta (2020) to F&O-regulation news (2024–26). After shocks there is no systematic next-day continuation or reversal and next-day volatility is **not** elevated in median terms. Differences vs today: the business is 4–6× larger, valuation higher, no debt, the closing mechanism changed, and NSE is now listed.

---

## 7. Forecasting process (auditable flow)

**Verified inputs** (§2) → **current regime** (Nifty ≈14–15% below peak, VIX ≈14–15, BSE vol 2.2–2.4%/day, pending SEBI decision) → **signals** → **method** → **validation** (§8) → **uncertainty** → **conditional forecast** (§9).

| Signal | Observed | Why it might matter | Tested? Result |
|---|---|---|---|
| Recent realised volatility (EWMA, GARCH-t, HAR on gap²+Garman-Klass) | σ_R forecasts 2.28% (EWMA) … 2.61% (S0/GARCH); selected S6 = 2.48% | volatility clusters | **Tested**: improves interval sharpness/calibration vs untimed S0 (Final p = 0.0006); gain ≈ a one-parameter rescale in Final (p = 0.44) |
| Options-implied vol | 38.5% → 2.43%/day | market's own forecast | **Tested** (339 sessions): on par with S6 (p = 0.76), no extra edge |
| Momentum/market/technical/calendar/volume features → direction | — | classic return predictors | **Tested, not found** (Val+Final OOS R² −2.2%, accuracy 51.2% vs 52.9% constant) |
| Delivery % | 40.9% ≈ mean | informed buying | **Tested, not found** (t < 2 everywhere; OOS R² +0.1%, p = 0.16) |
| Gap premium (+0.3% median 2019–2025) | zero since 3-Aug-2026 | VWAP-close convention | Post-hoc test selected it, **overridden by judgement** (§8) |
| Pending SEBI circular | open | regulatory regime | **Untestable** (one event); subjective overlay only |
| Support/resistance, RSI, MAs | §4 | traders' reference levels | **Untested**, descriptive only |

**Method** (pre-registered, `docs/PREREGISTRATION.md`, committed before any BSE return statistic was computed): filtered-historical-simulation quantiles = σ_t × median-centred trailing-500 standardised residuals. σ_t: S6 (geometric mean of GARCH(1,1)-t and HAR) for close-to-close and intraday returns; S4 (HAR on gap²/GK) for the gap; HAR for the range. Location: L0 (median = P0). High/low: joint bootstrap of (gap, high, low, close) vectors scaled by σ_R. Benchmarks: unchanged price, historical mean, expanding-RMS, EWMA, trailing-250/500 empirical quantiles. Models were refit on all sessions through 13-Oct.

---

## 8. Did the method have predictive value? (walk-forward, no look-ahead; code `src/`, tables `results/`)

*Protocol:* expanding window, refit every 20 sessions, 500-session burn-in; Development 2019-02→2024-06 (1,322 forecasts), Validation 2024-07→2025-06 (248), **Final 2025-07→2026-10 (317)**; model selection used Development+Validation only.

**Scale (interval) models, close-to-close [C]** — mean pinball loss ×10⁴ (lower is better), 90% coverage and Kupiec p:

| Model | Dev+Val (n = 1,570) | Final (n = 317) | Final 90% cov (Kupiec p) | Final DM p vs S0 (Holm) |
|---|---|---|---|---|
| S0 expanding-RMS (benchmark) | 54.13 | 49.22 | 96.8% (3e-6) | — |
| S1 EWMA | 53.08 | 47.56 | 88.3% (0.33) | 0.006 (0.006) |
| S2 GARCH-t | 53.17 | 47.45 | 91.2% (0.48) | 0.001 (0.004) |
| S4 HAR-GK | 52.89 | 47.29 | 91.2% (0.48) | 0.001 (0.004) |
| **S6 blend (selected)** | **52.80** | **47.27** | **91.8% (0.27)** | **0.0006 (0.004)** |

The selection rule (lowest Dev+Val pinball) picks S6 for R and I, S4 for the gap, HAR for the range — all pass the Final-window gate. **Caveats found by the independent audit:** (i) S6, S4 and S1 are statistically a tie (S6 vs S1 Final p = 0.11); (ii) in Final, S0 was simply too wide, and **S0 rescaled by one ex-post constant matches S6 (DM p = 0.44)**; vs a trailing-250-day untimed benchmark S6's Final gain is weak (p = 0.084; pooled Dev+Val p = 0.0001; Validation alone p = 0.19); (iii) Validation alone shows no significant gain for any model; (iv) QLIKE ranks S4/S5 first and GARCH below S0 in Final; (v) 50% intervals ran narrow in Final (R: 46%, G: 44%); (vi) Final-window Kupiec power to reject 88% vs 90% is only ≈ 22%, and Dev+Val coverage for S6 was 88.2% (p = 0.017). **Conclusion: modest, real but not overwhelming evidence that volatility models help; "validated" would overstate it.**

**Gap, intraday, range [C]** — selected models beat S0/EMP250 on Final (gap p = 0.006, intraday p = 0.0001, range p = 0.03) with 90% coverage 91%, 91%, 91%. Gap intervals under-covered at 90% in Development (86.5%) and Validation (83.9%) and are the least reliable component.

**Direction / location [C]** — ridge (α = 1000) and logit (C = 0.01), chosen on Development only, on Validation+Final (n = 565): OOS R² vs historical mean **−2.2%**, Clark–West p **0.41**, accuracy **51.2% / 51.9% vs 52.9%** best constant (p = 0.81), AUC 0.515, reliability bins flat. **All four pre-registered gate legs fail → L0.** The Development window had looked significant (R² +1.4%, accuracy 56%, p = 0.0003) and 2019–2023 sub-periods are positive, but 2024+ is negative: an effect that decayed or was never stable. Power is low (≈ 12–26%), so "not found" ≠ "no effect"; the wording is "no demonstrated predictability".

**Gap location (post-hoc)** — a positive median gap (+0.3%) beat zero on Validation+Final (DM p = 0.0007; rule fixed before computing, but motivated by descriptive output). **Overridden:** since 3-Aug-2026 the closing price is the auction price, 16% of gaps are exactly zero (vs 5–6%), positive-gap share fell 70.7% → 44.9% (p = 0.0002), median 0.000%. Post-break n = 49 and partly confounded by a −0.19%/day drawdown; the zero-median gap is a **judgement**.

**Other checks.** OHLC-bootstrap high/low forecasts, Final: 90% coverage high 90.2%, low 88.6% (DM vs S0 p < 0.001 / 0.14). Calibration-adjustment rule (scalar rescale if Final Kupiec p < 0.05) not triggered. Delivery %: no effect. Weekday: Monday variance ≈ 1.4× normal; Wednesday 1.03× (no adjustment). Day-after-big-up-day conditioning (n = 263): next-day up 54% [48, 60]% — descriptive, not used.

**Independent audit** (`research/03_independent_audit.md`, a separate agent session): *no look-ahead in any scale, range, ridge or logit model* (truncation, future-garbage and same-row perturbation tests on real data, with positive controls); S0/S1/S2/S4/S6 results re-derived to ≥ 12 significant figures; both gates reproduced. It also found — and I fixed or disclosed — weak original leak tests (now replaced by `tests/test_same_row_real.py`, which detects an injected leak), two feature defects (location gate unchanged), over-strong wording, unlogged departures (`docs/DEVIATIONS.md` #19–22). Bit-for-bit reproduction: `results/v1_before_audit_fixes/` keeps pre-fix outputs.

---

## 9. Next-session forecast

### A. Current situation
Official close ₹3,375.40 (+1.36%, +10.8% from the 1-Oct low) after a quiet day lifted late (14:15–14:30 spike on 1.08m shares); cash market closed 15:30 IST 13-Oct; regime: Nifty ≈14–15% below its peak, VIX ≈ 14–15, BSE daily vol 2.2–2.4% with options-implied 2.43%; dominant drivers: pending SEBI settlement decision, market risk appetite (Asia −5.5% KOSPI overnight read-through unknown), retail F&O volume trend.

### B. Forecast estimates (log-return model; ₹ at P0 = 3,375.40)
| | 2.5% | 5% | 10% | 25% | **50%** | 75% | 90% | 95% | 97.5% |
|---|---|---|---|---|---|---|---|---|---|
| Open | 3,315 | 3,334 | 3,348 | 3,368 | **3,375** | 3,387 | 3,398 | 3,414 | 3,437 |
| Close | 3,229 | 3,247 | 3,267 | 3,322 | **3,375** | 3,429 | 3,475 | 3,508 | 3,536 |
| Close if the open is exactly P0 (open→close) | 3,238 | 3,252 | 3,281 | 3,327 | 3,375 | 3,422 | 3,468 | 3,494 | 3,517 |
| Day high | 3,356 | 3,368 | 3,379 | 3,397 | 3,424 | 3,462 | 3,505 | 3,544 | 3,563 |
| Day low | 3,182 | 3,213 | 3,249 | 3,298 | 3,336 | 3,366 | 3,388 | 3,398 | 3,415 |

*Intervals are for the **close**, and the high-low row is the predicted **range extremes**, which are different objects: the close lies inside the day's range, and a closing price forecast says nothing about the path.* P(high > P0) 91%, P(low < P0) 80%, P(range straddles P0) ≈ 70–75% (historical frequency). P(close within ±1%) 34%, P(|R| ≥ 2%) 41%, P(R ≥ +4%) = P(R ≤ −4%) = 4.4%.

### C. Scenario table (exhaustive and non-overlapping, partitioned on the close; probabilities are the model's, calibrated only at the 90% interval level; the SEBI overlay is subjective)
| | Bearish: close ≤ ₹3,324.8 (R ≤ −1.5%) | Base: ₹3,324.8 – ₹3,426.0 | Bullish: close ≥ ₹3,426.0 (R ≥ +1.5%) |
|---|---|---|---|
| **Probability** | **26.6%** | **47.6%** | **25.8%** |
| Close range (10/50/90th pct within scenario) | 3,231 / 3,279 / 3,320 | 3,336 / 3,376 / 3,413 | 3,433 / 3,465 / 3,536 |
| Trigger / assumption | risk-off spill-over (Asia chip rout, crude/yields), disappointing SEBI text (blended VWAP or CAS kept), weak Groww read-through, profit-taking after +10.8% | no decisive regulatory news; trades with sector tone and retail-activity data | pro-BSE SEBI outcome or credible leak, strong broker/Groww read-through, risk-on rotation into India |
| Opening behaviour | flat-to-lower; gap below ≈ −0.5% (< 3,358) | within ±0.5% of P0 (3,368–3,387 is the 50% band) | gap above ≈ +0.5% (> 3,392) |
| Conditional intraday trajectory | loses 3,290 (13-Oct low) → next descriptive zone 3,159–3,216; most range set by 10:15 | range-bound, ~2.9% range, extremes usually in the first hour, volume builds into 15:00–15:15 | holds above 3,400–3,405 on rising volume → 3,470–3,540 plausible; failure → round trip (5–7 Oct gains faded) |
| Evidence | β 0.6–1.4 to a market ≈14–15% below its peak; 12/50 days ≥ 3% moves; sell-the-news history; 49× trailing P/E; split analysts | σ model = IV; low relative volume; neutral RSI | CAS headlines gave +3.1% to +4.4% days; IV 38.5% leaves upside tail |
| Invalidation | pre-open indicative > P0 + 0.5% with peers firm, or pure-VWAP circular | first-hour move beyond ±1.5% on > 2× volume, or any regulatory headline | open ≤ P0 with peers weak, or text that retains CAS for expiry settlement |

*Subjective event overlay (SEBI decision hits this session; reaction sizes from 16 hand-picked, hence large-move-biased, dated analogues, median |move| 5.3%):* p = 5% → 95% close interval ₹3,180–3,565; **p = 10% → ₹3,149–3,599 (P(|R| ≥ 4%) 15%)**; p = 15% → ₹3,128–3,625. My own weight is 5–15%; a favourable pure-VWAP text is partly priced, so I would not assume the upside reaction exceeds the downside one.

### D. Intraday trajectory (conditional; no minute-by-minute path)
*Opening:* the pre-open indicative price (09:08 IST) is the first hard datum; inside ₹3,368–3,387 it carries little information. *Middle:* the first hour usually contains the high or the low (86%); **first-hour direction has not predicted the rest of the day** (r −0.11), so I do not suggest continuation or fade. If the open is above 3,400 on strong volume and Angel One/MCX/CDSL are firm, a test of 3,470+ is plausible; if it opens below 3,330 and loses 3,290 early, 3,160–3,215 is the next zone. *Closing:* the closing auction sets the official close (thin: < 1% of cash turnover); the 15:00–15:15 window carries ≈ 9% of the day's volume, so a late move of ±0.2% (mean absolute 15:15-bar move 0.20%) is normal.

### E. Main uncertainties
Pending SEBI text (timing and content); unseen overnight news (Asia open after the KOSPI rout, crude/Iran headlines, US bank earnings, US CPI at 18:00 IST on 14-Oct acts on the 15th); the closing-auction regime has only 49 sessions of history; gap intervals have been the weakest-calibrated part; 50% intervals run narrow; the sample contains a few regime changes (STT hike, RBI curbs, Nifty-50 inclusion, NSE listing) that no model conditioned on; liquidity risk is low (≈ ₹1,100–1,400 cr daily turnover) but the stock has no circuit filter and has gapped 8–17% on rule news; model risk — S1/S4/S6 are a statistical tie and give σ_R of 2.28%–2.61%.

### F. Forecast updates
*Scheduled by you, not automatic — no monitoring is running.* (1) **09:08 IST** pre-open price: re-centre — close ≈ open × exp(I) with σ_I = 2.2% (quantile multipliers: −3.7% / −1.4% / 0 / +1.4% / +3.5% at 5/25/50/75/95%). (2) A SEBI circular: replace this distribution by scenario analysis (§C overlay). (3) Peers (Angel One, MCX, CDSL) and Nifty Capital Markets in the first 30 minutes: agreement with BSE's direction raises odds of a trend day, divergence of > 2% suggests stock-specific flow. (4) **10:15 IST**: if the range already exceeds 3% the day is in the upper tail of volatility (median day range 2.9%). (5) Groww's Q2 numbers (14-Oct) and Angel One's (15-Oct) for retail-derivatives activity.

---

## 10. Final evidence audit and dated forecast record

**Checks.** Arithmetic and timestamps re-verified by code and by the independent audit; prices in ₹; bonus-adjusted series; all material numbers traced to a source or script; correlated signals (MAs/RSI/ATR) not counted as independent; precision limited to ₹1 for prices and 0.1 pp for returns. **Contrary evidence reported:** Validation-window non-significance, S0-rescaling equivalence, decay of the Development-window directional edge, gap premium vs structural break, weak 50% calibration.

**Predictive value:** *volatility/scale — demonstrated against the pre-registered benchmark, only weakly beyond a level correction; direction — not found; gap centre — judgement; intraday path — untested; support/resistance — untested; event risk — subjective.*

**Process honesty.** 22 logged deviations (`docs/DEVIATIONS.md`), including a data error I caught myself (NSE `PREV_CLOSE` not re-based on bonuses), a code bug in the episode study, several exploratory or post-hoc steps, the gap override, and fixes prompted by an independent audit. The location models were evaluated twice (before/after fixing two feature defects). Git commit times, not the log's timestamps, are authoritative.

### Dated forecast record (also `results/forecast_record_2026-10-14.json`)
| Field | Value |
|---|---|
| Stock | BSE Ltd, NSE:BSE (INE118H01025), INR |
| Cutoff / generated | 2026-10-13 16:55 IST / see JSON `generated_utc` |
| Reference price | ₹3,375.40 (official NSE close 13-Oct-2026) |
| Target session | Wed 2026-10-14 |
| Method | pre-registered FHS quantiles; σ: S6 (R, I), S4 (G), HAR (range); L0 location; bootstrap high/low |
| Estimates | gap median 3,375 [90%: 3,334–3,414]; close median 3,375 [50%: 3,322–3,429; 90%: 3,247–3,508]; range median 2.9% [90%: 1.6–5.8%]; P(up) 50% (no skill claimed); scenarios 26.6 / 47.6 / 25.8% |
| Uncertainty | σ_R = 2.48%/day (IV 2.43%); model spread 2.28–2.61%; SEBI-event overlay subjective |
| Invalidation | not a normal full session; official close ≠ 3,375.40 by > 0.3%; SEBI circular before/at the open; gap > ±2.8% |
| Scoring | `python3 src/score_forecast.py results/forecast_record_2026-10-14.json` after NSE publishes 14-Oct data (UDiFF file ≈16:34 IST) |

**Reproduce.** `python3 src/fetch_nse.py … && python3 src/build_dataset.py && python3 src/walkforward.py && python3 src/evaluate.py --periods all && python3 src/run_location.py --stage full && python3 src/forecast_live.py … && python3 tests/test_same_row_real.py`. Raw archives are git-ignored; processed data and all results are committed.
