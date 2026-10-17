# v2 workstream "intraday": intraday structure and session patterns of NSE:BSE

Scope: reference price P0 = ₹3,375.40 (official NSE close 2026-10-13); v2 information cutoff 2026-10-13 22:00 IST; target session Wed 2026-10-14. Everything below is **descriptive** unless a chronological test is named. All numbers come from `results/behaviour/intraday.json`, produced by `src/behaviour/intraday.py` (deterministic: two runs gave byte-identical outputs). Union dataset: `data/processed/intraday_union_15m.csv`.

**Cutoff exposure: none.** The script contains no network code, every input file is asserted to end on or before 2026-10-13 (`meta.max_date_in_inputs` = 2026-10-13), I ran no `fetch_*.py`, did not refresh `data/raw/macro`, and opened no page. The sandbox clock reading 14 Oct was not used for anything. The only sibling document I read for cross-checking (`research/v2/02_news_catalysts_update.md` §3, and v1's `FORECAST_REPORT.md` intraday paragraphs) contains no 14-Oct price information in the passages read. The 14-Oct session was never seen.

---

## 0. Headline results (numbers, not adjectives)

| # | Result | Status |
|---|---|---|
| 1 | Union dataset: 37 sessions (20 workbook + 17 earlier fetch), 917 bars, 18 Aug → 13 Oct; **adds exactly one session (13 Oct) to v1's 36**; 3 sessions fail the validator (17 Aug, 2 Sep, 10 Sep) | `verified_source` (OHLC close = NSE close 37/37) |
| 2 | **The last bar's close equals the official NSE close in 37/37 sessions** (max abs diff ₹0.00): the 15:15 bar in 29 sessions, the 15:00 bar in the 8 sessions where Yahoo has no 15:15 bar | `verified_source` |
| 3 | Volume is U-shaped: opening hour 26.5% of bar volume (CI 23.4–29.8) vs 16% if uniform; midday 11:15–14:15 35.7% (32.9–38.4) vs 48% uniform; 15:00 bar alone 9.0% (7.9–10.2, n=29) | `descriptive_only` |
| 4 | Volatility is open-heavy: the opening hour carries 46.7% of the day's 15-min realized variance (38.6–54.7); mean absolute 15-min return 0.47% in the opening hour vs 0.20% midday (first bar alone 0.83%, 4.1× midday) | `descriptive_only` |
| 5 | **"High or low set in the first hour" = 83.8% (31/37; CI 68.9–92.3) is what a driftless random walk with this same U-shaped variance profile produces (84.9%)**: no excess; high alone 59.5% vs 45.6% benchmark (p=0.10), low alone 32.4% vs 45.7% (p=0.14); none survives Holm | `not_found` (beyond the volatility clock) |
| 6 | Share of the bar range formed by 10:15: mean 0.709 (0.636–0.780), median 0.772; benchmark mean 0.672 (95% band 0.611–0.734), p=0.24; by 11:15 mean 0.760 vs 0.751 | `not_found` (beyond the clock) |
| 7 | First hour vs rest of day: r = −0.064 (CI −0.38 to +0.27, n=37, p=0.71); sign agreement 19/36 = 52.8% (37.0–68.0); walk-forward sign rule hit 37.0% vs 40.7% benchmark (n=27) | `not_found`; power is low (44% to detect ρ=0.3) |
| 8 | Close above the exchange VWAP on 16/37 = 43.2% (28.7–59.1), p=0.51; price-vs-VWAP at 11:15 / 13:15 does not predict the rest of the day (Spearman −0.03 / +0.10) | `not_found` |
| 9 | Closing-auction bar (n=29): mean absolute ln(close/open) of the 15:15 bar = **0.131%** (0.088–0.180), median 0.110%, p90 0.31%, max 0.46%, 6/29 exactly zero; mean abs move from the 15:00 close to the official close 0.134%. **v1's "0.20%" mixed two different bars** | `descriptive_only` |
| 10 | 13 Oct: quiet (every bar ≤1.4× its slot median) until 14:15; the 14:15 bar = 1,076,912 shares = 8.9× slot median, 27.2% of the day's bar volume, range 2.45%, high 3,400.9 then close 3,326.3; 14:30 bar +1.60% on 3.8×. Range formed by 10:15: 34% (2nd lowest of 37) | `descriptive_only`; cause `not_found` (sibling workstream) |
| 11 | 29 Sep: the 15:00 bar held 22,504,261 shares = 74.8% of NSE's 30.1M daily volume (75.4× slot median), closed 3,200.0 = official close = official high | `descriptive_only` |
| 12 | 14-Oct levels (+0.82% / −2.56% from P0; 0.35σ / 1.09σ): in the 2,368-session history with similar σ-distance the previous-day high was touched 71.1% (67.3–74.6, n=584) and the low 23.5% (18.5–29.3, n=234), close to a volatility-scaled random walk (72.9% / 29.2%). No resistance at prior highs out of sample; **persistence of breaks at prior lows** (58.4% close beyond after a touch, 62.6% in the latest 40%) | highs `not_found`; lows `validated_out_of_sample` (scope-limited, §4.4) |
| 13 | Tests run: 25 (registry in §9); after Holm only R01 and R02 (long-history level tests) are below 5%; nothing in the 37-session window survives Holm (smallest: C04 0.096, L01 0.103) | |

---

## 1. Data: how the union was built and what was excluded

**Sources and rules** (fixed before computing any outcome; code docstring D1–D4):

* A (preferred): `data/processed/xlsx_15m_clean.csv` = user workbook, Yahoo chart API values, 20 sessions 15 Sep → 13 Oct, 495 bars.
* B: `data/raw/intraday/*.csv`, used only for sessions not in A: 17 of 20 such sessions pass (17 Aug, 2 Sep, 10 Sep fail). B's 495 bars overlapping A are used for a cross-check only. B stores float32 artefacts (e.g. 3266.10009765625); snapped to the 0.05 tick after verifying the deviation was < 0.0001 everywhere.
* Validation re-implemented in the script with the **same constants and tests as `src/validate_intraday.py`** (close ±0.02%, high/low ±0.25%, volume ratio 0.80–1.02, ≥24 bars, per-row OHLC ±₹0.06, volume>0 except the last row, bar-open within 0.4% of previous close). The original file is untouched; `data/processed/intraday_validation.csv` predates the 13-Oct daily row (it says "NO DAILY ROW" for 13 Oct), so I could not reuse it. All 20 workbook sessions pass, including 13 Oct (volume ratio 0.961).
* Every row carries `source` (`xlsx_workbook` or `earlier_fetch`), `session_bars`, `has_1515_bar` and `vol_other_source` (the earlier fetch's volume for the same bar where both exist).

**Excluded sessions and why** (JSON `data.excluded_sessions`):

| Session | Failed check | Detail |
|---|---|---|
| 2026-08-17 | high | bar high is ₹30.4 below the NSE high (3,390.4): the fetch lost the opening spike |
| 2026-09-02 | row OHLC | one garbled 15:00 bar (low 3,167.7 above min(open, close) 3,165.2 + 0.06) |
| 2026-09-10 | bar continuity | the 15:15 bar opens at the auction price 3,306.0 vs 15:00 close 3,286.1 (+0.60%). **This is a genuine large auction jump excluded by a rule written for garbled rows**; all other checks pass (volume ratio 0.991). It matters only for §6 (see sensitivity there). |

**Overlap check (495 bars in both sources):** 0 price mismatches > ₹0.051; 2 volume mismatches, both first bars: 16 Sep 09:15 workbook 290,601 vs earlier 142,512 (2.04×) and 7 Oct 09:15 473,178 vs 225,402 (2.10×). The workbook value is used (direct API, preferred). Session volume ratio to NSE is 0.9998 / 0.9999 with the workbook value and 0.949 / 0.962 with the earlier value; both are inside the accepted range, so NSE totals cannot say which is right. Effect on the union: ≤0.1 pp on the first-bar share of two sessions.

**Effective sample.** 37 non-overlapping sessions (39 trading days in the span 18 Aug → 13 Oct; 2 excluded). Bars inside a session are dependent, so every bar-level statistic has **37 sessions as its effective sample (29 for anything about the 15:15 bar)**. One regime only (closing-auction close, since 3 Aug). 36 of the 37 sessions are v1's 36, so nothing here confirms v1 independently.

---

## 2. The workbook's pitfalls, re-examined

| Pitfall | What the data show | Consequence |
|---|---|---|
| **Missing 15:15 bar** | 8 of 37 union sessions (5 in the workbook: 17 Sep, 22 Sep, 29 Sep, 8 Oct, 9 Oct; 3 more in the earlier fetch: 18 Aug, 24 Aug, 3 Sep). In the earlier fetch these are explicit all-null rows, so the omission is upstream (Yahoo), not a workbook artefact. Weekdays: 3 Tue, 3 Thu, 1 Mon, 1 Fri (no inference drawn). | Never treat "last bar" as 15:15. Use the **combined 15:00–15:30 window**, i.e. ln(official close / 14:45 close), which exists in all 37 sessions. |
| **Where the closing print sits when 15:15 is missing** | In the 8 sessions the **15:00 bar's close equals the official close in 8/8**, and in 5/8 it is also that bar's high. In the 29 sessions with a 15:15 bar the 15:00 close equals the official close in 1/29 (coincidence) and is the bar high/low in 0/29 (Fisher exact p = 0.0001). | The closing print is attached to the 15:00 bar in those sessions. 15:00-bar volume, return and range are **not comparable** between the two groups (the 15:00-bar volume share is 9.0% in the 29 pure sessions and 16.7% in the 8, driven by 29 Sep at 75.9%). |
| **Closing-auction bar = auction price** | Last-bar close = official close in 37/37 (max diff ₹0.00); the daily file has `last == close` in 37/37. The 15:15 bar's open differs from the 15:00 close (mean absolute difference ₹1.48, max ₹7.0; equal in only 9/29). Its high/low equal the envelope of {open, close} in 26/29 sessions, i.e. **the bar carries two prices and a volume, nothing about the path inside the auction window**. | The "auction move" can only be measured as ln(close/open) of that bar or ln(official close/15:00 close). |
| **Zero-volume bars** | 10 of 29 15:15 bars have volume 0 (6 in the workbook, 4 in the earlier fetch); zero-volume bars exist **only** at 15:15 (no zero bar in any other slot of 917). Their price still moves (mean absolute move 0.135% vs 0.129% for positive-volume ones). | The 15:15 bar's volume is feed volume, **not the auction volume**. Auction volume is not identifiable here. |
| **Bar volume vs NSE daily** | Mean 94.2% (82.7%–99.99%) of NSE daily volume; 5.8% unattributed. The shortfall is the same with and without a 15:15 bar (93.3% vs 94.4%) and uncorrelated with the absolute auction move (r = 0.10, p = 0.59). | Cause still unestablished. All volume "shares" below are shares of **bar** volume. |
| **First-bar open ≠ official open** | Mean absolute ln(first bar open / official open) 0.115%, max ₹22.1; equal (±0.05) in only 3/37 sessions. | First-hour returns are measured from the **official open** (pre-open auction price); the v1 definition (bar open) is reported as a variant. |
| **Bars miss ticks** | At least one of bar high / bar low misses the NSE extreme in 94.6% of sessions: bar high below NSE high (mean ₹0.94, max ₹5.3; exact in 12 of 37), bar low above NSE low (mean ₹1.11, max ₹4.5; exact in 6 of 37). The official extreme can be the pre-open price (official open = official high in 2 sessions, = low in 2). | Timing of extremes is approximate. Sensitivity (§4.2): at most 1 (high) / 2 (low) of 37 sessions are ambiguous between windows; counting the official open as a path point changes **no** session's window. |
| **Bar VWAP ≠ exchange VWAP** | Typical-price bar VWAP vs turnover/volume: mean −2.4 bps, mean absolute error 6.3 bps, worst −36 bps on 29 Sep. | The exchange VWAP (turnover/volume from bhavcopy) is used for the close-vs-VWAP test. |
| **1-hour sheet volume defective** | Zero volume in 22 hourly bars: **16 are the 09:15 opening-hour bar (16 of 20 sessions)** and 6 are the 15:15 bar. The 30-minute sheet has zeros only where 15m has them (6, all 15:15). | The one hour with 27% of the day's volume is unusable on the hourly sheet. |

---

## 3. What the 30-minute and 1-hour sheets add (cross-check)

Rebuilt from the 15-minute bars of the same 20 sessions and compared bar by bar (JSON `timeframes`):

| | 15 min | 30 min | 1 hour |
|---|---|---|---|
| Bars / sessions | 495 / 20 | 255 / 20 | 135 / 20 |
| OHLC mismatches vs rebuilt-from-15m (> ₹0.051) | – | **0 of 255** | **0 of 135** |
| Volume mismatches > 1% | – | 0 | **16** (all 09:15 bars, sheet = 0) |
| First-hour high/low classification differs from 15m | – | 0 of 20 | 0 of 20 |
| Range share by 10:15 differs | – | max diff 0.0 | max diff 0.0 |

**They add no information.** Same 20 sessions (15 Sep → 13 Oct), identical highs/lows/closes, no extra history, no pre-open data, nothing finer than 15 minutes.

What each timeframe supports (this dataset only):

* **15 min**: all of §4–§6 (25 slots, running range/VWAP, bar-level timing of extremes to ±15 min, spike bars, the 15:00 and 15:15 slots). Cannot: timing inside a bar (the 14:15 bar on 13 Oct cannot be split), auction volume, pre-open price, order book.
* **30 min**: first hour (2 bars), range by 10:15 and 11:15 (2 and 4 bars) are exactly reproducible; volume is correct. Cannot: the "last hour" 14:30–15:30 (the 14:15 bar spans 14:15–14:45, so only 14:45–15:30 is separable), the 15:00 vs 14:45 split.
* **1 hour**: first-hour OHLC, range by 10:15 and 11:15, and the closing bar are right; **volume is wrong in the opening hour**; cannot separate 14:15–15:15 into 14:30+ or 15:00+, so no last-hour or pre-auction statistics.
* Fine for a coarse picture of price, **not** for volume profiles or the 15:00–15:30 window.

---

## 4. Results

Conventions: sessions are the unit; "CI" = 95% percentile bootstrap over sessions (10,000 draws, seed 20261013; a circular block-3 bootstrap is stored alongside in the JSON and differs by <1 pp for the means shown); proportions use Wilson intervals. Windows are defined by bar start time: opening hour 09:15–10:14 (slots 0–3), late morning 10:15–11:14, midday 11:15–14:14 (12 bars), afternoon 14:15–14:59 (3 bars), closing window 15:00–15:29 (15:00 + 15:15 bars). "Last hour" = bars starting 14:30–15:15.

### 4.1 (1) Time-of-day profiles — `descriptive_only`

Windows, mean over 37 sessions (JSON `profile.windows`); 29 Sep distorts the closing window, so the ex-29-Sep value is shown:

| Window | Uniform share | Volume share % (CI) | Ex 29 Sep | Share of realized variance % (CI) | Mean abs 15-min return % (CI) |
|---|---|---|---|---|---|
| Opening hour 09:15–10:14 | 16.0 | **26.5** (23.4–29.8) | 27.2 | **46.7** (38.6–54.7) | **0.471** (0.405–0.538) |
| Late morning 10:15–11:14 | 16.0 | 13.8 (12.3–15.4) | 14.1 | 10.2 (7.7–12.9) | 0.222 (0.187–0.258) |
| Midday 11:15–14:14 | 48.0 | 35.7 (32.9–38.4) | 36.5 | 31.0 (24.8–37.5) | **0.202** (0.176–0.230) |
| Afternoon 14:15–14:59 | 12.0 | 12.7 (10.7–15.2) | 12.8 | 7.5 (4.1–12.2) | 0.202 (0.152–0.263) |
| Closing window 15:00–15:29 | 8.0 | 11.3 (8.7–15.5) | **9.6** (8.4–10.8) | 4.6 (2.4–7.3) | 0.296 per 30 min (0.186–0.442) |

* Opening-hour volume per bar is 2.23× the midday per-bar volume (ratio of mean shares; bootstrap CI 1.90–2.62; mean of the per-session ratios 2.42); it is higher in 89% of sessions. First-bar mean |return| is 4.1× the midday mean.
* Peak slots by mean volume share: 15:00 (10.7%; 9.0% in the 29 pure sessions, median 8.1%), 09:15 (8.5%), 09:30 (7.6%), 09:45 (5.7%), 14:45 (5.1%). Quietest: 12:45 (2.5%), 12:30, 12:15, 11:45, 12:00 (2.7–2.9%). The 15:15 bar: 0.86% (0.47–1.37, n=29, median 0.52%).
* Full 25-slot table:

| Bar start | n | Vol share % (mean) | 95% CI | median | mean excl. 29 Sep | mean bar range % | mean abs 15-min return % [95% CI] | share of day variance % |
|---|---|---|---|---|---|---|---|---|
| 09:15 | 37 | 8.49 | 6.78–10.48 | 6.86 | 8.70 | 1.51 | 0.83 [0.64, 1.03] | 25.7 |
| 09:30 | 37 | 7.63 | 6.65–8.64 | 7.53 | 7.82 | 0.90 | 0.51 [0.38, 0.64] | 12.7 |
| 09:45 | 37 | 5.69 | 4.84–6.75 | 5.36 | 5.82 | 0.63 | 0.25 [0.19, 0.31] | 3.5 |
| 10:00 | 37 | 4.71 | 3.80–5.79 | 3.87 | 4.81 | 0.62 | 0.30 [0.22, 0.40] | 4.8 |
| 10:15 | 37 | 4.23 | 3.56–4.94 | 3.60 | 4.33 | 0.53 | 0.23 [0.16, 0.31] | 2.4 |
| 10:30 | 37 | 3.52 | 3.09–3.98 | 3.41 | 3.60 | 0.48 | 0.24 [0.20, 0.29] | 2.5 |
| 10:45 | 37 | 3.03 | 2.62–3.48 | 2.92 | 3.09 | 0.44 | 0.20 [0.15, 0.26] | 2.3 |
| 11:00 | 37 | 3.00 | 2.43–3.67 | 2.58 | 3.05 | 0.44 | 0.22 [0.16, 0.29] | 3.0 |
| 11:15 | 37 | 3.30 | 2.65–4.13 | 2.84 | 3.37 | 0.44 | 0.20 [0.13, 0.27] | 3.2 |
| 11:30 | 37 | 3.15 | 2.60–3.80 | 2.66 | 3.21 | 0.43 | 0.22 [0.14, 0.33] | 3.9 |
| 11:45 | 37 | 2.77 | 2.26–3.36 | 2.18 | 2.82 | 0.40 | 0.22 [0.16, 0.27] | 2.2 |
| 12:00 | 37 | 2.91 | 2.48–3.35 | 2.81 | 2.96 | 0.41 | 0.20 [0.14, 0.26] | 2.2 |
| 12:15 | 37 | 2.75 | 2.29–3.27 | 2.31 | 2.80 | 0.42 | 0.24 [0.17, 0.32] | 3.5 |
| 12:30 | 37 | 2.68 | 2.32–3.05 | 2.62 | 2.74 | 0.33 | 0.13 [0.10, 0.16] | 1.0 |
| 12:45 | 37 | 2.52 | 2.05–3.01 | 2.13 | 2.57 | 0.37 | 0.18 [0.12, 0.26] | 2.8 |
| 13:00 | 37 | 3.03 | 2.50–3.65 | 2.71 | 3.11 | 0.35 | 0.19 [0.14, 0.24] | 2.0 |
| 13:15 | 37 | 3.17 | 2.55–3.95 | 2.74 | 3.25 | 0.38 | 0.18 [0.12, 0.26] | 2.6 |
| 13:30 | 37 | 3.07 | 2.49–3.76 | 2.59 | 3.14 | 0.42 | 0.22 [0.16, 0.29] | 2.4 |
| 13:45 | 37 | 3.23 | 2.45–4.33 | 2.42 | 3.30 | 0.41 | 0.23 [0.14, 0.38] | 2.7 |
| 14:00 | 37 | 3.14 | 2.53–3.87 | 2.65 | 3.21 | 0.41 | 0.23 [0.13, 0.35] | 2.4 |
| 14:15 | 37 | 3.92 | 2.88–5.47 | 2.98 | 4.01 | 0.43 | 0.16 [0.10, 0.23] | 1.6 |
| 14:30 | 37 | 3.68 | 3.06–4.43 | 2.86 | 3.70 | 0.44 | 0.23 [0.14, 0.35] | 3.6 |
| 14:45 | 37 | 5.06 | 4.43–5.78 | 4.65 | 5.04 | 0.43 | 0.22 [0.16, 0.28] | 2.3 |
| 15:00* | 37 | 10.67 | 8.14–14.74 | 8.14 | 8.86 | 0.54 | 0.29 [0.18, 0.44] | 4.6 |
| 15:15 | 29 | 0.86 | 0.47–1.37 | 0.52 | 0.86 | 0.14 | 0.13 [0.10, 0.18] | (in 15:00 row) |

\*The 15:00 row mixes 29 pure 15:00 bars with 8 sessions whose 15:00 bar carries the closing print (return = ln(official close / 14:45 close), variance share = the combined 15:00–15:30 window). The 15:15 row's return is ln(auction close / 15:00 close). In the 29 pure sessions the 15:00 bar's mean |return| is 0.26%.

Benchmark: a uniform-time profile (4% per bar). Exceptions: 29 Sep (the 15:00 bar is 75.9% of the day, the opening hour only 3.6%) and 4 Sep, the only session with ≥ 50% of volume in the opening hour (58.3%). Per-session values are in JSON `sessions`.

### 4.2 (2) Timing of the session high and low — `not_found` beyond the volatility clock

Plain frequencies (JSON `timing`), n = 37:

| | First hour (09:15–10:14) | Midday | Last hour (14:30–15:29) |
|---|---|---|---|
| High | **22 = 59.5%** (43.5–73.7) | 11 | 4 = 10.8% (4.3–24.7) |
| Low | **12 = 32.4%** (19.6–48.5) | 16 | 9 = 24.3% (13.4–40.1) |
| High **or** low in the first hour | **31 = 83.8%** (68.9–92.3) | | high or low in last hour 13 = 35.1% |
| Both in the first hour | 3 = 8.1% | | |

Hourly histograms (bars starting 09:15 / 10:15 / 11:15 / 12:15 / 13:15 / 14:15 / 15:15): highs 22 / 4 / 1 / 1 / 3 / 6 / 0, lows 12 / 2 / 5 / 2 / 5 / 11 / 0.

**The right benchmark is not "16% of the day".** Because the first hour carries 46.7% of the realized variance, a driftless random walk run on the **empirical variance clock** (200,000 simulated paths, 1-minute steps) puts the high in the first hour with probability 45.6% (low 45.7%), in the last hour 21.3% (21.5%), and has *either* extreme in the first hour 84.9% of the time. (A uniform-clock arcsine law would give 26.2% for any 16% window.) Against that benchmark:

| Test (registry id) | Observed | Benchmark | Exact binomial p | Holm / BH |
|---|---|---|---|---|
| T01 high in first hour | 59.5% | 45.6% | 0.100 | 1.0 / 0.41 |
| T02 low in first hour | 32.4% | 45.7% | 0.137 | 1.0 / 0.43 |
| T03 high in last hour | 10.8% | 21.3% | 0.158 | 1.0 / 0.44 |
| T04 low in last hour | 24.3% | 21.5% | 0.689 | 1.0 / 1.0 |
| (descriptive) high or low in first hour | 83.8% | 84.9% | 0.82 | not in family |

The v1 statement "the first hour usually contains the high or the low (86%)" is true as a frequency but **is exactly what the U-shaped volatility profile alone implies**; it is not an extra regularity. Highs lean toward the first hour (+14 pp) and lows away from it (−13 pp), but each deviation is within sampling error at n=37, and the two cancel in the "either" statistic. No difference survives correction.

**Share of the day's bar range already formed** (running high − running low over the final bar range):

| | Mean (CI) | Median (CI) | Benchmark mean (95% band for a mean of 37) | p (MC) | ≥ 0.5 / ≥ 0.75 of sessions |
|---|---|---|---|---|---|
| By 10:15 (T05) | **0.709** (0.636–0.780) | 0.772 (0.579–0.854) | 0.672 (0.611–0.734) | 0.236 | 78% / 51% |
| By 11:15 (T06) | **0.760** (0.692–0.824) | 0.812 (0.649–0.934) | 0.751 (0.692–0.809) | 0.757 | 86% / 59% |

In 3 of 37 sessions the whole bar range existed by 10:15 (24 Aug, 9 Sep, 12 Oct). Lowest: 7 Oct 0.25, 13 Oct 0.34, 1 Oct 0.35.

Sensitivities (not registered; stated after the first run): (A) clock with the first bar measured from the first printed open instead of the official open: benchmark 45.8%/45.7%/21.3%/21.4%, same conclusions; (B) counting the official open as a path point: **0 sessions change window**, high-first-hour still 22/37; missed-tick ambiguity: ≤1 session (high) and ≤2 (low) could switch window (bounds for high-in-first-hour 59.5%–59.5%, low 27.0%–32.4%). Limits: the benchmark ignores day-level drift (trend days push extremes to the ends), and the bar extremes miss up to ₹5.

### 4.3 (3) First hour versus the rest of the day; opening gap — `not_found`

Definitions (code docstring): G = ln(official open / adjusted prev close); FH = ln(10:00-bar close / official open); Rest = ln(official close / 10:00-bar close); I = FH + Rest.

| Statistic | Value | n | Test / status |
|---|---|---|---|
| Pearson r(FH, Rest) | **−0.064** (Fisher CI −0.380 to +0.266; bootstrap −0.405 to +0.337) | 37 | T07 p = 0.71 |
| Spearman | +0.029 (p = 0.86) | 37 | |
| v1 definition (FH from first bar open) | r = −0.112, p = 0.51 | 37 | v1 had −0.108, p = 0.53, n = 36 |
| Rest has the sign of FH | **19/36 = 52.8%** (37.0–68.0) | 36 | T08 p = 0.87; continuation after up first hour 8/18 = 44.4%, after down first hour 11/18 = 61.1% |
| Slope of Rest on FH | −0.086 (se 0.228) | 37 | |
| Walk-forward S01 (rule: sign of the running correlation × sign of FH; first 10 sessions training) | hit rate **37.0%** vs benchmark (sign of running mean of Rest) **40.7%** | 27 | McNemar exact p = 1.0 → **not validated**; the rule chose "continuation" in only 26% of test sessions |

Opening gap (G ≠ 0 in 34 sessions: 20 up, 14 down, 3 exactly zero; median |G| 0.46%):

| Subset | n | Statistic | Value (CI) | p | Holm / BH |
|---|---|---|---|---|---|
| All, sign(G)·I | 34 | mean | +0.53% (−0.11 to +1.17); 24/34 = 70.6% of days move in the gap direction (53.8–83.2) | T09 0.116 | 1 / 0.41 |
| Gap up (C01) | 20 | mean Rest | +0.07% (−0.52 to +0.68); r(FH, Rest) = +0.18 | 0.82 | 1 / 1 |
| Gap down (C02) | 14 | mean Rest | +0.05% (−0.95 to +1.20); r(FH, Rest) = −0.44 | 0.93 | 1 / 1 |
| Large gap, \|G\| ≥ 0.46% (C03) | 19 | mean sign(G)·I | −0.18% (−0.99 to +0.65) | 0.69 | 1 / 1 |
| **Small gap, \|G\| < 0.46% (C04)** | 15 | mean sign(G)·I | **+1.43%** (+0.61 to +2.17); 13/15 move in the gap direction | **0.0042** | **0.096 / 0.029** |
| Walk-forward S02 (sign(I) from G) | 27 | hit 48.1% vs benchmark 44.4% | | McNemar p = 1.0 | not validated |

* **C04 is contradicted by the long history.** In the 2,208 earlier daily sessions the small-gap sign(G)·I is −0.01% (n=1,104, p=0.85); in 2024 → Aug 2026 it is −0.37% (n=283, p=0.02, i.e. a fade) and −0.50% for the 144 small-gap sessions among the 281 sessions from 24 May 2025 to 17 Aug 2026 (p=0.01). The +1.4% in the window is a 15-session streak (late-Sep/Oct trend days). Caveat: pre-3-Aug closes are 30-minute VWAPs, so I there is not the same quantity as in the window. Not carried forward.
* First-hour magnitude (base rates for v1's "invalidation" trigger): mean |FH| 1.01%, median 1.10%; **|FH| ≥ 1.5% in 10/37 = 27% (15.4–43.0)**; with first-hour volume > 2× the median first-hour volume, 2/37 = 5.4% (1.5–17.7; 3 and 4 Sep). A move beyond ±1.5% alone is therefore not rare.
* Power: |r| must exceed 0.324 for p < 0.05 at n=37; power at ρ = 0.3 is 44%, at ρ = 0.5 89%. The sign test (n=36) has 16% power against a true 60% and 61% against 70%; the walk-forward test (n=27) has 10% and 41%. **A modest continuation or reversal effect (ρ ≈ 0.2–0.3) could not have been detected.** The daily history (n=2,357, `results/conditional_day.json`) has corr(G, I) = −0.043, while its 2024-07+ sub-period has +0.021 and P(I>0 | gap up > 0.5 sd) = 71% (n=42) against 36% (n=273) in the full sample: unstable across periods.

### 4.4 (4) Price relative to VWAP, previous close, previous-day high/low

**VWAP** — `not_found`

* Close above the exchange session VWAP (turnover/volume): **16/37 = 43.2%** (28.7–59.1), V01 p = 0.51; with the bar-based VWAP 17/37 = 45.9%. Mean ln(close/VWAP) = +0.06% (−0.24 to +0.39).
* State at the checkpoint does not predict the rest of the day: 11:15 Spearman −0.034 (p = 0.84; above VWAP at 11:15 in 15 sessions, mean Rest −0.18%; below in 22, +0.25%); 13:15 Spearman +0.105 (p = 0.54; above in 14, +0.56%; below in 23, −0.02%).
* At each checkpoint hour from 10:00 to 15:00 only 35–46% of sessions have the bar close above the running bar-VWAP (descriptive; no inference attached).

**Previous close** — `descriptive_only`

* Side persistence (close on the same side of prev close as at the checkpoint): 10:15 76% (28/37; 60–87), 11:15 73%, 12:15 84%, 13:15 89% (33/37; 75–96), 14:15 89%.
* **Gap fill** (price touches the previous close after a non-zero gap): **18/34 = 52.9%** (36.7–68.5) vs 25.1 expected (73.8%) from the zero-drift reflection principle with σ = RMS of the previous 20 daily open→close returns; L01 p = 0.0047, Holm 0.103, BH 0.029. On the long history this benchmark is well calibrated (2,208 sessions: 75.3% observed vs 75.7% expected), though 2024 → Aug 2026 already ran below it (71.1% vs 78.6%; last 281 sessions 71.2% vs 77.3%). So the window's shortfall (55.6% vs 74.6% for the 36 daily sessions 18 Aug → 13 Oct with a non-zero gap, which include 2 Sep and 10 Sep; CI 39.6–70.5) is directionally in line with the recent drift but too large for the history; it is the same phenomenon as C04 (gaps persisting in this window) and carries the same warning. Not significant after Holm.

**Previous-day high and low** — the 13 Oct low ₹3,290.2 (−2.56% from P0, 1.09σ) and high ₹3,403.2 (+0.82%, 0.35σ), σ = trailing-20 RMS of daily returns = 2.34%/day (2.48% in v1; results barely change, see JSON `sensitivity_sigma_2.48pct`).

| Evidence | Prev-day high | Prev-day low |
|---|---|---|
| 37-session window: touched (official daily H/L) vs zero-drift reflection benchmark from the open | 19/37 = 51.4% vs 51.0% (L02 p = 1.0) | 17/37 = 45.9% vs 51.6% (L03 p = 0.51) |
| Long history (2,368 sessions, prev-close origin, σ-scaled): touched / benchmark | 46.8% / 46.2% | 49.0% / 58.0% |
| **Sessions with the same σ-distance as 14 Oct** (±0.15σ high, ±0.20σ low): touched | **71.1%** (67.3–74.6), n = 584; benchmark 72.9%; first 60%: 71.6%, last 40%: 70.4% | **23.5%** (18.5–29.3), n = 234; benchmark 29.2%; 23.9% / 23.1% |
| Once touched, does the day **close beyond the level** (R01/R02; 0.5 under a zero-drift martingale) | **44.1%** (40.8–47.5), n = 827, p = 0.0008, Holm 0.020. **First 60% (to 2022-11-30): 38.9% (p ≈ 1e-6); last 40%: 51.8% (46.4–57.1), p = 0.55.** Drift-adjusted expectation 46.7% overall (p = 0.21), 49.4% in the last 40% | **58.4%** (55.3–61.4), n = 1,012, p = 1e-7, Holm 3e-6. **First 60%: 55.8% (p = 0.004); last 40%: 62.6% (57.7–67.3), p ≈ 9e-7.** Drift-adjusted expectation 54.4% overall (p = 0.027), **50.9% in the last 40%** |
| In the 18 Aug → 13 Oct daily window (counts only; includes 2 Sep and 10 Sep) | 9 of 14 touches closed above | 11 of 17 touches closed below |

Reading: (i) **Prior-day extremes are touched about as often as their distance and the stock's volatility imply**; there is no measurable barrier effect on touch frequency (the lower level is touched somewhat less than the random-walk benchmark predicts at every distance inside 1σ, a miscalibration of the benchmark, not a level effect). (ii) **Resistance at a prior high** (R01): present in 2017 → 2022 (38.9%), absent in the latest 40% (51.8%, consistent with 50% and with the drift-adjusted 49.4%) → fails the chronological split: `not_found`. (iii) **Breaks of a prior low tend to persist** (R02): the direction chosen on the first 60% (> 0.5) holds in the last 40% (62.6%) and exceeds both the zero-drift (50%) and the drift-adjusted (50.9%) benchmarks (the last-40% p of ≈ 9e-7 stays below 0.05 even with a Holm factor of 26) → `validated_out_of_sample` **with scope limits**: it is a conditional frequency from the same long history (split inside history, not a post-cutoff test), sessions are serially dependent (so the exact-binomial p is optimistic), it is about what happens *after* a touch (not a forecast of direction), and it likely reflects the same asymmetry as v1's finding that closes sit in the bottom third of the day's range 47% of the time (one signal, not two). For 14 Oct the product P(touch 3,290.2) × P(close below | touch) ≈ 0.235 × 0.58–0.63 ≈ 14–15%, almost identical to the random-walk figure (0.29 × 0.5), so it adds nothing to the unconditional close-below-level probability.

### 4.5 (5) The 15:00–15:15 bar and the closing-auction bar — `descriptive_only`

Sessions with a 15:15 bar: n = 29 (Aug 19, 20, 21, 25, 26, 27, 28, 31; Sep 1, 4, 7, 8, 9, 11, 15, 16, 18, 21, 23, 24, 25, 28, 30; Oct 1, 5, 6, 7, 12, 13).

| Quantity | Mean (CI) | Median | Mean abs (CI) | Other |
|---|---|---|---|---|
| **Auction move: ln(15:15 close / 15:15 open)** | +0.070% (+0.007 to +0.130) | +0.083% | **0.131%** (0.088–0.180) | 6/29 exactly zero; \|move\| ≥ 0.25%: 4/29; ≥ 0.5%: 0; p90 0.31%; max 0.46% (26 Aug −0.46%, 18 Sep +0.44%, 5 Oct +0.37%) |
| Gap between 15:00 close and 15:15 open | −0.029% (−0.053 to −0.008) | −0.003% | 0.045% | |
| Move from 15:00 close to the official close | +0.041% (−0.023 to +0.103) | +0.041% | **0.134%** (0.096–0.176) | |
| All 37 sessions: 14:45 close → official close (the 30-minute window) | +0.186% (+0.054 to +0.350) | +0.039% | **0.296%** (0.184–0.439) | typical 30-min \|return\| 11:15–14:45: 0.290% |

* Scale: the mean absolute auction move is 0.65× a typical 15-minute move (0.20%); the whole 15:00–15:30 window is as large as an ordinary 30-minute interval. v1's "mean absolute 15:15-bar move 0.20%" is **not the auction move**: it was |ln(close[−1]/close[−2])| over whichever row was last (15:15 bar in 28 sessions, 15:00 bar in 8).
* Mean signed auction move +0.070%: A02 p = 0.037, **Holm 0.79, BH 0.19** → not distinguishable from zero after correction (`not_found`); A01 corr(15:00-bar return, auction move) = −0.22 (bootstrap −0.51 to −0.06; Spearman −0.35; p = 0.25 → `not_found`; 13 of 23 non-zero pairs reverse the 15:00 bar's direction).
* **Mapping to the official close:** the 15:15 bar's close **is** the official NSE close (29/29, max diff ₹0.00); for the other 8 sessions the 15:00 bar's close is (8/8). Daily `last == close` 37/37. The bar's own open/high/low contain no information beyond {open, close}.
* Sensitivity: adding the 15:15 bars of the three validator-failed sessions (n = 32) gives mean abs auction move 0.136% and mean abs move from the 15:00 close 0.157%: 17 Aug −0.46% (−0.45% from the 15:00 close), 2 Sep +0.09%, **10 Sep 0.00% within the bar but +0.60% from the 15:00 close**. The 10-Sep exclusion removes the largest 15:00-close-to-auction move in the sample.
* Zero-volume vs positive-volume 15:15 bars: mean |move| 0.135% vs 0.129%. The feed's 15:15 volume (0.86% of bar volume on average) is therefore **not** a measure of auction activity; v1's "thin: < 1% of cash turnover" is `unverifiable` from this data and, on 29 Sep, the closing print carried 75% of the day's volume (§4.6).
* The 15:00 bar before the auction (29 pure sessions): volume share 9.0% (7.9–10.2), median 8.1%; mean |return| 0.26%; it is the single busiest slot after the open, in line with v1's "≈ 9%".
* Effect on the forecast: with σ_R ≈ 2.4%/day, an auction move with mean |size| 0.13% (sd 0.17%) adds about 0.3–0.5% of the variance of R; the close is effectively the 15:15 price ± 0.13%.

### 4.6 (6) Anatomy of 13 October and of the large-volume sessions — `descriptive_only`

**13 Oct** (prev close 3,330.20; official open 3,332.00 (first print 3,343.70); high 3,403.20; low 3,290.20; close 3,375.40; G +0.05%, FH +0.06%, Rest +1.23%, R +1.35%; bars sum 3,959,915 = 96.1% of NSE's 4,119,552). Volume multiples are against the 36 other sessions' slot medians:

| Bar | O | H | L | C | Volume | × slot median | % of day | ret % | range % | run-VWAP | C vs run-VWAP % |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 09:15 | 3343.7 | 3349.0 | 3312.2 | 3329.9 | 113,300 | 0.4 | 2.9 | −0.06 | 1.10 | 3330.4 | −0.01 |
| 09:30 | 3330.1 | 3345.8 | 3322.2 | 3331.0 | 114,200 | 0.4 | 2.9 | +0.03 | 0.71 | 3331.7 | −0.02 |
| 09:45 | 3330.0 | 3341.0 | 3326.5 | 3340.5 | 150,551 | 0.8 | 3.8 | +0.28 | 0.43 | 3333.4 | +0.21 |
| 10:00 | 3339.0 | 3346.0 | 3333.1 | 3334.0 | 92,822 | 0.5 | 2.3 | −0.19 | 0.39 | 3334.3 | −0.01 |
| 10:15 | 3334.4 | 3340.2 | 3332.0 | 3337.8 | 49,451 | 0.3 | 1.2 | +0.11 | 0.25 | 3334.5 | +0.10 |
| 10:30 | 3337.0 | 3341.1 | 3325.3 | 3329.8 | 60,680 | 0.4 | 1.5 | −0.24 | 0.47 | 3334.2 | −0.13 |
| 10:45 | 3329.8 | 3331.5 | 3311.0 | 3324.7 | 129,147 | 1.1 | 3.3 | −0.15 | 0.62 | 3332.1 | −0.22 |
| 11:00 | 3324.7 | 3326.7 | 3318.6 | 3322.2 | 34,454 | 0.3 | 0.9 | −0.08 | 0.24 | 3331.6 | −0.28 |
| 11:15 | 3323.0 | 3325.0 | 3303.1 | 3304.9 | 124,852 | 1.1 | 3.2 | −0.52 | 0.66 | 3328.7 | −0.72 |
| 11:30 | 3303.1 | 3309.1 | 3297.2 | 3303.1 | 101,481 | 0.8 | 2.6 | −0.05 | 0.36 | 3326.0 | −0.69 |
| 11:45 | 3303.1 | 3318.0 | **3291.7** | 3312.3 | 134,036 | 1.4 | 3.4 | +0.28 | 0.80 | 3323.7 | −0.34 |
| 12:00 | 3312.3 | 3312.3 | 3301.0 | 3310.0 | 46,270 | 0.4 | 1.2 | −0.07 | 0.34 | 3323.1 | −0.39 |
| 12:15 | 3310.0 | 3312.0 | 3304.1 | 3310.0 | 56,296 | 0.5 | 1.4 | 0.00 | 0.24 | 3322.4 | −0.37 |
| 12:30 | 3310.0 | 3320.1 | 3308.8 | 3314.5 | 114,784 | 1.1 | 2.9 | +0.14 | 0.34 | 3321.7 | −0.22 |
| 12:45 | 3314.8 | 3319.5 | 3312.7 | 3317.0 | 41,869 | 0.5 | 1.1 | +0.08 | 0.21 | 3321.6 | −0.14 |
| 13:00 | 3315.8 | 3316.9 | 3309.5 | 3312.5 | 77,772 | 0.8 | 2.0 | −0.14 | 0.22 | 3321.1 | −0.26 |
| 13:15 | 3313.0 | 3315.0 | 3303.9 | 3312.0 | 102,388 | 0.9 | 2.6 | −0.02 | 0.34 | 3320.4 | −0.25 |
| 13:30 | 3310.2 | 3332.9 | 3310.0 | 3329.2 | 132,732 | 1.3 | 3.4 | +0.52 | 0.69 | 3320.7 | +0.26 |
| 13:45 | 3329.1 | 3338.4 | 3314.2 | 3316.0 | 110,970 | 1.1 | 2.8 | −0.40 | 0.73 | 3320.8 | −0.15 |
| 14:00 | 3314.2 | 3320.0 | 3311.3 | 3319.9 | 44,485 | 0.4 | 1.1 | +0.12 | 0.26 | 3320.7 | −0.02 |
| **14:15** | 3318.6 | **3400.9** | 3318.6 | 3326.3 | **1,076,912** | **8.9** | **27.2** | +0.19 | **2.45** | 3331.0 | −0.14 |
| 14:30 | 3326.2 | 3385.0 | 3310.4 | 3379.9 | 465,382 | 3.8 | 11.8 | **+1.60** | 2.23 | 3334.8 | +1.34 |
| 14:45 | 3380.0 | 3384.0 | 3360.1 | 3366.9 | 301,922 | 1.5 | 7.6 | −0.39 | 0.71 | 3337.7 | +0.87 |
| 15:00 | 3366.7 | 3378.3 | 3361.0 | 3374.0 | 256,891 | 0.8 | 6.5 | +0.21 | 0.51 | 3339.9 | +1.02 |
| 15:15 | 3371.6 | 3375.4 | 3371.6 | 3375.4 | 26,268 | 1.2 | 0.7 | +0.04 | 0.11 | 3340.1 | +1.05 |

* Until 14:15 every bar had volume ≤ 1.4× its slot median; cumulative volume to 14:15 was only 46.3% of the day (the median of the other sessions is about 79%, i.e. 100% − 20.8%). Price drifted from 3,343 to a low of 3,291.7 (11:45), then oscillated 3,310–3,330. **Range formed by 10:15: 34%, rank 2 lowest of 37.** The high (3,400.9 in bars; NSE 3,403.2) was set in the 14:15 bar (could be anywhere in 14:15–14:30; the bars do not resolve it), the low in the 11:45 bar (NSE low 3,290.2 vs bar 3,291.7).
* The 14:15 bar: 8.9× the slot median (8.87× when measured, as the news workstream did, against the 19 other workbook sessions; independent recomputation agrees), 27.2% of the day's bar volume; high +2.45% above its open, then a fall of 2.2% from the bar high to a close +0.23% above the bar's open (+0.19% close-to-close); the **next bar (14:30)** was the second leg up (+1.60%, 3.8×). 14:15–15:30 held 53.7% of bar volume (rank 2 of 37 after 29 Sep; median of the other sessions 20.8%, 19.9% excluding 29 Sep).
* Close 3,375.4 vs exchange VWAP 3,343.2 (+0.96%); close position in the official range 0.754 (upper quarter, barely).
* The cause is `not_found` (sibling workstream `02_news_catalysts_update.md` §3); nothing here identifies it, and price patterns do not identify intent.

**29 Sep** (Nifty 50 inclusion effective after the close; documented in the dossiers): prev close 3,097.50; official open 3,100.00 (= official low); high 3,200.00 = close; G +0.08%, FH +0.23%, Rest +2.95%, R +3.26%. Selected bars:

| Bar | O | H | L | C | Volume | × slot median | % of day | ret % |
|---|---|---|---|---|---|---|---|---|
| 11:30 | 3170.0 | 3186.0 | 3170.0 | 3184.9 | 351,126 | 2.8 | 1.2 | +0.49 |
| 14:15 | 3139.1 | 3146.9 | 3135.2 | 3143.0 | 212,942 | 1.8 | 0.7 | +0.12 |
| 14:30 | 3143.3 | 3183.5 | 3142.7 | 3168.7 | 848,018 | 6.9 | 2.9 | +0.81 |
| 14:45 | 3162.7 | 3172.6 | 3144.3 | 3158.0 | 1,698,673 | 8.6 | 5.7 | −0.34 |
| **15:00** | 3160.1 | **3200.0** | 3131.4 | **3200.0** | **22,504,261** | **75.4** | **75.9** | **+1.32** |

There is no 15:15 bar; the 15:00 bar closes at the official close and contains **74.8% of NSE's 30,101,047 shares** (bars sum 29.64M = 98.5%), so for that session the closing-auction print is inside the 15:00 bar. Not a "bar" in the ordinary sense, and 29 Sep alone moves the closing-window mean volume share from 9.6% to 11.3% (§4.1). Bulk deals at 3,200 are documented in the dossiers; I attach no intention to the price path.

**Largest volume bars** (JSON `anatomy.top12_bars_by_volume`): 29 Sep 15:00 (22.5M, 75.4×), 4 Sep 09:15 (2.51M, 9.8×, +1.95%), 29 Sep 14:45 (1.70M, 8.6×), 4 Sep 09:30 (1.13M, 3.8×), 31 Aug 13:45 (1.12M, 11.3×, −2.43%), **13 Oct 14:15 (1.08M, 8.9×)**, 3 Sep 09:45, 5 Oct 15:00 (995,107, 3.3×), 20 Aug 09:15, 24 Sep 10:00 (911,116, 5.5×), 29 Sep 14:30, 6 Oct 09:15. Largest sessions by NSE volume: 29 Sep 30.1M (6.9× the median session), 4 Sep 7.98M, 6 Oct 6.87M, 21 Sep 6.74M, 5 Oct 6.74M.

Spike rule fixed in advance (bar volume ≥ 5× slot median of the other sessions **and** range ≥ 2%): 31 Aug 13:45 (−2.43%) and 14:00 (+2.10%), 4 Sep 09:15 (+1.95%), 24 Sep 10:00 (+1.28%), 29 Sep 15:00, 13 Oct 14:15. The move from the end of each spike bar to the official close: +1.81% (31 Aug 13:45, reversing the bar), −0.29%, −1.66% (4 Sep, reversing), −2.71% (24 Sep, reversing), 13 Oct +1.47% (continuing). Of the four non-index spike events (31 Aug, 4 Sep, 24 Sep, 13 Oct) three were reversed by the close and the 13 Oct move continued; **n = 4, no inference**.

---

## 5. (7) Recomputing `results/intraday_profile.json`, and which v1 statements change

The v1 script reproduces exactly on v1's 36-session sample (0 differing keys, `v1_comparison.v1_code_reproduced_on_v1_sample`). Columns: v1 as published; v1's own definitions run on the union (37); corrected definitions on the union.

| Key (v1 name) | v1 (36) | v1 code on union (37) | Corrected definition on union | Change |
|---|---|---|---|---|
| volume share, first bar % | 8.41 | 8.49 | 8.49 | none |
| volume share, first hour % | 26.73 | 26.51 | 26.51 (23.4–29.8) | none |
| volume share, "last hour" % | 20.46 | 20.58 | **20.08** (14:30–15:30 aligned) | v1 used the last 4 rows: 14:30–15:15 in 28 sessions, 14:15–15:00 in 8 |
| **volume share, "last bar 15:15" %** | **4.395** | 4.293 | **0.857** (15:15 bar, n=29); 15:00 bar 9.0% (n=29); 15:00+15:15 11.3% (n=37) | **v1 value is wrong**: it averages the 15:15 bar (28 sessions) and the 15:00 bar (8 sessions) |
| high in first hour | 0.611 | 0.595 | 0.595 (22/37) | −1.6 pp; benchmark 0.456 |
| low in first hour | 0.333 | 0.324 | 0.324 (12/37) | benchmark 0.457 |
| high in last hour | 0.111 | 0.108 | 0.108 | benchmark 0.213 |
| low in last hour | 0.250 | 0.243 | 0.243 | benchmark 0.215 |
| **high or low in first hour** | **0.861** | 0.838 | 0.838 (31/37; 0.689–0.923) | 86% → 84%, and **equals the random-walk benchmark 0.849** |
| median range share formed by 10:15 | 0.773 | 0.772 | 0.772 (0.579–0.854); mean 0.709 vs benchmark 0.672 | none; consistent with the benchmark |
| corr(first hour, rest) | −0.108 (p 0.532, n 36) | −0.112 (p 0.509, n 37) | −0.064 (p 0.709, n 37) from the official open | conclusion unchanged: `not_found` |
| P(rest continues first-hour direction) | 0.500 | 0.486 | 0.528 (19/36; 0.370–0.680) | unchanged (≈ coin flip) |
| P(close above VWAP) | 0.444 | 0.459 (bar VWAP) | 0.432 vs exchange VWAP (16/37; 0.287–0.591) | unchanged; p = 0.51 |
| **last-bar 15:15 mean abs move %** | **0.1965** | 0.1924 | **0.131** within the bar; 0.134 from the 15:00 close (n=29); 0.296 for the 14:45 → close window (n=37) | **changes**: v1 mixed bars |
| last-bar 15:15 mean signed move % | +0.1121 | +0.1102 | +0.070 within bar (CI +0.007 to +0.130, Holm p 0.79) | smaller; not significant |

**v1 report statements (FORECAST_REPORT.md) affected:**

1. "The 15:00–15:15 bar alone ≈ 9%" — **stands** for the 29 sessions where it is a pure bar (9.0%, median 8.1%); it is 10.7% over all 37 sessions only because of 29 Sep. The JSON key behind it (`volume_share_last_bar_1515_pct` = 4.4%) is mislabelled.
2. "High or low set in the first hour on 86% of sessions" and "extremes usually in the first hour" — frequency 84% on 37 sessions; **no longer a regularity worth conditioning on**: a driftless walk with the same U-shaped variance gives 85%.
3. "A median 77% of the day's range exists by 10:15" — stands (77.2%, mean 70.9%) but is also what the variance clock implies (benchmark mean 67.2%).
4. "First-hour direction did not predict the rest of the day (r = −0.11, p = 0.53, n = 36)" — stands (−0.11, p = 0.51, n = 37; −0.06 from the official open); the study cannot exclude |ρ| up to ≈ 0.3–0.4.
5. "Close above bar-VWAP on 44% of days" — 46% (bar VWAP) / 43% (exchange VWAP); not different from 50%.
6. "The closing auction sets the official close (thin: < 1% of cash turnover)" — the first half is verified 37/37; the second half is **unsupported**: the 15:15 bar's volume is not auction volume, and on 29 Sep the closing print carried 75% of the day.
7. "A late move of ±0.2% (mean absolute 15:15-bar move 0.20%) is normal" — **0.13%** for the auction bar (90th percentile 0.31%, max 0.46%), 0.30% for the whole 15:00–15:30 window.
8. 13 Oct: "quiet until 14:15, then a 1.08m-share bar (high ₹3,400.9) and closed in the upper quarter of its range" — **confirmed** (every earlier bar ≤ 1.4× slot median; close position 0.754).
9. Conditional trajectory table: "most range set by 10:15 / extremes usually in the first hour" — see 2–3: the base rates are right, but they are properties of the volatility profile, not of price direction.
10. Invalidation trigger "first-hour move beyond ±1.5% on > 2× volume": fired in 5.4% of sessions (2/37); the move alone (≥ 1.5%) in 27%.
11. "Volume builds into 15:00–15:15" — confirmed (14:45 5.1%, 15:00 10.7% mean / 8.1% median, the largest median after the open).

---

## 6. Validation status and effect on the next session forecast (summary by claim)

| Claim | Status | n (eff.) | Effect on next-session forecast |
|---|---|---|---|
| Last-bar close = official close (37/37) | `verified_source` | 37 | The official close of any session = the last bar's close; there is no extra auction noise to model beyond the 15:15 move. |
| U-shaped volume / open-heavy volatility | `descriptive_only` | 37 | Scale only: ≈ 47% of the intraday variance arrives by 10:15. |
| Highs/lows cluster in the first hour | `not_found` beyond the clock | 37 | None; do not use "extremes in the first hour" as an additional signal. |
| First hour → rest of day | `not_found` (S01 failed) | 37 (27 test) | None (no continuation/fade rule). |
| Gap continuation, small gaps | `contradicted` by 2,208 earlier sessions | 15 | None. |
| Gap fill below benchmark | `descriptive_only` (BH 0.029, Holm 0.10) | 34 | None to the centre; weakly says gaps may persist more than in history. |
| Price vs VWAP | `not_found` | 37 | None. |
| Prev-day high resistance (R01) | `not_found` out of sample | 827 touches | None. |
| Prev-day low break persistence (R02) | `validated_out_of_sample` (scope-limited) | 1,012 touches | Conditional only: after a touch of ₹3,290.2, close below it ≈ 58–63%; unconditional probability unchanged. |
| Touch frequencies at 14-Oct distances | `descriptive_only` | 584 / 234 | P(touch 3,403.2) ≈ 71%, P(touch 3,290.2) ≈ 23–24% (history, σ-scaled); same as the random-walk benchmark to within 2–6 pp. |
| Auction move | `descriptive_only` | 29 | Mean absolute ΔP ≈ 0.13% (p90 0.31%); adds ≈ 0.3–0.5% of the variance of R. |
| 15:15-bar volume as auction volume | `unverifiable` | – | Cannot size auction liquidity. |
| 13 Oct and 29 Sep anatomy | `descriptive_only` | 1 each | A late-day volume surge with a 2.45% bar range has precedents in this window (31 Aug 13:45, 24 Sep 10:00); n too small to conditionalise. |

---

## 7. Contrary evidence and what would reverse each conclusion

* **First-hour extremes:** the point estimates lean the way v1 said for highs (59.5% vs 45.6%). A larger sample (e.g. 150+ sessions) could turn a +14 pp excess significant; with n=37 the Wilson interval for the high alone (43.5–73.7%) contains the benchmark. A drifting clock (e.g. much lower first-hour variance share in a calmer regime) would change the benchmark itself.
* **No first-hour effect:** this is also a low-power result (§4.3); a true ρ of 0.2–0.3 is undetectable. The 2024-07+ conditional table (`conditional_day.json`) had the opposite gap-continuation sign to the full history, so regime dependence is possible.
* **Gap persistence in the window** (C04, L01) is the one pattern that looked strong (BH q ≈ 0.03) and it is contradicted by long history; it would be revived only if the same sign shows up again in sessions after the window (14 Oct is not usable as a test: it is out of bounds for this analysis).
* **R02** would be reversed by a stable fall in the post-touch breakdown rate to ≈ 50% in the next ~100 touch events, or by evidence that the 50.9%/54.4% drift-adjusted benchmark is the right baseline for the current auction-close regime (the long history is mostly VWAP-close).
* **Auction move:** one regime of 29 sessions; expiry-day dislocations documented for index products (dossier 02, R3) did not produce a |move| > 0.46% in this stock's bar, but 10 Sep (+0.60%, excluded by a validator rule) did.
* **Data:** third-party bars (Yahoo), tick misses, 8 missing 15:15 bars with the closing print folded into the 15:00 bar, volume ≈ 94% of NSE's, and a validator that excluded 3 sessions (one for a legitimate auction jump). If the 3 excluded sessions were repaired, n would be 40, still a single regime.

## 8. Gaps (what is missing and its effect)

* Auction-session volume and price formation (indicative price path 15:15–15:30): not in any file; effect: auction liquidity and the 15:15–15:30 path stay unknown; only open and close of the window are observed.
* Pre-open (09:00–09:08) indicative price and volume: not available; the first-print vs official-open difference (mean 0.115%, max ₹22.1) is therefore unmodelled.
* Minute-level data: Yahoo 1-minute/direct API not used (rate limits and the cutoff rule); the 13 Oct 14:15 bar cannot be resolved inside its 15 minutes, and nothing is invented there.
* History beyond 18 Aug for 15-minute bars: none; the earlier-fetch sessions 17 Aug, 2 Sep and 10 Sep could be recovered only by a re-fetch, which this task did not run.
* Cause of the 5.8% bar-volume shortfall: unestablished (not explained by the presence of a 15:15 bar or by the auction move).
* TradingView: none supplied; not used (terms of service).

## 9. Test registry (25 tests, all two-sided; Holm = FWER, BH = FDR across the whole family)

| ID | Test | n | Observed | Benchmark | p raw | Holm | BH |
|---|---|---|---|---|---|---|---|
| T01 | session high in first hour | 37 | 0.5946 | 0.4562 | 0.100 | 1 | 0.415 |
| T02 | session low in first hour | 37 | 0.3243 | 0.4575 | 0.137 | 1 | 0.427 |
| T03 | session high in last hour | 37 | 0.1081 | 0.2130 | 0.158 | 1 | 0.439 |
| T04 | session low in last hour | 37 | 0.2432 | 0.2146 | 0.689 | 1 | 1 |
| T05 | mean share of range formed by 10:15 | 37 | 0.7095 | 0.6719 | 0.236 | 1 | 0.573 |
| T06 | mean share of range formed by 11:15 | 37 | 0.7598 | 0.7506 | 0.757 | 1 | 1 |
| T07 | corr(FH, Rest) | 37 | −0.0636 | | 0.709 | 1 | 1 |
| T08 | P(sign Rest = sign FH) | 36 | 0.5278 | 0.5 | 0.868 | 1 | 1 |
| T09 | mean sign(G)·I | 34 | +0.0053 | | 0.116 | 1 | 0.415 |
| C01 | G>0: mean Rest | 20 | +0.0007 | | 0.823 | 1 | 1 |
| C02 | G<0: mean Rest | 14 | +0.0005 | | 0.927 | 1 | 1 |
| C03 | large abs G: mean sign(G)·I | 19 | −0.0018 | | 0.686 | 1 | 1 |
| C04 | small abs G: mean sign(G)·I | 15 | +0.0143 | | 0.0042 | 0.096 | 0.029 |
| S01 | walk-forward sign(Rest) from FH | 27 | hit 0.370 | 0.407 | 1.0 | 1 | 1 |
| S02 | walk-forward sign(I) from G | 27 | hit 0.481 | 0.444 | 1.0 | 1 | 1 |
| V01 | P(close > exchange VWAP) | 37 | 0.4324 | 0.5 | 0.511 | 1 | 0.961 |
| V02 | Spearman(price vs VWAP at 11:15, rest of day) | 37 | −0.0341 | | 0.841 | 1 | 1 |
| V03 | Spearman(price vs VWAP at 13:15, rest of day) | 37 | +0.1046 | | 0.538 | 1 | 0.961 |
| L01 | touch of previous close (gap fill) | 34 | 18 | 25.1 | 0.0047 | 0.103 | 0.029 |
| L02 | touch of previous-day high | 37 | 19 | 18.9 | 1.0 | 1 | 1 |
| L03 | touch of previous-day low | 37 | 17 | 19.1 | 0.512 | 1 | 0.961 |
| R01 | prev-day high: P(close above \| touched from below), long history | 827 | 0.4414 | 0.5 | 0.0008 | 0.020 | 0.010 |
| R02 | prev-day low: P(close below \| touched from above), long history | 1,012 | 0.5840 | 0.5 | 1e-7 | 2.5e-6 | 2.5e-6 |
| A01 | corr(15:00-bar return, auction-bar move) | 29 | −0.2197 | | 0.252 | 1 | 0.573 |
| A02 | mean auction-bar move | 29 | +0.0007 | | 0.037 | 0.786 | 0.187 |

**Process record (honest).** The first run covered the 23 tests T01–A02 with definitions fixed before any union statistic was computed (v1's summary numbers had been read; v1's sessions are 36 of these 37). After seeing that output I added, each defined before being computed: R01/R02 (rejection vs breakthrough at prior extremes on the long history), follow-ups F1/F2 (long-history checks of the two nominally interesting cells C04 and L01), sensitivity (A) (clock from the first printed open) and (B) (official open as path point), the 14-Oct σ-distance frequencies, and the v1 invalidation-trigger base rate. None of these changes a registered result; they are labelled in the JSON. The family-wise count includes R01/R02 (25 tests). R01/R02 use serially dependent sessions, so their exact-binomial p-values are optimistic; their chronological split is the safeguard. The MC benchmark assumes a martingale on a fixed variance clock and ignores day-level drift and fat tails.

## 10. Reproduction

`cd /home/user/pred_18 && PYTHONPATH=src python3 src/behaviour/intraday.py` (≈ 8 s, no network). Writes only `data/processed/intraday_union_15m.csv` and `results/behaviour/intraday.json`. Output is deterministic (seed 20261013). I independently recomputed the headline numbers from the CSV with a separate script (sessions 37, bars 917, first-hour volume 26.51%, highs/lows in first hour 22/12, range-by-10:15 mean 0.7095 and median 0.7723, corr −0.0636, auction mean abs 0.1312% on 29): all equal. No git command was run.
