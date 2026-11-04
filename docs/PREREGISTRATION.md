# Pre-registration v1.0 — NSE:BSE next-session forecast (target session 2026-10-14)

Written 2026-10-13 ≈ 15:55 IST, **before** any return-distribution statistic, backtest, GARCH fit, regression or
episode study for BSE Ltd had been computed. Everything below is a commitment; any later deviation is logged in
`docs/DEVIATIONS.md` with a reason and a note of whether results of the affected model had already been seen.

## 0. Peeking log (what had been seen before writing this)
* Last five daily bars of NSE:BSE (7–13 Oct 2026) from stockanalysis.com; the 12-Oct-2026 NSE bhavcopy rows for BSE and peers.
* 12-Oct-2026 index closes (Nifty 50 22,363.35, India VIX 15.25, Nifty Capital Markets +1.5%).
* One search snippet: BSE closed ₹3,447 on 14 Aug 2026; 52-week high ₹4,446.8.
* The F&O bhavcopy for 12 Oct 2026 was opened to check that BSE option strikes exist (no volatility computed yet).
* Nothing else. No historical returns, volatilities or correlations for BSE had been computed.

## 1. What is forecast
* Stock: BSE Ltd, NSE symbol `BSE`, series EQ, ISIN INE118H01025, INR, exchange timezone Asia/Kolkata (UTC+5:30).
* Reference price **P0** = official NSE close of 2026-10-13 from `sec_bhavdata_full_13102026.csv` (the file is not yet published at
  writing; provisional 3,375.40 per Google Finance and stockanalysis.com stamped 15:28–15:30 IST). If the official close differs from
  3,375.40, every price in the forecast is re-expressed from the official P0 using the *return* forecasts (return forecasts do not change).
* Target session **T = Wed 2026-10-14** (09:15–15:30 IST), subject to holiday confirmation.
* Targets (log returns vs P0): G = ln(O_T/P0) opening gap; I = ln(C_T/O_T) open-to-close; R = G+I close-to-close;
  H′ = ln(H_T/P0), L′ = ln(L_T/P0); ρ = ln(H_T/L_T) daily range.
* Information set: data published up to and including the T−1 session close only (OHLCV, indices, VIX, breadth, F&O EOD).
  Overnight/global/news information after the T−1 close is **unknown** at forecast time and is treated as noise that the
  gap distribution must absorb; it is not conditioned on.

## 2. Sample and splits
* NSE:BSE sessions from 2017-02-06 (listing day 2017-02-03 excluded: IPO-price base) to the latest published session.
* Walk-forward, expanding window, every forecast uses data strictly before the forecast session.
  First forecast after 500 sessions of history (≈ Feb 2019).
* Periods (used only for model *selection* and reporting; parameters are always estimated on data before each forecast):
  * **Development**: first forecast → 2024-06-28
  * **Validation**: 2024-07-01 → 2025-06-30
  * **Final test**: 2025-07-01 → latest published session at run time. Run **once**; all candidates reported, not only the winner.
* Regime slices reported: pre-COVID (≤2020-02-19), COVID (2020-02-20→2020-12-31), 2021–2022, 2023, 2024, 2025-onward;
  and high/low volatility halves by trailing-60d realised vol rank.

## 3. Candidate models (complete list; nothing may be added after seeing results without a DEVIATIONS entry)
Scale (σ_t) models for R, and separately for G and I:
| id | description |
|---|---|
| S0 `hist` | benchmark: expanding-sample std (“historical average”, no volatility timing) |
| S1 `ewma94` | RiskMetrics EWMA λ=0.94 on squared returns, zero mean |
| S2 `garch_t` | GARCH(1,1), Student-t, zero mean, refit every 20 sessions on trailing ≤1,500 sessions (`arch`) |
| S3 `gjr_t` | GJR-GARCH(1,1,1), Student-t, same schedule |
| S4 `har_gk` | HAR (daily, 5d, 22d means) on log of v_t = G_t² + Garman–Klass(O,H,L,C)_t; OLS expanding; refit every 20; Duan smearing |
| S5 `har_x` | S4 + ln VIX_{t−1}, Nifty 5-day realised vol, BSE log-turnover z-score (60d), Nifty |ret|_{t−1}; OLS |
| S6 `blend` | geometric mean of S2 and S4 σ |
Predictive distribution for every scale model: **location × scale × empirical quantiles of the trailing 500 standardised
residuals** (filtered historical simulation), so models differ only in σ_t. Quantile grid {0.05,0.10,0.25,0.50,0.75,0.90,0.95}.

Location models:
| id | description |
|---|---|
| L0 `zero` | median/location fixed at 0 (“unchanged price” benchmark) |
| L1 `hist_mean` | expanding mean of R |
| L2 `ridge` | ridge on σ-standardised return; features below; α ∈ {1,10,100,1000} selected on Development only, then frozen |
| L3 `logit` | L2-logistic for 1{R>0}; C ∈ {0.01,0.1,1} selected on Development only, then frozen |
Features (all measured at T−1 close): R_{t−1}, R_{t−2}, 5d/20d/60d cumulative return, I_{t−1}, G_{t−1} (each ÷ σ_{t−1}),
Nifty 50 R_{t−1}, Nifty Capital Markets R_{t−1} (when available), BSE return minus rolling-β×Nifty, Δln VIX_{t−1}, VIX percentile (trailing 500),
BSE log-turnover z (60d), market advance share_{t−1}, day-of-week dummies, distance to 20d and 50d mean (÷σ), RSI(14).
Delivery % is **excluded** from L2/L3 (only exists from late 2019); examined separately post-2020 as a secondary analysis.
Group ablations (momentum / market / technical / calendar) are reported.

Range model: HAR on log(ρ_t) with the same FHS machinery vs benchmark trailing-250d empirical quantiles of ρ.

## 4. Metrics, tests and the gates that decide what is used
* Interval/quantile quality: coverage of 50/80/90/95% central intervals with Kupiec (UC) and Christoffersen (independence) tests;
  mean pinball loss over the grid; mean interval width.
* Pairwise comparison vs benchmark: Diebold–Mariano on pinball loss (Newey–West, 5 lags); QLIKE on v_t proxy for σ² as secondary.
  Family-wise caution: Holm correction across the 6 non-benchmark scale models.
* Location: out-of-sample R² vs L1 (Campbell–Thompson), Clark–West p, directional accuracy vs base-rate with exact binomial test, AUC, Brier score
  and 5-bin reliability for P(up).
* **Gate for using a scale model other than S0 in the live forecast**: lowest mean pinball loss on Development+Validation pooled among S1–S6
  (ties → simpler). Its Final-test results are reported regardless of outcome. If it fails to beat S0 on the Final test (DM one-sided p ≥ 0.10)
  the forecast is still produced from it but the record states “no demonstrated advantage over benchmark on unseen data”.
* **Gate for using a location model other than L0**: on Validation+Final pooled, OOS R² > 0, Clark–West one-sided p < 0.05, directional accuracy
  above base-rate with binomial p < 0.05, and the result survives dropping the 5 largest |R| sessions. Otherwise L0 is used, and P(close>P0) is
  taken from the (location-0) empirical standardised distribution and labelled as *not* a validated directional claim.
* Calibration check: if the selected model’s Final-test 90% coverage differs from 0.90 with Kupiec p < 0.05, the live intervals are widened/narrowed by
  the scalar that restores Final-test coverage, and that scalar is disclosed.
* Statistical power is stated explicitly: with ≈320 Final-test sessions a true 53% hit-rate is detectable with ≈15% power.
  “Not detected” never means “no effect”.

## 5. Episode study (selection rules fixed now; outcomes not viewed)
* E1 market stress day: Nifty 50 close-to-close ≤ −2.5%.
* E2 fear regime: India VIX close ≥ 25; consecutive days (gap ≤ 5 sessions) merged into one episode.
* E3 correction regime: Nifty 50 ≥ 10% below its trailing 250-day closing high.
* E4 stock shock: |R_BSE| ≥ 8%, or |R_BSE − β̂·R_Nifty| ≥ 3 × trailing-60d residual SD (β̂ from trailing 120d, excluding the event day).
* E5 results days: BSE Ltd quarterly-results announcement dates from the company/exchange record (dossier), reaction = first session able to trade on the news.
* Metrics: R and market/sector-relative excess return, next-day |R|/σ̂, 5d & 20d cumulative return, turnover multiple vs trailing 60d, sessions to recover the
  pre-event close, share with next-day R>0. Report n, medians with bootstrap 90% CIs. No event is dropped after seeing outcomes.

## 6. Live forecast record (schema fixed now)
`results/forecast_record_2026-10-14.json`: stock, cutoff timestamp, P0 (+source), target session, model ids chosen, quantile table for G, I, R, H′, L′, ρ,
P(R>0), P(|R|<0.25σ) (“broadly unchanged” = |R| < 0.25 × forecast σ_R, defined now), scenario probabilities (explicitly subjective unless validated),
invalidation conditions, git commit hash of the code, and SHA-256 of the processed datasets. `src/score_forecast.py` scores it after the session without edits.

## 7. Non-goals / honesty clauses
* No trading-profit claims. No minute-level data, order book, short-interest or dealer positioning is available; none will be inferred.
* Intraday *path* statements are conditional descriptions built from daily OHLC frequencies only.
* If no location model passes its gate the answer to “which direction?” is: **there is insufficient evidence for a reliable directional forecast**.
