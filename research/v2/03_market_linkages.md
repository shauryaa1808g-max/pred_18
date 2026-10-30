# v2 / 03 — Market, sector and macro linkages of BSE Ltd (NSE: BSE)

Workstream "linkages". Cutoff 2026-10-13 22:00 IST. P0 = ₹3,375.40. Code `src/behaviour/linkages.py` (≈25 s, deterministic, seed 20261013); all numbers below are read from `results/behaviour/linkages.json`. The protocol (definitions, windows, thresholds, families) is the module docstring, written before any BSE beta, correlation or regression was computed. Nothing under `src/`, `docs/`, `results/` (other than my JSON), `data/processed/` or the frozen v1 forecast was edited; no git commands were run.

## 1. Bottom line (numbers)

* **Follow, not lead, the market.** BSE's same-day beta to Nifty 50 is **0.89 (95% HAC CI 0.77–1.01), correlation 0.35**, n = 2,388 sessions 2017-02-06→2026-10-13. The beta is unstable: calendar-year betas run from 0.28 (2019) to 1.82 (2025); the rolling-250-session beta is 1.38 now (range 0.27–1.96), the last 120 sessions give 0.75. Versus the NSE Capital Markets index (2024-09-16→, n = 513) beta is **1.47 (1.32–1.61), correlation 0.81**, but BSE is itself a constituent (weight 15–23% according to unverified web sources), and 34–51% of the BSE–index covariance is BSE's own weight times its own variance. Peers: correlations 0.29–0.49 (CDSL 0.49, Angel One 0.42, MCX 0.39).
* **Most of BSE's variance is its own.** Idiosyncratic share vs Nifty 50: **87.5% (bootstrap CI 83–91%)** over the full sample, 80.7% in 2025-onward, 75.9% in the last 250 sessions (CI 62–90%). vs Nifty 50 + equal-weight peers: 67.3% (61–73%). vs Nifty 50 + Capital Markets: 31.2% (26–36%, inflated explanatory power by the constituent overlap). For the open gap G alone the idiosyncratic share vs the Nifty gap is 73.6%, for open-to-close I it is 91.5%.
* **No lead over the indices; weak lead over two sector peers.** Of 130 lead-lag cells (13 series × lags ±1..±5) 16 have raw p < 0.05 (6.5 expected by chance); after Holm only **3 survive: CDSL at lag −1 (BSE leads CDSL, r = 0.097) and +1 (CDSL leads BSE, r = 0.092), Angel One at lag −1 (r = 0.121)**. No Nifty/Next 50/Midcap/Bank/FinServ/Capital-Markets/India-VIX lag survives; lags 2–5 are all null.
* **Previous US session predicts the next Indian opening gap: validated out of sample, but economically small for 14 Oct.** S&P 500 → G: slope **0.276 pp of BSE gap per +1% S&P (CI 0.215–0.337)**, walk-forward OOS R² **+7.85%** (n_oos = 1,813, CW t 6.4, Holm p = 3e-10) and a fixed chronological split (train ≤2022, test 2023-01→2026-10-13) OOS R² **+6.79%** (Holm p = 2e-4). For close-to-close R: slope 0.304 (0.194–0.414), OOS R² +1.70% (WF) / +1.34% (split). The slope is **not stable**: 0.178 / 0.291 / 0.454 in chronological thirds, 0.03 in 2019, 0.68 in 2026, last-250-sessions 0.585 (0.406–0.764); test-minus-train difference +0.184 (p = 0.021). Sign positive in 10/10 calendar years for G, 8/10 for R.
* **Live adjustment for 14 Oct.** At 16:17:42 UTC (21:47 IST, 13 min before the cutoff) the S&P 500 was 7,797.72 vs the 12-Oct close 7,807.24 = **−0.122%** (≈2h47m into the session; full session ends 01:30 IST). Mechanical gap adjustment = β·(x − sample mean 0.053%) = **−0.048 pp (full-sample β; CI −0.038…−0.059)** or **−0.102 pp (last-250 β)**, against sd(G) = 1.11%. An exploratory composite (S&P, US VIX +1.37%, BSE's own +1.35% day, BSE's −0.86% residual vs Nifty) gives **−0.16 pp (CI −0.30…−0.02)** but was chosen after looking at the same sample. For the close-to-close return the composite shift is −0.04 pp (CI −0.40…+0.32): no adjustment is supported. The adjustment is 0.04–0.15 sd of G: statistically validated, practically negligible, and the 13-Oct US move being unfinished adds variance, not bias.
* **Asymmetry, VIX regimes, rates, oil: not found.** Down-market beta 1.00 vs up-market 0.76 (difference 0.25, CI −0.01…0.50, raw p = 0.06, Holm p = 0.61); beta by ex-ante India VIX tercile 1.07 / 1.04 / 0.85 (Wald p = 0.30). Correlation is higher in the high-VIX tercile (0.49 vs 0.22) but the Forbes–Rigobon correction gives 0.24: a variance effect, not a change in linkage. US 10-year yield and Brent: no association (Holm p = 1.0).

## 2. Data, alignment, access

| item | what was done |
|---|---|
| BSE | `data/processed/bse_daily.csv` via `load_bse()/targets()`; G = ln(open/prev), I = ln(close/open), R = G+I; 2,388 sessions 2017-02-06→2026-10-13. Close definition changed 2026-08-03 (30-min VWAP → closing auction): the auction era has 50 sessions. |
| Indices | `index_daily.csv` (to 2026-10-12). Index/peer returns use the same two BSE session dates (Muhurat/special sessions BSE drops are rolled into the next regular session). **13-Oct row added** from `nsearchives…/ind_close_all_13102026.csv` (HTTP 200, Last-Modified 2026-10-13 14:20:38 GMT = 19:50 IST, before the cutoff; fetched 21:33 IST): Nifty 50 22,721.95 (+1.59%), Next 50 +0.84%, Midcap 100 +1.06%, Bank +1.02%, FinServ +1.45%, Capital Markets +0.51%, India VIX 14.12 (−7.7% log). Capital Markets used only from 2024-09-13 (a stray 2023-04-12 value is discarded; a v1 audit finding had flagged a zero-filled version of this series). |
| Peers | `peers_daily.csv`; NSE PREV_CLOSE is not re-based for splits/bonuses, so returns use an adjusted close; ex-dates detected from close₋₁/close ≈ integer: CDSL 2024-08-23 (×2), CAMS 2025-12-05 (×5), Nuvama 2025-12-26 (×5), MCX 2026-01-02 (×5), Angel One 2026-02-26 (×10); KFin none. |
| Macro (FRED, event time) | S&P 500 and VIX through 2026-10-12, US 10y through 2026-10-08, Brent spot through 2026-10-06, USD/INR (Fed H.10 noon NY) through 2026-10-02, i.e. stale by 1, 1, 3, 5, 7 business days at the cutoff. FRED was deliberately not refreshed (a refresh could contain post-cutoff values). |
| Time-zone alignment | Indian session k = 03:45–10:00 UTC. A US session of calendar date u ends 20:00 UTC, **after** the Indian close of the same date. "Prior window" of session k = US observations dated in [d_{k−1}, d_k) (all complete before the Indian open of d_k) → used for every predictive claim. The "same" window (d_{k−1}, d_k] is used only for FX and Brent as an association (it contains information after the close). Sessions whose window holds no US observation (day after a US holiday, 75 of 2,388 for S&P) are dropped. Indian-lag features use session k−1 (known at 15:30 IST). |
| Publication lag | The backtest uses event time (value dated u assumed known after u's close). For the live nowcast the files are too stale, so Yahoo/ECB quotes are used and flagged as unofficial and time-misaligned. |

Access log (also in the JSON): FRED CSVs read as supplied; `data/raw/macro/usdinr_ecb_2017_2026.json` is an HTML "301 Moved Permanently" page, not data (unused); Frankfurter/ECB USD/INR 2026-10-01→13 OK with `curl -L` (live check only: 96.73 on 9 Oct, 95.78 on 12 Oct, 95.28 on 13 Oct); NSE archive index file OK; Yahoo chart API OK for ^GSPC, ES=F, ^VIX, ^TNX, BZ=F, INR=X (one request per symbol, no 429; Yahoo's `previousClose` for ^VIX, 14.84, is the 9-Oct close and was replaced by FRED's 12-Oct close 15.21); stooq connection reset (unused); GIFT Nifty / SGX Nifty / Asian overnight indices not obtainable and not in the supplied data. A web-search summary (not the PDF) gave BSE's weight in NIFTY Capital Markets as 22.88% (NSE factsheet 2025-03-28) vs 15.09% (an Angel One article): unverified.

## 3. Test accounting (260 registered hypothesis tests, ten families)

| family | tests | raw p<0.05 | Holm p<0.05 | BH q<0.05 |
|---|---|---|---|---|
| F1 lead-lag correlations (13 series × 10 lags) | 130 | 16 | 3 | 3 |
| F2 walk-forward predictors of next-session R | 23 | 12 | 7 | 11 |
| F3 same for the opening gap G | 23 | 9 | 7 | 7 |
| F4 same for open→close I | 23 | 4 | 0 | 0 |
| F5 conditional (same-day index) beta forecast | 2 | 2 | 2 | 2 |
| F6 asymmetry / VIX-regime | 16 | 5 | 2 | 2 |
| F7 contemporaneous macro sensitivity | 14 | 5 | 3 | 4 |
| F8 S&P 500 → G and R (split and walk-forward CW) | 4 | 4 | 4 | 4 |
| F9 incremental to S&P (exploratory) | 12 | 7 | 7 | 7 |
| F10 does BSE lead others (walk-forward) | 13 | 4 | 3 | 3 |

Walk-forward rule (fixed in advance): expanding window, rows j<k only, minimum 500 training rows (250 for predictors with fewer than 1,500 paired rows), benchmark = expanding mean of the same target; OOS R² = 1 − SSE_model/SSE_mean; Clark–West one-sided t with Newey–West 5 lags; `validated_out_of_sample` iff OOS R²>0 and Holm-adjusted CW p<0.05 within the family. I also report a stricter v1-style gate (positive in both OOS halves and without the five largest |y| sessions); **every label below that is "validated" also passes the strict gate.** The statistics are slope estimates with HAC (Newey–West 5) CIs; "effective n" = n·(se_iid/se_HAC)², which absorbs heteroskedasticity as well as autocorrelation.

Disclosed changes made after the first run (all in the docstring): a bug in the S&P status (an adjusted p of exactly 0 was treated as 1, which wrongly labelled the G walk-forward as failing) was fixed; F9, F10, the placebo diagnostics, the strict gate and the live arithmetic were added after seeing F2–F8 (F9/F10 are labelled exploratory where applicable); an arithmetic slip in the docstring (14 vs 13 series, 140 vs 130 cells) was corrected.

## 4. (a) Betas and correlations of R on each factor (full sample, HAC)

| series | n (n_eff) | period | beta [95% CI] | corr | beta 2025→ | rolling-250 now (min–max) |
|---|---|---|---|---|---|---|
| Nifty 50 | 2388 (1543) | 2017-02-06→ | 0.892 [0.774, 1.010] | 0.354 | 1.53 | 1.38 (0.27–1.96) |
| Nifty Next 50 | 2388 (1749) | | 0.939 [0.843, 1.036] | 0.416 | 1.29 | 1.10 |
| Nifty Midcap 100 | 2105 (1368) | 2018-04-03→ | 1.011 [0.907, 1.115] | 0.458 | 1.48 | 1.33 |
| Nifty Bank | 2388 (1590) | | 0.609 [0.520, 0.697] | 0.321 | 1.24 | 1.00 |
| Nifty Fin Services | 2388 (1717) | | 0.635 [0.548, 0.723] | 0.324 | 1.27 | 1.16 |
| Nifty Capital Markets | 513 (199) | 2024-09-16→ | 1.466 [1.318, 1.613] | 0.810 | 1.37 | 1.26 (1.26–1.60) |
| India VIX Δln | 2388 (1541) | | −0.138 [−0.162, −0.114] per unit | −0.280 | −0.17 | −0.16 |
| CDSL | 2289 (623) | 2017-07-03→ | 0.548 [0.471, 0.625] | 0.489 | 0.79 | 0.68 |
| MCX | 2388 (1030) | | 0.410 [0.351, 0.469] | 0.391 | 0.65 | 0.50 |
| Angel One | 1214 (520) | 2021-11-12→ | 0.425 [0.346, 0.505] | 0.418 | 0.63 | 0.57 |
| Nuvama | 750 (616) | 2023-09-27→ | 0.329 [0.244, 0.414] | 0.293 | 0.43 | 0.35 |
| CAMS | 1486 (871) | 2020-10-06→ | 0.407 [0.318, 0.495] | 0.293 | 0.63 | 0.51 |
| KFin Tech | 933 (668) | 2022-12-30→ | 0.339 [0.257, 0.421] | 0.300 | 0.39 | 0.36 |

Benchmark: beta = 1 / zero correlation (an association has no unconditional forecasting benchmark). Status: `descriptive_only`. Notes:

* Dimson (lags −1,0,+1) sum-of-betas is larger than the same-day beta for the broad indices (Nifty 50 1.11 vs 0.89, Next 50 1.10 vs 0.94, Midcap 1.16 vs 1.01), i.e. part of BSE's co-movement with them is spread over adjacent sessions; for Capital Markets it is smaller (1.34 vs 1.47).
* The year-by-year Nifty beta (0.68, 0.38, 0.28, 0.76, 0.97, 1.25, 0.96, 0.92, 1.82, 1.32 for 2017…2026) shows that "beta ≈ 1" is a long-run average of very different regimes. Rolling-250 values at quarter ends: 0.30 (2018-09) … 1.45 (2022-06) … 0.75 (2024-09) … 1.81 (2025-12) … 1.38 now.
* Joint models: BSE on Nifty + Capital Markets (n = 513): Nifty −0.91 [−1.23, −0.59], Capital Markets 1.75 [1.53, 1.96], R² 0.69. The negative Nifty coefficient is an artefact of regressing on a sector index that already carries the market (and BSE); do not read it as an inverse relation. BSE on Nifty + equal-weight peers (n = 1,486 from 2020-10-06): Nifty 0.15 [−0.04, 0.34], peers 0.94 [0.83, 1.05], R² 0.33: once peers are in, the market adds little.
* Gap and intraday parts: BSE G on Nifty gap beta 0.88 (corr 0.51, R² 0.26); BSE I on Nifty open→close beta 0.85 (corr 0.29, R² 0.08).
* Divergence: when |Nifty| ≥ 0.5% (n = 1,221), BSE has the same sign 68.8% of the time (Jeffreys 95% 66.2–71.4% vs 50% under independence); it diverges on the other 31%.
* **Conditional use is validated:** given the same-day Nifty 50 move, a walk-forward beta forecast beats the mean with OOS R² **12.6%** (n_oos 2,138 from 2018-02, halves 16.4% / 10.0%, positive in every year 2018–2026, Holm p < 1e-15); with Capital Markets added OOS R² 64.4% (n_oos 263, from 2025-09). This validates the beta as a scenario mapping (if Nifty moves x, BSE's conditional mean is ≈ β̂x with β̂ re-estimated); it does not forecast the index. Status `validated_out_of_sample` for that conditional claim only.

## 5. (b) Lead-lag and walk-forward prediction

**Cross-correlations** (corr(R_k, x_{k−lag}); lag>0 = x leads BSE; HAC and stationary-bootstrap CIs in the JSON `b1_lead_lag`, 143 cells). Survivors after Holm over 130 cells: CDSL lag −1 r = 0.097 (boot CI 0.056–0.133, Holm p = 0.0018); CDSL lag +1 r = 0.092 (0.052–0.126, Holm 0.00095); Angel One lag −1 r = 0.121 (0.060–0.176, Holm 0.013). Half-sample check: CDSL −1: 0.066 / 0.126; CDSL +1: 0.110 / 0.082; Angel −1: 0.130 / 0.111 (same sign both halves). Lag ±1 same-sign positive values also appear for the Nifty indices (0.03–0.07) but not significantly. Status `descriptive_only` (in-sample).

**Does BSE lead others? (F10, walk-forward of other_k on BSE R_{k−1}, Holm over 13).** CDSL OOS R² +0.74% (Holm p = 0.003), Angel One +0.82% (0.035), Capital Markets index +1.62% (0.009, n_oos only 263 and the HAC coefficient CI includes 0). Nifty 50, Next 50, Midcap, Bank, FinServ, India VIX, MCX, Nuvama, CAMS, KFin: not found. Caveat: sector peers also show positive own-lag autocorrelation (CDSL 0.10, Angel One 0.10, Capital Markets 0.11, KFin 0.09; Nifty −0.04), so a common mechanism (VWAP-based closes, slow sector information diffusion) is as likely as "BSE leads"; the data cannot separate them.

**Does the market/sector lead BSE? (F2/F3 walk-forward)** OOS R² of next-session R: Nifty 50 +0.17% (Holm p = 0.27), Next 50 +0.27% (0.11), Midcap 100 +0.30% (0.32), Bank +0.03%, FinServ +0.03%, Capital Markets −0.27% (n_oos 262), India VIX +0.13% (0.74): **not_found for every index and for the VIX**. Validated (target R): S&P 500 +1.70% (Holm 7e-6), US VIX +0.71% (0.007), BSE's own lag +0.94% (coef 0.105, Holm 0.0045), CDSL +0.71% (coef 0.103, Holm 0.0042), BSE residual vs Nifty +0.57% (0.032), MCX +0.42% (0.045), multivariate [Nifty, India VIX, S&P, US VIX] +1.32% (3e-6). For the gap G: S&P +7.85%, US VIX +7.60%, multivariate +8.75%, BSE's own lag +1.64%, residual +1.49%, USD/INR (prior noon-NY, Δln) +0.91%, CDSL +0.68%. For open→close I: none (4 raw p<0.05, 0 after Holm). Not found: Angel One, Nuvama, CAMS, KFin, US 10y, Brent, [Nifty, India VIX] jointly.

Which of these are one signal? F9 (exploratory, nested vs [1, S&P]): for G, US VIX adds +0.93 pp of OOS R² (Holm 0.0005), BSE's own lag +1.05 pp (0.0018), residual +1.41 pp (0.0003); USD/INR adds nothing (+0.12 pp, Holm 0.48), CDSL and MCX nothing. For R, BSE's own lag (+0.77 pp, Holm 0.010), CDSL (+0.47, 0.017), MCX (+0.37, 0.036) and the residual (+0.61, 0.015) add to S&P, US VIX and USD/INR do not. The USD/INR and US-VIX results are therefore the same global risk-on/risk-off signal as the S&P move; the own-lag/residual/peer results are a second, much smaller, Indian persistence signal.

**Important caveat for the own-lag/peer persistence.** BSE's lag-1 autocorrelation is 0.107 (CI 0.067–0.147) up to 2026-08-02, positive in 9 of 10 years (−0.009 in 2024), but 0.018 (CI −0.26…0.29) in the 50 sessions since the closing auction replaced the 30-minute VWAP close. A VWAP close mechanically pushes the end-of-day drift into the next gap. Whether any of these lagged-Indian-return effects survive the new close definition is untested; the S&P→G relation does not depend on it (auction era n = 49: slope 0.596, CI 0.207–0.985).

## 6. (c) Asymmetry and regimes

* **Up/down beta (R on max(x,0), min(x,0)):** Nifty 50 b_up 0.755 [0.562, 0.949], b_down 1.001 [0.843, 1.160] (n_up 1,286, n_down 1,100); difference up−down −0.246 (CI −0.503…+0.010), raw p = 0.060, Holm p = 0.61, walk-forward asymmetric-vs-symmetric OOS R² +0.06% (Holm 0.65). Bank 0.487 / 0.711 (raw p 0.045, Holm 0.54); FinServ 0.551 / 0.706 (Holm 1.0); Midcap 1.00 / 1.02 (p 0.89). **Capital Markets has the opposite sign**: up 1.687, down 1.223 (raw p 0.038, Holm 0.49). Verdict: `not_found`; signs disagree across indices.
* **Declines:** on 115 sessions with Nifty ≤ −1.5% BSE averaged −2.74% vs Nifty −2.46% (ratio 1.11), within-subsample slope 0.66 [0.49, 0.84] vs 0.81 on other days; BSE fell more than the index on 52% of those days. On 85 Capital Markets decline days the ratio is 1.32 (BSE below the index on 63.5%): a mild amplification vs the sector, `descriptive_only`.
* **Beta in India VIX terciles (ex-ante, expanding thresholds from 2018-02; VIX_{k−1} bounds low 9.2–14.4, mid 11.9–18.9, high 13.7–83.6):** Nifty beta 1.07 [0.64, 1.50] / 1.04 [0.78, 1.30] / 0.85 [0.72, 0.98]; Wald equal-slopes p 0.30 (Holm 1.0), walk-forward interaction model OOS R² −0.41%. Capital Markets beta 1.71 / 1.38 / 1.22 (Wald p 0.012, Holm 0.17; the sample is dominated by the calm tercile). `not_found`.
* **Correlation in stress vs calm:** corr(R, Nifty) 0.49 in the high-VIX tercile vs 0.22 in the low (difference 0.27, bootstrap CI 0.14–0.39, Holm 0.016), but the Forbes–Rigobon correction for the higher index variance gives 0.24, i.e. essentially the calm value; for Capital Markets 0.90 vs 0.78 (corrected 0.83). Reading: apparent contagion is mostly the variance effect; `descriptive_only`.

## 7. (d) Macro sensitivity and the S&P 500 test

**Contemporaneous association (F7, effects in pp of BSE R; "ctrl" = also controlling for same-day Nifty 50):**

| variable (window) | n | per unit | univariate [95% CI] | Holm | with Nifty control [CI] | Holm |
|---|---|---|---|---|---|---|
| S&P 500, prior US session(s) | 2313 | +1% | 0.304 [0.194, 0.414] | 8e-7 | 0.081 [0.003, 0.160] | 0.42 |
| US VIX Δln, prior | 2346 | +10% | −0.288 [−0.428, −0.147] | 7e-4 | −0.039 [−0.166, 0.088] | 1.0 |
| US 10y, prior | 2297 | +10 bp | 0.020 [−0.189, 0.229] | 1.0 | 0.046 [−0.128, 0.221] | 1.0 |
| USD/INR Δln, prior (noon NY d−1) | 2285 | +1% | −0.425 [−0.739, −0.111] | 0.088 | −0.205 [−0.469, 0.059] | 1.0 |
| USD/INR Δln, same date (association only) | 2281 | +1% | −0.968 [−1.308, −0.627] | 4e-7 | −0.015 [−0.317, 0.286] | 1.0 |
| Brent spot Δln, prior | 2332 | +10% | 0.222 [−0.078, 0.521] | 1.0 | 0.199 [−0.075, 0.473] | 1.0 |
| Brent spot Δln, same date | 2331 | +10% | 0.223 [−0.160, 0.606] | 1.0 | −0.005 [−0.290, 0.280] | 1.0 |

The rupee and the US VIX are associated with BSE only through the Nifty move (the effects vanish under the Nifty control). The same-date USD/INR association (−0.97 pp per +1%) is the largest, but the H.10 noon-NY rate partly postdates the Indian close and reflects Indian equity flows too; it is not causal and not usable for prediction. The US 10-year yield and Brent show no association in daily data (the Brent spot series includes a +16.6% log one-day jump on 2026-10-02, which is in the sample).

**PRIMARY test: previous US session S&P 500 return → BSE's next Indian-session gap G and close-to-close R.** x = S&P 500 log return over US sessions dated in [d_{k−1}, d_k); n = 2,313 of 2,388 sessions (75 sessions lack a US session in their window); sd(x) = 1.15%.

| | G (opening gap) | R (close-to-close) |
|---|---|---|
| full-sample slope per +1% S&P [HAC 95% CI] (n_eff) | **0.276 [0.215, 0.337]** (882) | **0.304 [0.194, 0.414]** (1,593) |
| in-sample R² | 8.1% | 1.8% |
| robustness: ex 2020-02-20..04-30 / winsorised 1–99% | 0.305 [0.240, 0.369] / 0.316 [0.261, 0.371] | 0.311 / 0.356 |
| chronological split: train 2017-02-06→2022-12-30 (n 1,415) slope | 0.232 [0.179, 0.285] | 0.265 [0.148, 0.383] |
| test 2023-01-02→2026-10-13 (n 898): refit slope | 0.416 [0.270, 0.563] | 0.420 [0.184, 0.656] |
| split OOS R² with fixed train coefficients vs train mean; CW t, Holm p | **+6.79%**; 3.73; 1.9e-4 | **+1.34%**; 3.03; 1.2e-3 |
| walk-forward (expanding, min 500) OOS R² (n_oos 1,813 from 2019-03-11); CW t; Holm p | **+7.85%**; 6.39; 3e-10 | **+1.70%**; 4.98; 9e-7 |
| WF OOS R² first / second half | 8.7% / 7.1% | 2.1% / 1.4% |
| WF OOS R² by year | 2019 −5.1%, 2020 7.4, 2021 7.5, 2022 17.6, 2023 8.1, 2024 2.3, 2025 10.2, 2026 11.8 | 2019 0.3, 2020 3.9, 2021 −0.5, 2022 4.2, 2023 1.3, 2024 −0.4, 2025 1.4, 2026 6.3 |
| slope by calendar year | 0.357, 0.209, 0.030, 0.220, 0.333, 0.288, 0.288, 0.311, 0.431, 0.681 (2017…2026; positive 10/10) | 0.204, 0.153, 0.071, 0.299, −0.038, 0.384, 0.377, −0.029, 0.384, 1.091 (positive 8/10) |
| slope by chronological thirds | 0.178 / 0.291 / 0.454 | 0.228 / 0.343 / 0.382 |
| slope stability test (test minus train) | +0.184, p = 0.021 | +0.155, p = 0.25 |
| **status** | **validated_out_of_sample** | **validated_out_of_sample** |

Benchmark: expanding / train mean of the same target. Positive control: the same regression on Nifty 50's own opening gap gives slope 0.290 [0.236, 0.343], in-sample R² 25.7%, split OOS R² +22.7%, stable between train and test (diff −0.003, p = 0.94), so the alignment and the transmission are real. Placebos: G on the S&P window shifted back one more session −0.043 (CI −0.089…+0.002); open→close I on the prior S&P window 0.028 (−0.075…0.132, p = 0.59), i.e. the information is fully in the opening price; S&P dated d_k (after the Indian open) vs G 0.060 (0.012–0.107) and vs R 0.234, which reflects shocks shared across markets and is never used. G averaged +0.31% when |S&P|≤1% (n 1,730), −0.39% after S&P < −1% (n 264), +0.70% after S&P > +1% (n 319).

Exceptions: 2019 (slope 0.03 for G, OOS R² −5.1%), 2021 and 2024 for R (slopes ≈ 0, wide CIs); the slope has risen over time, so the full-sample coefficient probably understates the current sensitivity. The effect is not independent of GIFT Nifty / Asian-session information that I could not obtain: the S&P move may mostly proxy for those.

## 8. (e) Idiosyncratic variance share (1 − R², bootstrap 95% CI)

| model | n | full | by year (2017-19 / 20 / 21 / 22 / 23 / 24 / 25 / 26 YTD) | 2025→ | last 250 | last 120 |
|---|---|---|---|---|---|---|
| R ~ Nifty 50 | 2388 | **87.5%** (83.1–91.5) | 94.9 / 69.0 / 89.7 / 77.4 / 95.2 / 94.8 / 82.8 / 74.1 | 80.7% (72.3–87.2) | 75.9% (61.6–90.0) | 92.8% |
| R ~ Nifty 50 + peers (EW) | 1486 (2020-10-06→) | 67.3% (61.4–72.9) | – / 69.4 / 64.9 / 60.9 / 81.6 / 73.7 / 56.4 / 61.4 | 58.7% | 61.0% | 86.3% |
| R ~ Nifty 50 + Capital Markets | 513 (2024-09-16→) | 31.2% (26.5–36.2) | 2024 30.2 / 2025 28.2 / 2026 33.5 | 30.2% | 33.7% | 52.5% |
| G ~ Nifty gap | 2388 | 73.6% (63.5–81.6) | | 47.4% | 43.5% | 50.2% |
| I ~ Nifty open→close | 2388 | 91.5% (88.6–94.1) | | 85.1% | 83.7% | 94.6% |

The ten largest residual days account for 14.5% of the full-sample residual sum of squares (27% in 2025→); the idiosyncratic risk is fat-tailed. The Capital Markets figure (31%) is not comparable with the others because BSE is a constituent. The gap component has become much more market-driven since 2025 (idiosyncratic share 47% vs 74% over the full sample), consistent with a rising S&P→G slope.

## 9. Live state for 14 Oct and what it implies

* 13 Oct: BSE R = +1.35% (G +0.05%, I +1.29%) vs Nifty 50 +1.59%, Capital Markets +0.51%, Midcap +1.06%, India VIX −7.7%; CDSL +2.03%, Angel One +2.53%, CAMS +3.18%, KFin +2.72%, MCX −2.45%, Nuvama −3.32%. BSE's residual vs Nifty with the trailing-250 beta (through 12 Oct) is −0.86%; vs Capital Markets +0.71%. BSE moved with the market and sector on 13 Oct; no outsized divergence.
* US (Yahoo, unofficial): S&P 500 7,797.72 at 16:17:42 UTC vs 7,807.24 (−0.122%); VIX 15.42 (16:02:31 UTC) vs FRED's 12-Oct close 15.21 (+1.37% log); ES future 7,841.75 vs prior settle 7,858.0; US 10y 5.223% vs 5.240%; Brent front future 105.99 vs 106.65 (FRED's spot series ended 6 Oct at 125.44, so futures and spot are not comparable here); USD/INR 95.27 (14:18 UTC) vs 95.76, ECB 95.28 vs 95.78: the rupee strengthened ≈0.5% on 13 Oct. The 13-Oct US session ends after the cutoff, so these are partial.
* Per-predictor shifts of the conditional mean for 14 Oct (full-sample OLS, relative to the sample mean of x; predictors in the same group overlap, do not add them): G: S&P −0.048 pp, US VIX −0.053 pp, BSE own lag +0.068 pp, residual −0.057 pp, CDSL +0.079 pp; R: S&P −0.053, CDSL +0.198, MCX −0.192, BSE own +0.127, residual −0.091, US VIX −0.039. The sums nearly cancel. Recommendation: **a gap-centre shift of about −0.05 pp (validated S&P rule) with the −0.16 pp exploratory composite as the lower bound; no change to the close-to-close centre.** Neither is large against σ_G = 1.1% and σ_R = 2.5%. The USD/INR rupee-strength signal (G +0.19 pp) is not incremental to S&P (Holm 0.48) and its FRED definition (noon NY) does not match the ≈19:50 IST Yahoo print, so I do not use it.
* Market-state read-through: with beta to Nifty somewhere between 0.8 and 1.4 and 76–88% idiosyncratic variance, the market view explains little of tomorrow's range; BSE's own volatility model (v1) remains the right scale. Any scenario "Nifty moves x%" maps to a BSE conditional mean of about β̂x (β̂ from the last 250 sessions = 1.38, with the 0.75 last-120 value as the low case), and the conditional-forecast OOS R² of 12.6% means a Nifty move still leaves ≈87% of the variance unexplained.

## 10. Pattern ledger (definition, n, period, benchmark, exceptions, CI/p, status)

The full machine-readable ledger with 103 entries (all betas, every Holm-surviving lead-lag cell, every walk-forward predictor for R and G, F10, F6, F7, F8, E) is `patterns` in the JSON. Headline entries:

| pattern | n (n_eff) | period | benchmark | estimate [CI] | adj. p | exceptions | status |
|---|---|---|---|---|---|---|---|
| BSE beta to Nifty 50 (same day) | 2388 (1543) | 2017-02→2026-10 | β = 1 | 0.89 [0.77, 1.01] | – | yearly 0.28–1.82; roll-250 0.27–1.96 | descriptive_only |
| Conditional beta forecast given same-day Nifty | 2138 (1228) | 2018-02→ | expanding mean | OOS R² 12.6% | Holm <1e-15 (F5) | worst year 2019 (2.0%) | validated_out_of_sample |
| BSE beta to Capital Markets | 513 (199) | 2024-09→ | β = 1 | 1.47 [1.32, 1.61], corr 0.81 | – | BSE is a constituent (34–51% of covariance mechanical) | descriptive_only |
| Idiosyncratic share vs Nifty | 2388 | full | 100% | 87.5% [83.1, 91.5] | – | 69% (2020) to 95% (2023) | descriptive_only |
| Lead-lag CDSL ±1, Angel One −1 | 2289 / 1214 | | zero corr | 0.097 / 0.092 / 0.121 | Holm 0.0018 / 0.0009 / 0.013 | none at lags 2–5; no index lag survives | descriptive_only |
| BSE return predicts next-day CDSL / Angel One / Capital Markets | 1789 / 964 / 263 | | expanding mean | OOS R² 0.74 / 0.82 / 1.62% | Holm 0.003 / 0.035 / 0.009 | peers also autocorrelated; VWAP-era | validated_out_of_sample (weak) |
| Lagged Nifty / Next 50 / Midcap / Bank / FinServ / Capital Markets / India VIX → BSE R | 1604–1887 | 2019-02→ | expanding mean | OOS R² −0.27…+0.30% | Holm 0.11–1.0 | – | not_found |
| CDSL / MCX / BSE own lag / residual → next R | 1788 / 1887 / 1887 / 1767 | 2019→ | expanding mean | OOS R² 0.71 / 0.42 / 0.94 / 0.57% | Holm 0.004 / 0.045 / 0.005 / 0.032 | VWAP-close era; auction-era n = 50 untested | validated_out_of_sample (tiny) |
| S&P 500 prior session → G | 2313 (882) | 2017-02→2026-10 | train / expanding mean | 0.276 [0.215, 0.337]; OOS R² 7.85% WF, 6.79% split | Holm 3e-10 / 2e-4 | 2019 fails; slope 0.18→0.45 over thirds | validated_out_of_sample |
| S&P 500 prior session → R | 2313 (1593) | same | same | 0.304 [0.194, 0.414]; OOS R² 1.70% / 1.34% | Holm 9e-7 / 1.2e-3 | 2021, 2024 slopes ≈ 0 | validated_out_of_sample |
| US VIX, USD/INR (prior) → G | 1846 / 1785 | 2019-03→ | expanding mean | OOS R² 7.60% / 0.91% | Holm 3e-11 / 0.009 | not incremental to S&P for USD/INR; VIX adds 0.9 pp | validated_out_of_sample (same global signal) |
| US 10y, Brent → BSE | 1797 / 1832 | | expanding mean | OOS R² −0.14% / −0.04% | Holm 1.0 | – | not_found |
| Asymmetric (down>up) beta vs Nifty | 2388 | | symmetric | −0.25 [−0.50, +0.01] | Holm 0.61 | opposite sign vs Capital Markets | not_found |
| Beta differs by VIX tercile | 2139 | 2018-02→ | constant beta | 1.07 / 1.04 / 0.85 | Wald Holm 1.0 | – | not_found |
| Correlation higher in stress | 1497 | | calm | 0.49 vs 0.22 → FR-corrected 0.24 | Holm 0.016 (raw diff) | variance artefact | descriptive_only |

## 11. Contrary evidence and what would reverse each conclusion

* **S&P→G validated.** Against: the slope is unstable (0.03 in 2019, 0.68 in 2026), the 2019 OOS R² is negative, the relation may be a proxy for GIFT Nifty/Asian information I could not observe, and the live input is a partial-session value. Reverses if: the 14-Oct gap shows no relation across the next ~60 sessions (auction era n = 49 currently supports it: 0.60 [0.21, 0.99]), or an overnight Nifty-futures regressor absorbs the S&P coefficient.
* **Own-lag / peer persistence validated.** Against: effect sizes below 1% of variance, likely tied to the VWAP close; the auction-era autocorrelation is 0.018; peers show the same persistence, which argues against BSE-specific leadership. Reverses if the auction-era sample (50 sessions now) stays near zero over the next 100–200.
* **No lead over indices / no asymmetry.** Power is limited: for a 50/50 split of n ≈ 1,100–1,300 sessions the difference of two betas has SE ≈ 0.13, so effects below ≈ 0.25–0.3 cannot be excluded (the observed 0.25 up/down gap is borderline). "Not found" is not "absent". Capital Markets asymmetry and VIX-regime tests rest on only 513 sessions in a mostly calm period.
* **Beta ≈ 1 / idiosyncratic 87%** are averages across very different years; if the 2025–26 regime (beta 1.4–1.5, idiosyncratic share 76–81%) is the relevant one, the market matters more than the full-sample numbers suggest.
* **Macro:** the oil and rate tests use FRED spot/CM series that stop 5–7 sessions before the cutoff and cannot capture the live shocks; a null for Brent (+16.6% log on 2026-10-02) in daily data does not rule out event-driven sensitivity.

## 12. Gaps (what is missing and its effect)

* GIFT Nifty/SGX, Asian indices and Nifty option overnight pricing: not obtained; the S&P effect may be partly redundant, and the intraday-S&P partial number is the only US information at the cutoff.
* US 10y, Brent, USD/INR through 13 Oct from official series: unavailable (stale 3–7 sessions); live quotes used for context only.
* NIFTY Capital Markets weights: unverified (PDF not opened). The mechanical-overlap share (34–51%) is conditional on 15–23%.
* Intraday S&P path and its relation to the final close: only 5-minute snapshots from an unofficial source; no estimate of how the remaining 3h13m will change the 13-Oct move (zero mean assumed).
* Closing-auction era (since 2026-08-03) has 50 sessions: no test of whether lagged-Indian-return effects survive the change.
* HAC treats the non-contiguous rows left after NaN removal (peers' early gaps, post-US-holiday sessions) as adjacent; the effect is small (at most 4.3% of rows for the macro windows).

## 13. Reproduction

`cd /home/user/pred_18 && PYTHONPATH=src python3 src/behaviour/linkages.py` regenerates `results/behaviour/linkages.json` (≈ 25 s). I independently recomputed the S&P windows (naive loop), the S&P→G and S&P→R slopes, the walk-forward OOS R² (refit by `lstsq` each step: G 0.07851, R 0.01698, identical to the rank-one-update engine) and the Nifty beta/correlation with separate code (a throw-away script kept in the session scratchpad, not committed); all agree to 4 decimals except the iid CW t-statistic (6.98 vs the HAC 6.39 reported).
