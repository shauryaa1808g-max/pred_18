# Independent verification of v2 workstream "linkages" (research/v2/03_market_linkages.md)

Verifier run on the 2026-10-14 sandbox clock; information cutoff stays 2026-10-13 22:00 IST.
Scope: re-derive the main numbers from the raw/processed data without importing the analyst's code, audit look-ahead, definitions, multiple testing and labels, and test the lead's points (a), (b), (c).

**Integrity statement.** I used only repository files dated on or before 2026-10-13 (`data/processed/*.csv`, `data/raw/macro/SP500.csv`, `VIXCLS.csv`, `DGS10.csv`, `DCOILBRENTEU.csv`, `DEXINUS.csv`). I fetched nothing, ran no fetch script, did not refresh `data/raw/macro`, opened no web page, and did not look at any BSE price, volume or headline for 14 Oct. I was not exposed to post-cutoff content. The analyst's code was read only after my re-implementation, to diagnose differences. Verifier scripts are in the session scratchpad (`.../scratchpad/ver/*.py`), not in the repo.

## 0. Verdict

* **All headline numbers replicate** (to 3-4 significant digits, differences explained by one first-session row). The time alignment of the S&P 500 test is correct. The S&P -> opening-gap result is genuinely out-of-sample, survives the stricter frozen-v1 window gate, and is not an artefact of the close definition.
* **The labels on the secondary "Indian persistence" claims are overstated.** BSE's own lagged return, the residual vs Nifty, CDSL, MCX and "BSE leads CDSL / Angel One / Capital Markets" are labelled `validated_out_of_sample` for next-session R, but (i) in the frozen-v1 Validation+Final windows the own-lag and residual OOS R2 are **-0.70% / -0.69%** (CW p 0.30 / 0.40), (ii) the unadjusted Diebold-Mariano p for the own lag is 0.099, (iii) the peers add nothing once BSE's own lag (or the target's own lag) is controlled, (iv) pooled across families two of the five fall to Holm p 0.34-0.61. Recommended label: `descriptive_only` for R; the same predictors for the gap G do pass the v1 windows.
* **The report's explanation of the weakness (VWAP close mechanically creates the autocorrelation) is not supported.** Autocorrelation of last-traded-price returns is 0.094 vs 0.107 for VWAP-close returns, and the lag -> gap link in the 50 auction sessions is +0.19 (not smaller). The auction-era drop of ac1 to 0.018 is statistically indistinguishable from noise (interaction t = -0.90).
* **Two statements in the report are wrong as written**: "every label below that is validated also passes the strict gate" (false for F10 CDSL and Angel One; first-half OOS R2 negative) and the description of the strict gate as "v1-style" (the v1 gate in `docs/PREREGISTRATION.md` s4 is evaluated on Validation+Final pooled and also needs a directional-accuracy test).
* Effect on the 14 Oct forecast: small. The analyst already recommends no change to the R centre and only about -0.05 pp (up to -0.10 pp with the recent slope) on the gap centre; my work supports both.

Overall severity: **minor** (numbers right; labels and one mechanism claim overstated; nothing that moves the forecast).

## 1. Re-implementation vs report (independent code, same data)

| claim | report | mine | note |
|---|---|---|---|
| S&P -> G slope per +1% (HAC CI), n, n_eff | 0.2757 (0.2145-0.3368), 2313, 882.4 | 0.2755 (0.2144-0.3366), 2312, 882.5 | n differs by the first session (needs 2017-02-03 S&P window) |
| S&P -> G in-sample R2 | 8.14% | 8.13% | |
| S&P -> G walk-forward OOS R2, CW t, n_oos | 7.85%, 6.39, 1813 | 7.85%, 6.40, 1812 | min train 500, expanding mean benchmark |
| S&P -> G fixed split (train <= 2022) OOS R2, CW t | 6.79%, 3.73 | 6.79%, 3.73 | |
| S&P -> G OOS R2 by year 2019..2026 | -5.1, 7.4, 7.5, 17.6, 8.1, 2.3, 10.2, 11.8 | -5.0, 7.4, 7.5, 17.6, 8.1, 2.3, 10.2, 11.8 | |
| S&P -> R slope, WF OOS R2, split OOS R2 | 0.304, 1.70%, 1.34% | 0.305, 1.70%, 1.34% | |
| S&P slope by year (G) | 0.357 ... 0.681; 10/10 positive | 0.347, 0.209, 0.030, 0.220, 0.333, 0.288, 0.288, 0.311, 0.431, 0.681 | 2017 differs only by the first row |
| auction-era S&P -> G slope | 0.596 (0.207-0.985), n 49 | 0.596 (0.207-0.985), n 49 | |
| Nifty 50 beta, corr, n_eff | 0.892 (0.774-1.010), 0.354, 1543 | 0.893 (0.775-1.011), 0.355, 1536 | n = 2387 vs 2388 (first row) |
| rolling-250 beta now / range; last-120 | 1.38 / 0.27-1.96; 0.75 | 1.39 / 0.267-1.961; 0.745 | |
| idiosyncratic share full / 2025+ / last 250 | 87.5 / 80.7 / 75.9% | 87.4 / 80.7 / 75.9% | |
| lead-lag family: cells, raw p<0.05, Holm survivors | 130, 16, 3 | 130, 16, 3 | identical Holm p: 0.00095, 0.00185, 0.0131 |
| CDSL +1 / -1, Angel One -1 | 0.092 / 0.097 / 0.121 | 0.0915 / 0.0971 / 0.1207 | |
| own-lag WF OOS R2 (R), CW t | +0.94%, p Holm 0.0045 | +0.941%, t 3.51, raw p 2.3e-4 (x23 = 0.0052) | |
| BSE ac1: VWAP era / auction era | 0.1067 / 0.0176 | 0.1067 / 0.0176 (within-era lag) | with the lag taken across the boundary the auction-era value is -0.007 |
| Capital Markets beta, corr, n | 1.466 (1.318-1.613), 0.81, 513 | 1.465 (1.317-1.613), 0.809, 513 | |
| mechanical overlap, w = 15.1% / 22.9% | 34% / 51% | 33.8% / 51.2% | same identity |
| conditional (same-day Nifty) WF OOS R2 | 12.6% | 12.57% (CW t 8.29) | |
| up/down beta; diff; raw p | 0.755 / 1.001; -0.246; 0.060 | 0.757 / 1.002; -0.246; 0.061 | |
| VIX-tercile betas; Wald p; Forbes-Rigobon corr | 1.07/1.04/0.85; 0.30; 0.24 | 1.07/1.04/0.85; 0.32; 0.239 | |
| sign agreement when abs(Nifty) >= 0.5%; top-10 residual share | 68.8%; 14.5% | 68.9%; 14.5% | |
| US 10y, Brent OOS R2 (R) | -0.14%, -0.04% | -0.14%, -0.03% | not found, confirmed |
| live gap adjustment: partial S&P; full / last-250 slope | -0.122%; -0.048 / -0.102 pp | -0.1220%; -0.0482 / -0.1022 pp | arithmetic confirmed |
| 13 Oct BSE R, G, I; peers' 13 Oct returns | +1.35 / +0.05 / +1.29 %; CDSL +2.03, MCX -2.45, Angel +2.53, Nuvama -3.32, CAMS +3.18, KFin +2.72 | identical (from `bse_daily.csv`, `peers_daily.csv`) | |

Not independently verifiable by me without fetching: the 13 Oct index row (NSE `ind_close_all_13102026.csv`) and the live Yahoo S&P/VIX/ES quotes. The Nifty close 22,721.95 is corroborated by other workstreams (research/02 cites a Yahoo feed 22,721.94; research/v2/02 cites the same NSE file). Its effect on the full-sample beta is nil (0.8932 -> 0.8931).

## 2. Point (a): S&P 500 -> opening gap, time alignment

* Alignment rule re-derived: US observations dated in [d_{k-1}, d_k) all finish (20:00/21:00 UTC) before the Indian open of d_k (03:45 UTC). Code and report agree; I found no look-ahead. Dropped sessions (76 incl. the first): 45 Tuesdays (US Monday holidays), 13 Fridays, 10 Mondays (one is the first session), 5 Thursdays, 3 Wednesdays.
* **Lag profile** (window of session k+s used for G_k; s = 0 is the stated alignment), HAC t of the slope:
  G: s=-4..-1: 1.4, -0.8, 0.2, -1.9; **s=0: 8.8 (slope 0.276, R2 8.1%)**; s=+1..+4: 2.1, 0.1, 0.7, -0.9. Neighbouring windows give R2 <= 0.25%.
  R (close-to-close): s=0 t 5.4; s=+1 (US session dated d_k, after the Indian close) t 3.8, slope 0.205 (common-shock association, correctly never used); all other shifts |t| < 1.8.
  I (open-to-close): s=0 slope 0.029 (t 0.6): the information is fully in the opening price.
* Deliberately mis-aligned placebos: same-calendar-date merge (the classic error) G slope 0.04 (R2 0.2%) and R 0.214; "last US obs on or before d_k - 1" (re-uses stale returns on holidays) 0.271 (similar, as expected since it differs from the correct rule only on the 3% holiday sessions).
* **Circular-shift null** (200 random offsets of the S&P series against BSE, same walk-forward engine): OOS R2 mean -0.05%, sd 0.07%, max +0.23% vs actual +7.85%.
* Holiday handling: slope with one US session in the window 0.269 (n 2194), with two or more (after Indian holidays) 0.328 (n 118); Mondays 0.311; Tuesday-Friday single 0.255. No alignment-driven heterogeneity.
* Close-definition independence: the gap measured from the last traded price instead of the VWAP close gives slope 0.268 and WF OOS R2 7.79% (VWAP-close gap 0.274, 7.80%), VWAP era only.
* **v1-window gate** (Validation 2024-07..2025-06, Final 2025-07..2026-10-13, pooled): S&P -> G OOS R2 Val +9.0%, Final +10.1%, pooled +9.4% (CW p 6e-4); S&P -> R Val +1.7%, Final +2.6%, pooled +2.0% (p 9e-4). Both pass. **Verdict: `validated_out_of_sample` is warranted for S&P -> G and S&P -> R.** Unadjusted DM test (no Clark-West correction): G t 4.9, R t 3.3.
* Caveats I confirm: slope is not stable (below); partial-session regressor. The remainder of the 13 Oct US session (about 3h13m) has sd about 0.8%, i.e. +/-0.22 pp on G with the full-sample slope and +/-0.48 pp with the last-250 slope. The analyst says this "adds variance, not bias"; correct, but the added spread is 4% (full slope) to 18% (recent slope) of var(G), larger than the shift itself (-0.05 / -0.10 pp), and the report does not quantify it.

## 3. Point (b): own lagged return, by close regime, calendar year and v1 windows

Own lag -> next R (walk-forward, min train 500, expanding-mean benchmark; my numbers equal the report's):

| window | n_oos | OOS R2 | note |
|---|---|---|---|
| all 2019-02..2026-10-13 | 1887 | +0.94% | CW t 3.51 (p 2.3e-4); unadjusted DM t 1.29 (p 0.099); block-bootstrap 95% CI of the OOS R2 [-0.52%, +2.26%] |
| Development ..2024-06-28 | 1321 | **+1.88%** | CI [+0.32%, +3.14%] |
| Validation 2024-07-01..2025-06-30 | 248 | **-0.71%** | |
| Final 2025-07-01..2026-10-13 | 318 | **-0.68%** | |
| Validation+Final pooled (the v1 gate window) | 566 | **-0.70%** | CI [-3.67%, +2.00%]; CW p 0.30 |
| by year 2019..2026 | | +1.74, +0.93, +1.28, +1.92, **+4.87**, -1.95, +0.46, +0.85 | 2023 alone is a quarter of the pooled gain |
| VWAP era (to 2026-08-02) | 1837 | +0.97% | |
| closing-auction era (from 2026-08-03) | 50 | -1.02% | meaningless at n = 50 |

Lag-1 autocorrelation of R by year 2017..2026: 0.064, 0.095, 0.146, 0.111, 0.104, 0.147, 0.223, **-0.009**, 0.080, 0.095. VWAP era 0.107 (n 2337); auction era +0.018 (within-era lag) or -0.007 (lag across the boundary), SE about 0.14.

**Reconciliation with frozen v1.** v1 found no out-of-sample skill (ridge: Development +1.4%, Validation -2.5%, Final -1.5% vs mean). The v2 pooled number is the same pattern: positive in Development, negative in Validation and Final. The report's "strict gate" (positive in both OOS halves and ex top-5) is passed because the half boundary falls in Dec 2022 and 2023 is the best year; it is not the v1 gate (Validation+Final pooled OOS R2 > 0, CW p < 0.05, directional accuracy binomial p < 0.05, ex top-5). Under the v1 window rule, R-target results:

| predictor -> next R | OOS R2 Dev / Val / Final / Val+Final | CW p (Val+Final) | v1-window verdict |
|---|---|---|---|
| S&P (prior window) | 1.5 / 1.7 / 2.6 / 2.0% | 0.0009 | pass |
| US VIX (prior window) | 0.4 / 0.9 / 2.0 / 1.3% | 0.006 | pass |
| BSE own lag | 1.9 / -0.7 / -0.7 / -0.7% | 0.30 | **fail** |
| residual vs Nifty | 1.3 / -0.8 / -0.5 / -0.7% | 0.40 | **fail** |
| CDSL lag | 1.1 / 1.1 / -1.6 / +0.1% | 0.083 | fail |
| MCX lag | 0.3 / 1.3 / -0.4 / +0.7% | 0.012 | weak (Final negative) |
| Nifty 50 lag | 0.2 / 0.3 / -0.2 / +0.1% | 0.20 | not_found (agrees with report) |

For the **gap G** the same predictors are positive in every window (own lag Dev +1.5%, Val +1.8%, Final +2.3%, Val+Final +2.0%, CW p 3e-4; residual +1.5%; CDSL +0.85%; MCX +0.65%), so the lag -> gap channel is stable; the close-to-close R version fails because the intraday leg (corr of R_{k-1} with I_k: +0.056 overall, -0.04 in 2024, -0.09 in the auction sample) reverses it.

**Is the VWAP close the cause?** Tests that use no judgement about the mechanism:
1. Replace the VWAP close by the last traded price (`last` column, available to 2026-07; equal to the close afterwards): ac1 of returns = **0.094 vs 0.107**; WF OOS R2 +0.75% (CW p 7e-4) vs +0.97% (p 2e-4) on the same sample. At most about 12% of the autocorrelation is attributable to the close definition.
2. VWAP-mechanics predict a lag -> gap channel (end-of-day drift pushed into the next open) that disappears under the auction. Observed corr(R_{k-1}, G_k): VWAP era 0.130; auction era **+0.192** (n 50, SE 0.14); interaction coefficient +0.018, t 0.25. The R -> R drop comes from the intraday leg (0.056 -> -0.090), interaction t = -0.90 (p 0.37).
3. A 50-session window has ac1 <= 0.018 in 31% of all rolling windows of the VWAP era (mean 0.073, sd 0.131). The auction-era sample cannot confirm or refute any change.
4. Nifty 50 (also priced off constituent VWAP closes) has ac1 -0.043, the wrong sign for a common VWAP artefact.
Conclusion: the report's sentence "a VWAP close mechanically pushes the end-of-day drift into the next gap" is a hypothesis, and the data on hand mostly contradict it. The honest statement is: small persistence (ac1 about 0.1), not stable in the last two years for close-to-close R, cause unknown.

**Do the peer results add anything?** Persistence alone implies cross-lag corr(R_k, CDSL_{k-1}) about 0.49 x 0.104 = 0.051; observed 0.092-0.097, so roughly half is explained by both series' own autocorrelation. Nested walk-forward tests (min train 500): adding CDSL_{k-1} to BSE's own lag gives +0.09% (CW p 0.11); MCX +0.01% (p 0.28); adding BSE_{k-1} to CDSL's own lag +0.05% (p 0.09); to Angel One's own lag -0.15% (p 0.19). Partial regression R_k on [R_{k-1}, x_{k-1}]: CDSL coefficient 0.059 (HAC t 2.1), Angel One 0.024 (t 0.7), MCX 0.038 (t 1.5). F9 only nested the peers against S&P, never against BSE's own lag, so "CDSL, MCX, own lag, residual validated" is one persistence signal counted four times (brief rule 5). F10 "BSE leads CDSL / Angel One" does not control for the target's own lag. Angel One's F10 result also depends on the "250 minimum training rows" exception: with 500 rows its stand-alone OOS R2 is +0.37% (raw p 0.024, not Holm-significant).

## 4. Point (c): Capital Markets "mechanical overlap"

* Arithmetic is sound: cov(R, I) = w var(R) + sum over other constituents; w var(R)/cov(R, I) = 33.8% (w = 15.09%) and 51.2% (w = 22.88%), identical to the report. With a time-constant w it is an identity, not an "upper bound" (JSON note wording).
* Weights are unverified in the report. **Data-implied weight:** regressing the index return on BSE and the six peers (n 513, R2 0.95) gives BSE 0.197 (0.194 first half, 0.211 second half; peer coefficients 0.06-0.17 plausible). That is inside the 15-23% range and implies a mechanical share of about **44%**. Weight varies over time (BSE's relative market cap moved a lot), which a constant w ignores.
* More useful statistic for readers: correlation of BSE with the index excluding BSE is 0.67 (w 15%) to 0.56 (w 23%) rather than 0.81, and the ex-BSE beta is 1.30 to 1.10 rather than 1.47. The "31% idiosyncratic share" (Nifty + Capital Markets) is correctly flagged as non-comparable.
* Verdict: confirmed, with the caveat that the headline 0.81 / 1.47 should be quoted with the ex-BSE counterparts.

## 5. Regime flip / break claims, independent tests

Wild-bootstrap sup-Wald (Andrews QLR style, 15% trimming, HAC 5 lags, 150 draws):
* S&P -> G slope: sup-W 17.9 at 2020-03-31, bootstrap p < 0.01 (95% critical 9.5); excluding 2020-02-20..04-30: 14.2 at 2020-06-09, p 0.007. Slopes: 0.150 (2017-02..2020-03), 0.357 (2020-04..), 0.511 (2025+), 0.584 (last 250). Linear slope trend t = 3.2. **Instability confirmed** (and slope still positive everywhere).
* S&P -> R slope: no break (sup-W 6.5, p 0.23).
* Nifty beta of BSE: sup-W 33.9 at 2021-03-25, p < 0.01. "Beta about 0.9" is an average of 0.64 before 2021-03-25 (n 1018) and 1.27 after (n 1369) (confirmed).
* BSE gap on Nifty gap: sup-W 65 at 2021-04, slope 0.755 (before 2025) vs 1.47 (2025+), R2 21% -> 53%; supports the report's "gap more market-driven since 2025".
* Own-lag "break" at the closing-auction change: not supported (t = -0.90; within the VWAP era a sup-Wald break test gives p 0.46). The report does not claim a break, but its caveats lean on one.
* Up/down beta, VIX-tercile beta: no break (p 0.061 and 0.32), forbes-rigobon 0.239: confirmed `not_found`.

## 6. Look-ahead, definitions, thresholds, multiple testing

* **Look-ahead:** none found. Windows [d_{k-1}, d_k); lag features use session k-1; the beta in the residual feature is shifted by one session before use; VIX terciles use expanding thresholds on VIX_{k-1}; walk-forward uses rows j < k only. Contemporaneous items (same-day Nifty, same-date USD/INR and Brent) are used only as associations or conditional scenario mappings and are labelled so.
* **Definition drift:** (i) "strict gate ... v1-style" is not v1's gate (see s3); (ii) JSON note calls the overlap share "upper-bound style" though it is an identity; (iii) report ledger text "validated_out_of_sample (weak/tiny)" while the JSON status string is plain `validated_out_of_sample` (the qualifier lives only in prose); (iv) S&P walk-forward appears in both F3 and F8 (counted twice).
* **Thresholds tuned on outcomes:** not found. Split date (2023-01-01), 500/250 minimum training rows, -1.5% decline cut-off, 0.5% sign-agreement cut-off, expanding terciles are fixed in the docstring; the post-hoc additions (F9, F10, strict gate, composite) are disclosed and the composite (-0.16 pp) is labelled exploratory.
* **Effective n:** no overlapping return windows exist (daily, disjoint US windows). n_eff = n x (se_iid/se_HAC)^2 reproduces (882.5) but mixes heteroskedasticity with autocorrelation; fine as a conservative summary. Rolling-250 windows are acknowledged as overlapping (about 8 independent windows).
* **Multiple testing:** Holm/BH are applied inside ten families (260 tests), with the same predictors tested against R, G and I and again in F1 and F10, with no cross-family adjustment. A pooled Holm over 218 of the tests (F1-F5, F8, F10) leaves: S&P -> G WF 1.7e-8, S&P -> G split 0.020, S&P -> R WF 6.6e-5 (S&P -> R split 0.24), US VIX -> G 2.7e-10, own lag -> G 4e-4, residual -> G 1e-3, own lag -> R **0.046**, CDSL -> R **0.041**, F10 CDSL **0.046**; and **fails** for MCX -> R (0.51), residual -> R (0.34), F10 Angel One (0.61), F10 Capital Markets (0.145), USD/INR -> G (0.10), CDSL -> G (0.068).
* **Clark-West vs raw MSPE:** all "validated" labels use the nested CW test; the unadjusted DM p-value for own lag -> R is 0.099 (for S&P -> G < 1e-6). Worth reporting both.
* **Report vs JSON:** all table entries I compared (family counts 260 / 16 / 3 / 7 / 7 / 0; beta table; D3 table; live state; F10 numbers) match `results/behaviour/linkages.json`. The one text-vs-JSON contradiction is the "every validated label passes the strict gate" sentence: `passes_strict_gate` exists only for F2-F4 entries, and F10 CDSL (first half -0.14%), Angel One (-0.12%) would fail it.

## 7. Recommended label changes

| claim | report | recommended |
|---|---|---|
| S&P -> G, S&P -> R | validated_out_of_sample | keep (note slope 0.15 -> 0.58 drift; use last-250 slope as a sensitivity) |
| US VIX -> G/R | validated (same signal) | keep as one global-risk signal |
| BSE own lag, residual, CDSL, MCX -> R | validated_out_of_sample (tiny) | descriptive_only (fail v1 Val+Final gate, DM p 0.10, not incremental to each other) |
| same predictors -> G | validated | keep (positive in every window) but treat as one signal |
| BSE leads CDSL / Angel One / Capital Markets | validated_out_of_sample (weak) | descriptive_only (not incremental to target's own lag; Capital Markets n_oos 263 and BSE is a constituent) |
| conditional Nifty beta forecast | validated_out_of_sample | keep, flag "contemporaneous, not a forecast" in the status cell |
| Capital Markets beta/corr | descriptive_only | keep, add ex-BSE statistic |
| lead-lag F1, asymmetry, VIX regime, macro nulls | descriptive_only / not_found | confirmed |

## 8. Residual gaps I could not close

* 13 Oct NSE index row and the live Yahoo quotes (not re-fetched, per instruction); corroborated elsewhere only for the Nifty close.
* BSE's actual Capital Markets weight (only data-implied, 0.197).
* GIFT Nifty/Asian overnight information: absent from the data, so I cannot say whether the S&P slope is a proxy.
* No intraday history for the VWAP era, so the VWAP mechanism is tested only through the `last` price and component correlations.
