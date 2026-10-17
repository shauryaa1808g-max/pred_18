# Specialist G: "watch the past to shape the future" - forecasting the day's high and low from comparable past sessions (analogues)

> **RESULT IN PLAIN WORDS (added after the results were in; the pre-fixed rule and design that follow were written before any variant was run and are unchanged: Section 0 text sha256 `5fe6dc76ba4dad09...`; the whole original file, sha256 `86315bda184f3dfe...`, is also in git commit 2072844).**
>
> **Verdict: matching today to comparable past days does NOT make the day's high or low more precise. The baseline stays the headline.**
>
> * **Tested:** 172 variant-target pairs (43 variants for each of the 4 targets: five sets of context features, four ways of picking and weighting the comparable days, each alone and blended with the baseline, plus three controls; 38 candidate features pre-open, 43 post-open). **0 of 172 meet the pre-fixed adoption rule.** The best any variant did was +0.02% / +0.78% / +0.41% / +0.39% lower pinball loss than the baseline (pre-open high / pre-open low / post-open high / post-open low); the rule needs at least +2% and a Holm-adjusted p below 0.05.
> * **In rupees** (Final window, n = 320 sessions, at Rs 3,428) the typical miss of the median barely moves: over all 43 variants it stays between Rs 41.8 and 44.0 for the pre-open high (baseline 42.7), 47.2 and 49.3 for the pre-open low (baseline 47.7), 34.2 and 35.7 for the high once the 09:08 open is known (baseline 34.8) and 37.2 and 39.4 for the low once the open is known (baseline 37.4). Table below.
> * **The five most similar days, which is what a person reads off the list, are a worse guide than the baseline median** (typical miss 8% / 9% / 16% / 12% larger). Five days are too few; with 80 days the forecast is steadier, but it is no more accurate than the baseline (table).
> * **Beyond volatility clustering?** No detectable gain. Richer context sets against the volatility-only control: 0 of 32 comparisons significant after Holm; the single best-looking cell (market context, pre-open high, +4.5% against the volatility-only control, raw p 0.003, Holm p 0.08) is not significant and the variant is still worse than the baseline. The features carry almost no linear information about the standardised high and low (out-of-sample R-squared -0.07 to +0.03). So "more parameters" did not help in this form.
> * **Power, said plainly:** with n = 320 and 172 tests only a true gain of about 2.3% to 3.0% or more could have been confirmed; the point estimates are about zero or negative, and a gain above 1.5% is excluded for the blended display variant on every target.
> * **16 Oct 2026** (official close Rs 3,428.0, official open Rs 3,450.0): the comparable-days and baseline medians differ by Rs 14 (pre-open high), 11 (pre-open low), 5 (post-open high), 2 (post-open low), far less than the typical miss. The dated comparable days are in Section 5; one missing input (delivery %) changes 3 of the 5 nearest days, which shows how fragile such a list is (Section 5.7).
>
> | target (n = 320) | baseline typical miss, Rs | comparable days alone (set B, 80 nearest): miss Rs / pinball gain | blended with baseline: miss Rs / gain | best of the 43 variants: gain (which) | adopted |
> |---|---|---|---|---|---|
> | pre-open high | 42.7 | 43.4 / -5.0% | 42.8 / -1.4% | +0.02% (C_k40_b) | 0 of 43 |
> | pre-open low | 47.7 | 47.6 / -1.4% | 47.4 / -0.1% | +0.78% (A_k40_b) | 0 of 43 |
> | post-open high | 34.8 | 34.4 / -3.1% | 34.5 / -1.1% | +0.41% (C_k40_b) | 0 of 43 |
> | post-open low | 37.4 | 37.5 / -2.1% | 37.2 / -0.5% | +0.39% (V_ker_b) | 0 of 43 |

*Status: THE SECTION BELOW (Section 0) WAS WRITTEN BEFORE ANY ANALOGUE VARIANT WAS RUN (Fri 16 Oct 2026, morning IST). Before writing it I had only (a) read the project files listed in the brief, (b) looked at data facts (which files end on which date, how many rows each source has, outliers in the peer file, when the macro files were fetched) and (c) started the baseline's own evaluation in a scratch copy of the repo to reproduce its numbers. No analogue forecast, pinball, coverage or p-value had been computed. The text of Section 0 is not changed afterwards; anything that departs from it is listed in Section 6 as a departure. The timestamp is my own working record (file hash and modification time kept in the scratchpad), not an independent one.*

## 0. Pre-fixed rule, design and variant list

### 0.1 The adoption rule (fixed now; copied from the brief)

A variant counts as an improvement for a target (pre-open high `Hp`, pre-open low `Lp`, post-open high `HO`, post-open low `LO`) ONLY IF ALL five hold:

1. **Accuracy.** Mean pinball loss (average over the project's 9-level grid, 2.5% ... 97.5%) in the **Final window** (1 Jul 2025 to 15 Oct 2026, n = 320) is at least **2% lower** than the baseline's for that target, and the Diebold-Mariano test (Harvey-Leybourne-Newbold small-sample factor, Newey-West lag 5, `src/metrics.py`; **two-sided** p, as in the project) gives **p < 0.05 after Holm** over **every variant-target pair tried** (the family size is counted by the code and printed in Section 3).
2. **Validation sign.** In the Validation window (1 Jul 2024 to 30 Jun 2025, n = 248) the variant's pinball is also lower than the baseline's (same sign).
3. **Calibration.** In the Final window the 50% and 90% central bands are *not worse than the baseline's* (absolute distance of the coverage from its nominal level is no larger than the baseline's) **and** the Kupiec test has p > 0.05 for both bands. For `HO` (the high measured from the open, which has an atom at zero because the open is the day's high on about 4% of sessions) the 90% band is replaced by the atom-aware check from `verify_A_dayahead.md`: the share of outcomes above the model's 95% quantile must be no further from 5% than the baseline's and must have a two-sided exact binomial p > 0.05; the 50% band is checked as usual.
4. **Auction slice.** In the post-closing-auction slice (3 Aug 2026 on, n = 52) the pinball is not more than 5% worse than the baseline's.
5. **Leakage test passes.** All data from the target session onward is replaced by junk (random numbers; for the post-open forecast only the official open of that session is kept) in the bar file, the index/VIX file, the breadth file, the peer file and the macro files, and the forecast for that session (every variant, quantile by quantile) must be unchanged (tolerance 1e-9 in log units). Run for 8 sessions spread over 2020 to 15 Oct 2026.

Also reported for every variant: the typical rupee miss of the median (mean absolute error of the 50% quantile in rupees at the reference price Rs 3,428, as in `A_dayahead.md`). Baselines: `P_S6` (pre-open) and `W_I6` (post-open) from `src/hl_model.py`, plus 'price stays' / 'open stays' and the trailing-250 empirical quantiles.

Other rules kept: walk-forward only (expanding, refit every 20 sessions like the project; first evaluated session 750 = 25 Feb 2020 so all methods are scored on the same days); every feature selection or weight fit uses sessions before the 20-session block only, never the Final window; n beside every claim; "tested" and "descriptive" labelled; nulls reported plainly.

### 0.2 The method

For a target session `t`:

1. **Standardised outcomes of every past session `s`:** pre-open `u_s = (Hp_s, Lp_s) / sigma_s` and post-open `(HO_s, LO_s) / sigmaI_s`, where `sigma` is the baseline's own walk-forward S6 volatility of the close-to-close return (`hl_model.wf_sigmas(R, v)`) and `sigmaI` that of the open-to-close return. These are exactly the "residuals" the baseline resamples.
2. **Features of session `s`:** a vector `x_s` known at the *pre-open of `s`* (nothing from session `s` itself; Section 0.3). Post-open adds four gap features that are known at 09:08 from the official open.
3. **Distance** from `x_t` to `x_s` for every eligible past `s`: `500 <= s <= t - 6` (the last 5 sessions are excluded to avoid the overlap between the trailing windows of `x`), complete rows only. Features are standardised with the mean and standard deviation of the eligible sessions up to the start of the current 20-session block, clipped at +-4. Distance is **shrunk Mahalanobis** (`Sigma_shrunk = 0.7 * correlation matrix + 0.3 * identity`, both fitted on sessions before the block) for the a-priori sets, and a **ridge-weighted Euclidean** distance for the learned set.
4. **Forecast distribution:** the nearest analogues' standardised outcomes times the target's baseline sigma (`sigma_t`, or `sigmaI_t`), quantiles at the 9 grid levels: `k` nearest with equal weights, `k` in **{40, 80, 160}**; or a **Gaussian kernel** over all eligible sessions with bandwidth `h` = distance to the 80th nearest (weighted quantile with Hazen plotting positions).
5. **Blend (form `b`):** quantile averaging `(1 - w) * baseline_quantile + w * analogue_quantile`, `w` in {0, 0.1, ..., 1} chosen separately for each target to minimise mean pinball over the trailing 500 already-scored walk-forward sessions before the block (refit every 20 sessions; `w = 0.5` until 120 scored sessions exist). `w = 0` is the baseline.
6. **Ridge learned metric (space `L`):** at each block start, fit a ridge regression of the two standardised outcomes (`u_H`, `u_L`) on the standardised features using only sessions before the block; ridge penalty from {1, 10, 100, 1e3, 1e4} chosen on the last 30% of that training sample (fit on the first 70%); feature weight `w_j = sqrt(beta_Hj^2 + beta_Lj^2)`; distance = weighted Euclidean. Fewer than 150 complete training rows: equal weights.

### 0.3 The features and their timestamp rules (all must be known at the pre-open of session `s`; `j = s - 1` is the previous session; `sig_s` is the baseline S6 sigma for session `s`, which the baseline itself knows before the open)

Log-adjusted price series are built from the project's own log returns (`c_k = cumulative sum of R`; `h_k = c_{k-1} + Hp_k`, `l_k = c_{k-1} + Lp_k`, `o_k = c_{k-1} + G_k`), because the processed file's OHLC levels are raw traded prices (3-for-1 bonus/split on 21 Mar 2022 and 23 May 2025); only `prev` is adjusted. Volume in shares is adjusted for the same two events.

| id | feature | timestamp rule |
|---|---|---|
| **V** | `lnsig_rel = ln(sig_s / RMS of R over sessions j-249..j)` (the volatility state; the only feature of the vol-only control) | sig_s known at the pre-open; R to `j` |
| **A (6)** | `rng1 = ln(rho_j) - ln(sig_s)` (yesterday's high-low range in units of today's sigma); `cloc` = close location in yesterday's range; `gap1 = abs(G_j) / sig_s` (yesterday's absolute opening gap); `r5`, `r20` = log return over 5 / 20 sessions to `j`, divided by `sig_s * sqrt(5 or 20)`; `lnsig_rel` | official bars to `j` (bhavcopy ~16:34 IST on `j`) |
| **B (A + 8 = 14)** | `pk5` = 5-session Parkinson vol vs sig_s; `gk20` = 20-session Garman-Klass vol vs sig_s; `volz`, `turnz`, `delz` = 60-session z-scores (window ends at `j`) of ln share volume (split-adjusted), ln turnover, delivery %; `dhi`, `dlo` = log distance of the close from the trailing-250-session high / low (in units of `sig_s*sqrt(20)`); `streak` = signed run length of consecutive up / down closes (capped at 6) | bars to `j` |
| **C (B + 17 = 31)** | calendar: weekday of the target date (4 dummies), `mend` = target date is one of the last two weekdays of its month; market (index file row `j`, returns scaled by their own trailing-60-session standard deviation): `nifty_r1`, `nifty_rng1`, `bank_r1`, `bank_rng1`, `vix_ln`, `vix_d1`, `vix_rv` = ln VIX minus ln of Nifty 20-session realised vol (annualised, %); breadth row `j`: `adv` (advance share), `tailbal` = (stocks up >= 5% minus down >= 5%) / liquid stocks, `mktturn_z`; peers (mean over CDSL, MCX, MOTILALOFS, IEX, days with absolute return above 15% dropped as corporate actions): `peers_r1`, `peers_rng1`; US overnight (see lag rule): `sp_r1`, `usvix_ln`, `usvix_d1` | rows dated `j` (the index file row of date `j`, the breadth row of date `j`, the peer rows of date `j`) |
| **L (C + 4 = 35)** | C plus slow macro changes over 5 observations: `us10y_d5` (DGS10), `brent_r5`, `dxy_r5` (DTWEXBGS), `inr_r5` (DEXINUS) - all with the lag rule | see below |
| post-open (+5) | `gz = G_s / sig_s`, `agz = abs(gz)`, `obeyond` = +1 / -1 / 0 if the official open is above yesterday's high / below yesterday's low / inside, `orel` = (o_s - l_j) / (h_j - l_j) clipped to [-1, 2], `lnsI_rel` = ln(sigI_s / RMS of I) | the official open `O_s` (NSE pre-open auction, final 09:08 IST) and bars to `j` |

**Macro lag rule.** The FRED files were fetched on 13 Oct 2026 about 21:26 IST (file times) and end on 12 Oct (S&P 500, VIX), 8 Oct (DGS10), 6 Oct (Brent), 2 Oct (dollar index, USDINR); the publication lag of a FRED series is not provably zero, so for a session dated `D` I use the last observation dated on or before `D - 2` calendar days for S&P 500 and US VIX, `D - 6` for DGS10, `D - 8` for Brent, `D - 12` for DTWEXBGS and DEXINUS (the observed lag at the fetch plus one day of margin). This deliberately discards the freshest US session. The ECB USDINR file in `data/raw/macro` is an HTML error page (HTTP 301) and is unusable; DEXINUS (FRED) stands in.

**Missing-feature rule (affects only the live day).** If a feature of the target session is not available (a source file ends before the previous session) it is dropped from that session's distance (Mahalanobis on the available sub-vector, covariance sub-matrix) and the dropped features are listed. For 16 Oct this applies to every market, breadth, peer and US feature (files end 12-13 Oct), so on 16 Oct spaces `C` and `L` collapse to the BSE-own features plus the calendar. Spaces `V`, `A`, `B` are complete.

**Not usable / not used here, said plainly (untested):** NSE pre-open order book (2 snapshots), GIFT Nifty, FII/DII flows (no verified dated series), the Capital-Markets index (history only from Apr 2023, 21% of sessions; peers stand in), BSE ATM implied vol and skew (`bse_iv_daily.csv`, 461 sessions from 29 Nov 2024: with the 5-session exclusion and 150+ analogues needed, the pool would hold fewer than 150 sessions when the Final window opens and the Validation window would be empty, so the adoption rule could not even be applied), F&O expiry day (`data/raw/fo_bse` starts 18 Nov 2024, same problem), the Yahoo-bars-based intraday context (no history before Aug 2026 at 15 minutes).

### 0.4 The variants (all declared now)

Spaces `V` (volatility state only, 1 feature: **the control for "is it only volatility clustering"**), `A` (6), `B` (14), `C` (31), `L` (35, ridge-weighted). Estimators `k40`, `k80`, `k160`, `ker`. Forms `a` (analogue alone) and `b` (blended with the baseline). That is 5 x 4 x 2 = **40 variants per phase**, plus three controls per phase: `RAND80a`, `RAND80b` (80 analogues drawn at random from the same eligible pool, seed 10000 + t: the noise cost of an 80-draw sample with no matching) and `POOL` (all eligible past sessions, no matching: the expanding-window version of the baseline, to separate "matching" from "longer window"). **43 variants per phase x 2 targets x 2 phases = 172 variant-target pairs = the Holm family.** (Nothing else is tried; the number of distinct candidate features is 35 pre-open and 40 post-open.)

**Secondary analyses (labelled, not part of the adoption decision, their own small Holm family):** (S1) each of `A`, `B`, `C`, `L` (estimator `k80`, forms `a` and `b`) against the vol-only `V` control: 4 spaces x 2 forms x 4 targets = 32 tests; (S2) the point accuracy of "the median of the 5 nearest past days" (what a user reading the list of comparable days sees) in space `B`, descriptive only, mean absolute error with standard error; (S3) the walk-forward out-of-sample R-squared of the ridge fits (is there *any* linear information in the features about the standardised extremes?), descriptive.

**Live output (fixed now).** `analog_forecast(date, open_price=None)` returns the baseline-shaped dict for the display variant **space `B`, estimator `k80`, forms `a` and `b`** (chosen before results because `B` is the widest set that is complete on 16 Oct), the 5 and 10 most similar past sessions with dates, distance, similarity and their realised high / low as % of the previous close (pre-open) or the open (post-open), and the same for the other spaces in the JSON. Whatever the adoption rule decides, the baseline stays the headline unless a variant is adopted.

---

## 1. What was run, in plain words

**Idea.** Describe every session by a list of numbers known before the forecast time (yesterday's range and where it closed in that range, the volatility state, volume, the market and VIX, breadth, peers, the US overnight, and after 09:08 the official open). For a new day find the past days whose list is closest, take what their high and low turned out to be (as multiples of that day's normal move, the baseline's S6 sigma), rescale to today's normal move, and use the spread of those outcomes as the forecast. The user's hope was that reading "the full surrounding context" would sharpen the high and low.

**What was tried (all declared in Section 0 before any result).** Five feature sets: V (volatility state only: the control for "is it just volatility clustering"), A (6 features), B (14 BSE-own features), C (34: B plus calendar, market, VIX, breadth, peers, US overnight) and L (38: C plus slow macro, with ridge-learned feature weights). Four estimators: the 40, 80 or 160 nearest past sessions (equal weights, the last 5 sessions excluded) or a Gaussian kernel over all eligible past sessions. Each alone ("a") and blended with the baseline ("b", the blend weight fitted on the trailing 500 already-scored sessions only). Plus three controls (80 random past sessions alone and blended, and all past sessions with no matching); the volatility-only set V is itself the control for "is it only volatility clustering". That is 5 x 4 x 2 + 3 = 43 variants per phase; x 2 targets x 2 phases = **172 variant-target pairs = the Holm family**. The number of distinct candidate features searched is **38 pre-open and 43 post-open** (the counts in Section 0.3/0.4 were mis-added; see Section 6). No feature was chosen by looking at the Final window: the sets were fixed in advance, and the only fitted choices (standardisation, covariance, ridge weights, blend weights) are refitted every 20 sessions on earlier sessions.

**Windows (by target date; walk-forward, expanding, refit every 20 sessions, first evaluated session 25 Feb 2020).** Final 1 Jul 2025 to 15 Oct 2026 (n = 320); Validation 1 Jul 2024 to 30 Jun 2025 (n = 248); post-closing-auction slice from 3 Aug 2026 (n = 52); n = 1,640 sessions evaluated in all. History used: official bars through the 15 Oct 2026 close; the 16 Oct session is not used anywhere (`STUDY_END` in the code cuts every study run at sessions strictly before 16 Oct).

**How "better" is measured.** Pinball loss averaged over the 9-level grid (2.5% to 97.5%); a "gain" is the percentage by which a variant's average loss is below the baseline's (positive = better). The typical rupee miss is the mean absolute error of the 50% quantile in rupees at Rs 3,428, as in `A_dayahead.md`.

## 2. The baseline, reproduced first

Before testing anything I rebuilt the baseline (`src/hl_model.py`: S6 volatility x filtered historical simulation) inside my pipeline and compared it with the project's stored files (`results/hl_eval_predictions.csv`, `hl_eval_preopen.csv`, `hl_eval_postopen.csv`). **All 28 quantile columns x 1,640 evaluated sessions agree to 9.1e-13 rupees** (`results/hl5_baseline_repro.csv`), and the Final-window figures are the ones the user was given:

| target | pinball x1e4 (mine / project) | typical miss, Rs at 3,428 (mine / project) |
|---|---|---|
| pre-open high (n = 320) | 31.1516 / 31.1516 | 42.69 / 42.69 |
| pre-open low (n = 320) | 36.5788 / 36.5788 | 47.67 / 47.67 |
| post-open high (n = 320) | 23.8531 / 23.8531 | 34.81 / 34.81 |
| post-open low (n = 320) | 28.0298 / 28.0298 | 37.42 / 37.42 |

(The second figure in each pair is the project's value, recovered as mine minus the stored difference in the repro file; every difference is 0.)

The 16 Oct baseline inside my result also equals `hl_model.hl_forecast('2026-10-16', 3450.0)` to the cent (`results/hl5_live_checks.csv`, check 'baseline in hl5 result vs hl_model.hl_forecast': maximum difference Rs 0.000).

## 3. Result under the pre-fixed adoption rule

### 3.1 The benchmarks in the Final window (tested, n = 320)

| target | model | n | pinball x1e4 | 50% band covers | 90% band covers | typical miss of median (Rs at 3,428) | half the time within (Rs) |
|---|---|---|---|---|---|---|---|
| H | BASELINE P_S6 | 320 | 31.152 | 0.469 | 0.903 | 42.7 | 33.6 |
| L | BASELINE P_S6 | 320 | 36.579 | 0.503 | 0.887 | 47.7 | 32.2 |
| H | trailing-250 empirical | 320 | 32.739 | 0.506 | 0.912 | 43.7 | 35.4 |
| L | trailing-250 empirical | 320 | 36.587 | 0.519 | 0.919 | 47.5 | 33.7 |
| H | price stays | 320 |  |  |  | 62.9 | 51.6 |
| L | price stays | 320 |  |  |  | 61.3 | 42.6 |
| HO | BASELINE W_I6 | 320 | 23.853 | 0.494 | 0.950 | 34.8 | 29.1 |
| LO | BASELINE W_I6 | 320 | 28.030 | 0.503 | 0.894 | 37.4 | 26.6 |
| HO | trailing-250 empirical | 320 | 25.009 | 0.500 | 0.922 | 35.4 | 31.2 |
| LO | trailing-250 empirical | 320 | 28.053 | 0.491 | 0.903 | 37.6 | 28.3 |
| HO | open stays | 320 |  |  |  | 51.3 | 40.7 |
| LO | open stays | 320 |  |  |  | 59.0 | 45.2 |

*Read: 'pinball x1e4' is the average loss (lower is better); the 50% and 90% bands should cover 0.50 and 0.90. The post-open high band marked '90%' actually covers 95% because the open is the day's high on about 4% of sessions (the correction in `verify_A_dayahead.md`).*

### 3.2 How many of the 172 pairs pass each of the five conditions (tested)

| target | variants | c1 gain >= 2% and Holm < 0.05 | c2 validation sign | c3 calibration | c4 auction slice | c5 leakage | ADOPTED | variants better than baseline in Final | largest Final gain % | that variant | its Holm p | smallest raw p among the better ones | worse than baseline with Holm < 0.05 | median s.e. of the gain (% points) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| H | 43 | 0 | 22 | 6 | 30 | 43 | 0 | 1 | +0.02 | C_k40_b | 1.000 | 0.9665 | 16 | 0.63 |
| L | 43 | 0 | 35 | 3 | 40 | 43 | 0 | 23 | +0.78 | A_k40_b | 1.000 | 0.0408 | 0 | 0.83 |
| HO | 43 | 0 | 28 | 0 | 30 | 43 | 0 | 1 | +0.41 | C_k40_b | 1.000 | 0.6263 | 15 | 0.83 |
| LO | 43 | 0 | 26 | 3 | 37 | 43 | 0 | 10 | +0.39 | V_ker_b | 1.000 | 0.1921 | 1 | 0.64 |

*Columns: c1 = gain of at least 2% in the Final window AND Holm-adjusted two-sided Diebold-Mariano p < 0.05 over all 172 pairs; c2 = same sign in Validation; c3 = 50% and 90% coverage not worse than the baseline's and Kupiec p > 0.05; c4 = auction-slice pinball not more than 5% worse; c5 = leakage test passed (it did for every variant, Section 3.5). A pair is adopted only if all five hold: **0 of 172**. 'Variants better than baseline in Final' counts pairs with a positive point gain; 'worse with Holm < 0.05' counts pairs that are significantly WORSE than the baseline.*

**Failures, plainly.** Condition c1 fails for every pair: 0 of 172 pass it. The largest Final gain of any pair is +0.78% (never 2%). Many analogue-alone variants are significantly worse than the baseline: 16 of 43 for the pre-open high, 0 for the low, 15 for the post-open high, 1 for the post-open low (Holm p < 0.05 within the family).

### 3.3 Every variant tried: Final gain, Holm p, Validation gain and typical rupee miss (tested)

Gain % = percent lower pinball loss than the baseline (negative = worse); Holm p = two-sided Diebold-Mariano (HAC lag 5, Harvey-Leybourne-Newbold) adjusted over the whole family of 172; Val gain % = the same gain in the Validation window (n = 248); miss Rs = typical rupee miss of the median in the Final window (baseline: pre-open high 42.7, low 47.7; post-open high 34.8, low 37.4). Variant names: space (V, A, B, C, L), estimator (k40, k80, k160 nearest days; ker = kernel), form (a = analogue alone, b = blended with the baseline); RAND80 = 80 random past days; POOL = all past days, no matching.

**Pre-open (targets H = high, L = low; reference = previous close)**

| variant | H gain % (Final) | H Holm p | H Val gain % | H miss Rs | L gain % (Final) | L Holm p | L Val gain % | L miss Rs |
|---|---|---|---|---|---|---|---|---|
| V_k40_a | -9.82 | 0.000 | -1.59 | 44.0 | -5.65 | 0.267 | -1.55 | 48.7 |
| V_k40_b | -0.45 | 0.838 | +0.21 | 42.7 | -0.63 | 1.000 | +0.25 | 47.8 |
| V_k80_a | -6.49 | 0.000 | -0.68 | 43.5 | -1.24 | 1.000 | -1.03 | 47.5 |
| V_k80_b | -0.06 | 1.000 | -0.05 | 42.7 | +0.02 | 1.000 | -0.10 | 47.6 |
| V_k160_a | -5.30 | 0.001 | -0.87 | 43.3 | +0.52 | 1.000 | +0.24 | 47.4 |
| V_k160_b | -0.30 | 1.000 | -0.27 | 42.8 | +0.53 | 1.000 | +0.09 | 47.4 |
| V_ker_a | -6.58 | 0.000 | -0.72 | 43.3 | -0.01 | 1.000 | +0.48 | 47.5 |
| V_ker_b | -0.16 | 1.000 | -0.15 | 42.7 | +0.28 | 1.000 | +0.12 | 47.5 |
| A_k40_a | -5.91 | 0.003 | -4.44 | 41.8 | -1.61 | 1.000 | -2.34 | 48.1 |
| A_k40_b | -0.21 | 1.000 | -0.58 | 42.6 | +0.78 | 1.000 | +0.14 | 47.5 |
| A_k80_a | -5.27 | 0.002 | -0.86 | 42.4 | -1.14 | 1.000 | +0.66 | 48.0 |
| A_k80_b | -1.08 | 1.000 | +0.01 | 42.6 | +0.05 | 1.000 | +1.01 | 47.7 |
| A_k160_a | -4.57 | 0.000 | -0.08 | 42.4 | +0.19 | 1.000 | +1.27 | 47.7 |
| A_k160_b | -1.40 | 0.368 | -0.03 | 42.7 | +0.33 | 1.000 | +1.16 | 47.6 |
| A_ker_a | -4.04 | 0.000 | +0.40 | 42.8 | +0.30 | 1.000 | +1.10 | 47.5 |
| A_ker_b | -1.26 | 1.000 | +0.40 | 42.7 | +0.30 | 1.000 | +1.10 | 47.5 |
| B_k40_a | -5.55 | 0.181 | -1.11 | 42.9 | -3.56 | 1.000 | -0.37 | 47.2 |
| B_k40_b | -0.46 | 1.000 | +0.77 | 42.5 | -0.21 | 1.000 | +1.40 | 47.2 |
| B_k80_a | -5.02 | 0.107 | +0.03 | 43.4 | -1.37 | 1.000 | +1.48 | 47.6 |
| B_k80_b | -1.38 | 1.000 | +0.42 | 42.8 | -0.11 | 1.000 | +1.89 | 47.4 |
| B_k160_a | -4.32 | 0.003 | -0.39 | 42.6 | -0.15 | 1.000 | +1.55 | 47.2 |
| B_k160_b | -0.89 | 1.000 | -0.19 | 42.7 | +0.20 | 1.000 | +1.53 | 47.2 |
| B_ker_a | -3.69 | 0.000 | +0.19 | 43.1 | +0.39 | 1.000 | +0.80 | 47.5 |
| B_ker_b | -0.89 | 0.208 | +0.19 | 42.7 | +0.39 | 1.000 | +0.79 | 47.5 |
| C_k40_a | -3.29 | 1.000 | -1.47 | 42.9 | -2.51 | 1.000 | -1.31 | 48.0 |
| C_k40_b | +0.02 | 1.000 | +0.11 | 42.7 | +0.16 | 1.000 | +0.85 | 47.7 |
| C_k80_a | -1.75 | 1.000 | -0.24 | 42.6 | -1.16 | 1.000 | +2.06 | 48.3 |
| C_k80_b | -0.28 | 1.000 | +0.05 | 42.6 | -0.19 | 1.000 | +2.35 | 48.0 |
| C_k160_a | -1.99 | 1.000 | +0.60 | 42.7 | -0.74 | 1.000 | +2.06 | 47.8 |
| C_k160_b | -0.91 | 1.000 | +0.59 | 42.7 | -0.44 | 1.000 | +1.96 | 47.7 |
| C_ker_a | -3.42 | 0.000 | +0.24 | 43.1 | +0.34 | 1.000 | +0.60 | 47.6 |
| C_ker_b | -0.78 | 0.164 | +0.24 | 42.8 | +0.34 | 1.000 | +0.60 | 47.6 |
| L_k40_a | -4.48 | 0.682 | -0.96 | 43.8 | -3.18 | 1.000 | +0.06 | 49.3 |
| L_k40_b | -0.34 | 1.000 | +0.94 | 42.8 | +0.25 | 1.000 | +1.81 | 48.3 |
| L_k80_a | -4.48 | 0.019 | -0.31 | 43.9 | -0.35 | 1.000 | +2.03 | 48.5 |
| L_k80_b | -0.82 | 1.000 | +0.62 | 42.9 | +0.47 | 1.000 | +2.34 | 48.1 |
| L_k160_a | -4.46 | 0.001 | +0.32 | 43.7 | -0.30 | 1.000 | +2.71 | 48.3 |
| L_k160_b | -1.45 | 0.285 | +0.62 | 43.0 | +0.15 | 1.000 | +2.58 | 48.0 |
| L_ker_a | -3.81 | 0.000 | +0.47 | 43.1 | +0.12 | 1.000 | +2.04 | 47.6 |
| L_ker_b | -1.08 | 0.285 | +0.47 | 42.8 | +0.12 | 1.000 | +2.04 | 47.6 |
| RAND80_a | -4.62 | 0.012 | -0.60 | 43.5 | -1.44 | 1.000 | -0.02 | 47.4 |
| RAND80_b | -0.14 | 1.000 | -0.03 | 42.7 | +0.01 | 1.000 | -0.11 | 47.5 |
| POOL_a | -3.40 | 0.000 | +0.29 | 43.1 | +0.36 | 1.000 | +0.26 | 47.6 |

**Post-open (targets HO = high from the open, LO = low from the open; reference = the official open)**

| variant | HO gain % (Final) | HO Holm p | HO Val gain % | HO miss Rs | LO gain % (Final) | LO Holm p | LO Val gain % | LO miss Rs |
|---|---|---|---|---|---|---|---|---|
| V_k40_a | -4.52 | 0.044 | -1.76 | 34.7 | -2.39 | 1.000 | -2.96 | 37.6 |
| V_k40_b | -0.13 | 1.000 | -0.08 | 34.8 | -0.03 | 1.000 | -0.08 | 37.4 |
| V_k80_a | -3.38 | 0.012 | -1.73 | 34.4 | -0.68 | 1.000 | -2.13 | 37.4 |
| V_k80_b | +0.00 | 1.000 | -0.08 | 34.8 | +0.21 | 1.000 | -0.31 | 37.3 |
| V_k160_a | -2.67 | 0.002 | -0.79 | 34.5 | +0.18 | 1.000 | -0.77 | 37.3 |
| V_k160_b | -0.10 | 1.000 | -0.08 | 34.8 | +0.36 | 1.000 | +0.03 | 37.2 |
| V_ker_a | -3.65 | 0.000 | -1.25 | 34.5 | +0.06 | 1.000 | -1.22 | 37.2 |
| V_ker_b | +0.00 | 1.000 | -0.12 | 34.8 | +0.39 | 1.000 | -0.15 | 37.2 |
| A_k40_a | -8.54 | 0.002 | +0.90 | 35.2 | -7.57 | 0.024 | -1.50 | 39.4 |
| A_k40_b | -2.22 | 1.000 | +1.83 | 34.8 | -0.88 | 1.000 | +0.67 | 37.7 |
| A_k80_a | -6.15 | 0.006 | +1.29 | 34.9 | -4.26 | 0.241 | -0.54 | 39.0 |
| A_k80_b | -2.77 | 0.973 | +1.32 | 34.9 | -0.68 | 1.000 | +0.34 | 37.6 |
| A_k160_a | -3.96 | 0.016 | +0.59 | 34.6 | -2.09 | 1.000 | -0.01 | 38.2 |
| A_k160_b | -1.81 | 1.000 | +0.59 | 34.8 | -0.55 | 1.000 | +0.39 | 37.5 |
| A_ker_a | -2.40 | 0.000 | +0.66 | 34.5 | -0.10 | 1.000 | +0.22 | 37.5 |
| A_ker_b | -1.35 | 0.165 | +0.66 | 34.6 | -0.03 | 1.000 | +0.22 | 37.5 |
| B_k40_a | -3.75 | 1.000 | +0.67 | 34.2 | -5.27 | 0.870 | -1.87 | 37.5 |
| B_k40_b | -0.50 | 1.000 | +1.41 | 34.4 | -0.71 | 1.000 | +0.62 | 37.3 |
| B_k80_a | -3.15 | 1.000 | +1.19 | 34.4 | -2.13 | 1.000 | -0.29 | 37.5 |
| B_k80_b | -1.09 | 1.000 | +0.91 | 34.5 | -0.54 | 1.000 | +0.43 | 37.2 |
| B_k160_a | -3.47 | 0.014 | -0.03 | 34.6 | -1.01 | 1.000 | +0.82 | 37.8 |
| B_k160_b | -1.11 | 1.000 | -0.02 | 34.7 | -0.53 | 1.000 | +0.82 | 37.7 |
| B_ker_a | -2.69 | 0.001 | +0.25 | 34.6 | +0.20 | 1.000 | +0.21 | 37.4 |
| B_ker_b | -0.48 | 0.361 | +0.00 | 34.8 | +0.20 | 1.000 | +0.18 | 37.4 |
| C_k40_a | -1.61 | 1.000 | -0.67 | 34.5 | -4.68 | 0.493 | -2.13 | 37.9 |
| C_k40_b | +0.41 | 1.000 | +0.77 | 34.5 | -0.65 | 1.000 | +0.82 | 37.5 |
| C_k80_a | -1.41 | 1.000 | +0.27 | 34.3 | -3.93 | 0.929 | +1.90 | 37.9 |
| C_k80_b | -0.27 | 1.000 | +0.66 | 34.5 | -1.80 | 1.000 | +1.93 | 37.7 |
| C_k160_a | -2.36 | 0.496 | +1.15 | 34.5 | -1.88 | 1.000 | +1.50 | 37.9 |
| C_k160_b | -1.40 | 1.000 | +0.88 | 34.6 | -1.43 | 1.000 | +1.50 | 37.8 |
| C_ker_a | -2.86 | 0.000 | +0.19 | 34.6 | +0.14 | 1.000 | +0.26 | 37.4 |
| C_ker_b | -0.15 | 1.000 | -0.15 | 34.8 | +0.14 | 1.000 | +0.25 | 37.4 |
| L_k40_a | -6.98 | 0.011 | -1.01 | 35.7 | -4.07 | 1.000 | -3.19 | 39.0 |
| L_k40_b | -1.29 | 1.000 | +0.45 | 35.0 | -0.17 | 1.000 | +0.46 | 37.6 |
| L_k80_a | -3.91 | 0.304 | +0.78 | 35.3 | -2.45 | 1.000 | +0.99 | 38.6 |
| L_k80_b | -1.39 | 1.000 | +1.08 | 35.0 | -0.47 | 1.000 | +1.77 | 37.7 |
| L_k160_a | -3.00 | 0.430 | +1.40 | 34.9 | -3.09 | 1.000 | +1.69 | 38.4 |
| L_k160_b | -1.36 | 1.000 | +1.34 | 34.9 | -1.22 | 1.000 | +1.93 | 37.8 |
| L_ker_a | -2.70 | 0.000 | +0.43 | 34.7 | -0.28 | 1.000 | +1.35 | 37.4 |
| L_ker_b | -0.86 | 0.173 | +0.43 | 34.8 | -0.28 | 1.000 | +1.35 | 37.4 |
| RAND80_a | -4.42 | 0.001 | -1.48 | 34.9 | -0.77 | 1.000 | -0.64 | 37.6 |
| RAND80_b | +0.00 | 1.000 | +0.00 | 34.8 | -0.08 | 1.000 | -0.03 | 37.4 |
| POOL_a | -3.07 | 0.000 | +0.09 | 34.6 | +0.29 | 1.000 | -0.23 | 37.4 |

### 3.4 Calibration and the auction slice for the display variants and the controls (tested)

| target | variant | 50% band covers | 90% band covers | Kupiec p (50%) | Kupiec p (90%; HO: share above q95 binomial p) | auction-slice pinball ratio to baseline |
|---|---|---|---|---|---|---|
| H | P_S6 (baseline) | 0.469 | 0.903 | 0.263 | 0.851 | 1.000 |
| H | B_k80_a | 0.472 | 0.884 | 0.314 | 0.362 | 1.059 |
| H | B_k80_b | 0.491 | 0.909 | 0.737 | 0.571 | 1.006 |
| H | V_k80_a | 0.459 | 0.887 | 0.146 | 0.464 | 1.066 |
| H | POOL_a | 0.463 | 0.928 | 0.180 | 0.079 | 1.044 |
| H | RAND80_a | 0.459 | 0.897 | 0.146 | 0.853 | 1.088 |
| L | P_S6 (baseline) | 0.503 | 0.887 | 0.911 | 0.464 | 1.000 |
| L | B_k80_a | 0.475 | 0.881 | 0.371 | 0.276 | 1.023 |
| L | B_k80_b | 0.500 | 0.891 | 1.000 | 0.581 | 1.006 |
| L | V_k80_a | 0.472 | 0.850 | 0.314 | 0.005 | 1.026 |
| L | POOL_a | 0.497 | 0.881 | 0.911 | 0.276 | 0.991 |
| L | RAND80_a | 0.491 | 0.859 | 0.737 | 0.022 | 1.071 |
| HO | W_I6 (baseline) | 0.494 | 0.950 | 0.823 | 0.039 | 1.000 |
| HO | B_k80_a | 0.487 | 0.922 | 0.655 | 0.007 | 1.080 |
| HO | B_k80_b | 0.481 | 0.922 | 0.502 | 0.020 | 1.026 |
| HO | V_k80_a | 0.500 | 0.944 | 1.000 | 0.039 | 1.057 |
| HO | POOL_a | 0.484 | 0.991 | 0.576 | 0.000 | 1.039 |
| HO | RAND80_a | 0.478 | 0.959 | 0.434 | 0.002 | 1.062 |
| LO | W_I6 (baseline) | 0.503 | 0.894 | 0.911 | 0.712 | 1.000 |
| LO | B_k80_a | 0.481 | 0.912 | 0.502 | 0.447 | 1.051 |
| LO | B_k80_b | 0.497 | 0.894 | 0.911 | 0.712 | 1.005 |
| LO | V_k80_a | 0.478 | 0.900 | 0.434 | 1.000 | 1.017 |
| LO | POOL_a | 0.484 | 0.916 | 0.576 | 0.340 | 0.993 |
| LO | RAND80_a | 0.500 | 0.900 | 1.000 | 1.000 | 1.033 |

*n = 320 (calibration), n = 52 (auction slice, ratio of mean pinball). Calibration of the display variants is similar to the baseline's; the blend inherits the baseline's. The auction-slice condition (ratio at most 1.05) is met by 137 of 172 pairs; it is not what stops adoption.*

**A flaw in the pre-fixed calibration condition, reported.** For the post-open high no variant passes c3 (0 of 43), because the baseline itself fails the atom-aware tail check: only 2.5% of outcomes (8 of 320) lie above its 95% quantile, a two-sided binomial p of 0.039 against 5% (the same 2.5% / p 0.039 appears for the pre-open high, as `verify_A_dayahead.md` noted). The rule asks for p > 0.05 AND no further from 5% than the baseline, so on this target it could not adopt anything whatever the accuracy. This does not change the verdict: c1 (accuracy) fails for every pair on its own.

### 3.5 Leakage test (condition c5; tested)

| session_index | session_date | max change, pre-open | max change, post-open | positive control pre | positive control post | bars replaced | index rows | breadth rows | peer values | macro obs |
|---|---|---|---|---|---|---|---|---|---|---|
| 900 | 2020-10-01 | 0.0e+00 | 0.0e+00 | 0.089 | 0.059 | 1490 | 1495 | 1496 | 17116 | 9426 |
| 1100 | 2021-07-26 | 0.0e+00 | 0.0e+00 | 0.097 | 0.114 | 1290 | 1294 | 1295 | 15308 | 8148 |
| 1500 | 2023-03-06 | 0.0e+00 | 0.0e+00 | 0.077 | 0.050 | 890 | 892 | 893 | 11010 | 5628 |
| 1800 | 2024-05-29 | 0.0e+00 | 0.0e+00 | 0.112 | 0.082 | 590 | 589 | 590 | 7208 | 3702 |
| 2100 | 2025-08-12 | 0.0e+00 | 0.0e+00 | 0.103 | 0.114 | 290 | 288 | 289 | 3468 | 1818 |
| 2250 | 2026-03-23 | 0.0e+00 | 0.0e+00 | 0.094 | 0.073 | 140 | 137 | 138 | 1656 | 858 |
| 2330 | 2026-07-22 | 0.0e+00 | 0.0e+00 | 0.100 | 0.068 | 60 | 57 | 58 | 696 | 342 |
| 2389 | 2026-10-15 | 0.0e+00 | 0.0e+00 | 0.097 | 0.096 | 1 | 0 | 0 | 0 | 0 |

For 8 sessions spread over Oct 2020 to 15 Oct 2026 I replaced every bar, index/VIX row, breadth row, peer row and macro observation from the target session onward (macro from the day before) with random junk (the target's own official open and previous close kept for the post-open forecast), re-ran the whole pipeline (all 43 variants and the baseline, both phases) and compared the forecast for that session quantile by quantile: **maximum change 0.0e+00 log units in all 16 cases** (the rule allows 1e-9). The positive control (distorting the PREVIOUS session instead) changes the forecasts by 0.05 to 0.11 log units in every case, so the test would have caught a leak. `results/hl5_leakage.csv`: PASSED.

### 3.6 What the sample could and could not detect (descriptive, from the Final window)

A Holm-corrected test over 172 pairs needs a Diebold-Mariano statistic of about 3.62 for its smallest p. The median standard error of a variant's gain was 0.63 / 0.83 / 0.83 / 0.64 percentage points (pre-open high / low, post-open high / low), so a true gain would have to be about **2.3% / 3.0% / 3.0% / 2.3%** to be confirmable. A smaller true gain (say 1%) could not have been shown by this sample. What the data do say: the point estimates are not positive. Display variant, analogue alone: -5.0% / -1.4% / -3.1% / -2.1%; blended: -1.4% / -0.1% / -1.1% / -0.5%. The 95% intervals for the blended display variant (gain +/- 1.96 s.e.) are -2.96 to +0.20 / -1.74 to +1.52 / -3.31 to +1.14 / -1.86 to +0.78 (%): for the blended display variant an improvement larger than about 1.5% is excluded on every target (largest upper limit 1.52%).

### 3.7 Independent re-computation of the code (verification)

`python3 src/hl_analog.py --selfcheck` re-computes, with separately typed plain loops, (A) 304 feature values on 8 sessions, (B) the analogue quantiles (40, 80, 160 nearest and kernel) of all five spaces in both phases on 9 sessions (including the last, which has missing features), and (C) 100 blend weights, and compares them with the vectorised pipeline: **0 mismatches in 764 comparisons, largest difference 6.4e-14** (`results/hl5_selfchecks.csv`). (D) The features of a live row built from a bundle cut before the target date equal the walk-forward row except for columns that depend on the volatility sigma, which the live call re-fits at the target date (largest relative difference 0.0085). (E) Availability: in the Final window the pre-open feature vectors are complete for every session in spaces V and A, and incomplete for 2 of 320 sessions in B, C and L (the last two sessions, 14 and 15 Oct, whose inputs end early).

## 4. Does matching add anything beyond volatility clustering?

The baseline already uses every past session through its volatility model (S6 sigma) and a trailing-500-session pool of standardised outcomes. The question is whether choosing days by context adds anything on top. Four pieces of evidence, labelled.

### 4.1 The pre-fixed controls (tested, Final window, n = 320)

| target | V alone (volatility state only, 80 nearest) gain % | 80 random past days gain % | all past days, no matching gain % | B alone (display) gain % | C alone (market context) gain % |
|---|---|---|---|---|---|
| H | -6.49 | -4.62 | -3.40 | -5.02 | -1.75 |
| L | -1.24 | -1.44 | +0.36 | -1.37 | -1.16 |
| HO | -3.38 | -4.42 | -3.07 | -3.15 | -1.41 |
| LO | -0.68 | -0.77 | +0.29 | -2.13 | -3.93 |

*Read.* With no matching at all, 80 random past days cost 4.6% (pre-open high) and 4.4% (post-open high) of pinball loss against the baseline: **using only 80 outcomes instead of the baseline's 500 has a noise price**, and the expanding-window pool (all past days, equally weighted) is 3.4% / 3.1% worse (Holm p 0.000 / 0.000) for the high targets, plausibly because the baseline's trailing-500 window follows the recent regime (not proven). Any matching has to earn that back first. The low targets are a tie for every control (gains between -1.4% and +0.4%).

### 4.2 Richer context against the volatility-only control (secondary S1, pre-fixed, own Holm family of 32; tested)

Each cell: gain of that space against the same estimator and form in the volatility-only space V (k80), Final window, n = 320; raw p and Holm p within the 32 tests.

| phase | space | form | H | L | HO | LO |
|---|---|---|---|---|---|---|
| post | A | a |  |  | -2.68% (p 0.082, Holm 1.00) | -3.55% (p 0.057, Holm 1.00) |
| post | A | b |  |  | -2.77% (p 0.008, Holm 0.25) | -0.89% (p 0.143, Holm 1.00) |
| post | B | a |  |  | +0.22% (p 0.890, Holm 1.00) | -1.44% (p 0.453, Holm 1.00) |
| post | B | b |  |  | -1.09% (p 0.338, Holm 1.00) | -0.75% (p 0.373, Holm 1.00) |
| post | C | a |  |  | +1.90% (p 0.149, Holm 1.00) | -3.23% (p 0.101, Holm 1.00) |
| post | C | b |  |  | -0.27% (p 0.684, Holm 1.00) | -2.02% (p 0.061, Holm 1.00) |
| post | L | a |  |  | -0.52% (p 0.710, Holm 1.00) | -1.75% (p 0.342, Holm 1.00) |
| post | L | b |  |  | -1.39% (p 0.104, Holm 1.00) | -0.68% (p 0.411, Holm 1.00) |
| pre | A | a | +1.15% (p 0.421, Holm 1.00) | +0.10% (p 0.936, Holm 1.00) |  |  |
| pre | A | b | -1.02% (p 0.020, Holm 0.61) | +0.03% (p 0.962, Holm 1.00) |  |  |
| pre | B | a | +1.38% (p 0.409, Holm 1.00) | -0.13% (p 0.926, Holm 1.00) |  |  |
| pre | B | b | -1.31% (p 0.102, Holm 1.00) | -0.13% (p 0.870, Holm 1.00) |  |  |
| pre | C | a | +4.45% (p 0.003, Holm 0.08) | +0.08% (p 0.954, Holm 1.00) |  |  |
| pre | C | b | -0.22% (p 0.657, Holm 1.00) | -0.21% (p 0.774, Holm 1.00) |  |  |
| pre | L | a | +1.89% (p 0.233, Holm 1.00) | +0.88% (p 0.653, Holm 1.00) |  |  |
| pre | L | b | -0.75% (p 0.046, Holm 1.00) | +0.45% (p 0.680, Holm 1.00) |  |  |

*Read.* Of the 32 comparisons, 4 have raw p < 0.05 and 0 survive Holm. The pattern is not consistent in sign: in the post-open, 14 of 16 comparisons are worse than volatility alone, in the pre-open 7 of 16. The most favourable cell is set C against V for the pre-open high (+4.5%, raw p 0.003, Holm 0.08); the same set gives +1.9% for the post-open high (raw p 0.149). That is **suggestive, not established, and it does not reach the baseline** (set C alone is -1.7% / -1.4% against the baseline).

### 4.3 Matching against random draws (post hoc: added after the first results; own Holm family of 20; descriptive)

Same idea with random draws of 80 as the reference: does choosing the 80 by context beat choosing them at random?

| phase | space | H | L | HO | LO |
|---|---|---|---|---|---|
| post | A |  |  | -1.66% (p 0.327, Holm 1.00) | -3.46% (p 0.052, Holm 0.94) |
| post | B |  |  | +1.22% (p 0.284, Holm 1.00) | -1.35% (p 0.449, Holm 1.00) |
| post | C |  |  | +2.89% (p 0.010, Holm 0.19) | -3.14% (p 0.084, Holm 1.00) |
| post | L |  |  | +0.49% (p 0.726, Holm 1.00) | -1.67% (p 0.351, Holm 1.00) |
| post | V |  |  | +1.00% (p 0.429, Holm 1.00) | +0.08% (p 0.957, Holm 1.00) |
| pre | A | -0.62% (p 0.636, Holm 1.00) | +0.29% (p 0.843, Holm 1.00) |  |  |
| pre | B | -0.38% (p 0.811, Holm 1.00) | +0.06% (p 0.966, Holm 1.00) |  |  |
| pre | C | +2.74% (p 0.019, Holm 0.37) | +0.27% (p 0.835, Holm 1.00) |  |  |
| pre | L | +0.14% (p 0.925, Holm 1.00) | +1.07% (p 0.594, Holm 1.00) |  |  |
| pre | V | -1.79% (p 0.135, Holm 1.00) | +0.19% (p 0.856, Holm 1.00) |  |  |

### 4.4 What the user would read off the list: the median of the 5 nearest days (secondary S2, pre-fixed; descriptive)

| phase | target | window | n | mae_median_of_5_nearest_rs | se_rs | mae_baseline_median_rs | ratio |
|---|---|---|---|---|---|---|---|
| pre | H | final | 320 | 46.2 | 2.4 | 42.7 | 1.083 |
| pre | L | final | 320 | 51.9 | 2.8 | 47.7 | 1.088 |
| pre | H | valfinal | 568 | 58.6 | 2.7 | 52.9 | 1.108 |
| pre | L | valfinal | 568 | 57.8 | 2.4 | 54.8 | 1.055 |
| pre | H | cas | 52 | 50.2 | 5.8 | 43.7 | 1.148 |
| pre | L | cas | 52 | 54.7 | 5.7 | 48.2 | 1.135 |
| post | HO | final | 320 | 40.5 | 2.3 | 34.8 | 1.164 |
| post | LO | final | 320 | 41.9 | 2.6 | 37.4 | 1.120 |
| post | HO | valfinal | 568 | 51.1 | 2.5 | 44.5 | 1.149 |
| post | LO | valfinal | 568 | 47.2 | 2.0 | 42.6 | 1.107 |
| post | HO | cas | 52 | 38.2 | 4.3 | 35.2 | 1.086 |
| post | LO | cas | 52 | 39.3 | 5.3 | 37.9 | 1.037 |

*Read.* In every window the median of the 5 nearest days misses by more than the baseline median (ratio 1.04 to 1.16; Final: Rs 46.2 / 51.9 / 40.5 / 41.9 against Rs 42.7 / 47.7 / 34.8 / 37.4, standard errors about Rs 2 to 3 in the Final window). Five days are too few; the sensible use of the list is as an illustration, not as a forecast.

### 4.5 Is there any linear information in the features at all? (secondary S3, pre-fixed; descriptive)

Out-of-sample R-squared of the ridge fit of the two standardised outcomes on all features of the learned-metric set (fitted each 20 sessions on earlier sessions only; 0 = no better than the training mean, negative = worse):

| phase | target | window | n | oos_r2_vs_training_mean |
|---|---|---|---|---|
| pre | H | valfinal | 566 | +0.0256 |
| pre | L | valfinal | 566 | -0.0551 |
| pre | H | final | 318 | +0.0324 |
| pre | L | final | 318 | -0.0705 |
| post | HO | valfinal | 566 | -0.0059 |
| post | LO | valfinal | 566 | -0.0136 |
| post | HO | final | 318 | +0.0194 |
| post | LO | final | 318 | -0.0090 |

*Read.* R-squared is between -0.070 and +0.032: the 38 / 43 features carry essentially no linear information about the standardised high and low beyond what sigma already holds. The features the ridge weighted most (mean share relative to equal weights, Final-window blocks) were, pre-open: cloc (3.4x), adv (2.8x), nifty_r1 (2.0x), dlo (1.8x), peers_r1 (1.6x); post-open: adv (2.8x), agz (2.4x), nifty_r1 (2.1x), vix_d1 (2.0x), cloc (2.0x). With an out-of-sample R-squared this close to zero these weights are mostly noise-fitting and should not be read as 'what matters' (`results/hl5_ridge_weights.csv`, `hl5_ridge_blocks.csv`).

### 4.6 Post hoc descriptive tables (added after seeing the first results; not part of the adoption decision)

**How old are the nearest days?** Median age in sessions of the 80 nearest and the share of them from the last 500 sessions (the baseline's own window), Final window; the share among all eligible days is the fair comparison.

| phase | space | n | median_age_sessions_of_80_nearest | share_of_80_nearest_from_last_500_sessions | share_of_all_eligible_from_last_500_sessions |
|---|---|---|---|---|---|
| pre | V | 320 | 733 | 0.377 | 0.288 |
| pre | A | 320 | 775 | 0.346 | 0.288 |
| pre | B | 320 | 454 | 0.550 | 0.324 |
| pre | C | 320 | 511 | 0.501 | 0.324 |
| pre | L | 320 | 632 | 0.437 | 0.324 |
| post | V | 320 | 752 | 0.366 | 0.288 |
| post | A | 320 | 761 | 0.346 | 0.288 |
| post | B | 320 | 494 | 0.521 | 0.324 |
| post | C | 320 | 531 | 0.489 | 0.324 |
| post | L | 320 | 632 | 0.435 | 0.324 |

*Read.* The nearest days are more recent than a random draw from the same pool would be, most of all for sets B and C: share of the 80 nearest from the last 500 sessions against the share among all eligible days (pre-open, Final window) is 38% vs 29% (V), 35% vs 29% (A), 55% vs 32% (B), 50% vs 32% (C), 44% vs 32% (L). Features such as the volume z-scores and the distance from the 250-day high drift over time, so matching on them partly selects recent days, which is the kind of recency the baseline's trailing-500 window already has (descriptive; not tested).

**Gain against the baseline by calendar year** (display variants and the no-matching control; positive = better; n per year 195 to 248):

| phase | target | variant | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|---|---|---|---|
| post | HO | B_k80_a | +0.71 | -1.80 | -2.35 | +1.14 | +2.21 | -0.69 | -4.57 |
| post | HO | B_k80_b | +0.37 | -0.82 | +0.06 | +0.07 | +1.46 | -0.11 | -1.55 |
| post | HO | POOL_a | +0.12 | +0.19 | +0.26 | -0.10 | +0.07 | -1.12 | -3.67 |
| post | LO | B_k80_a | -1.31 | +0.68 | +1.40 | +0.47 | +0.28 | -0.99 | -2.30 |
| post | LO | B_k80_b | -0.34 | -0.15 | +1.23 | +0.81 | +0.74 | -0.20 | -0.41 |
| post | LO | POOL_a | -0.22 | -0.09 | -0.35 | -0.66 | +0.01 | +0.31 | +0.13 |
| pre | H | B_k80_a | +0.74 | -2.53 | -3.50 | +1.06 | +1.46 | -1.93 | -5.84 |
| pre | H | B_k80_b | +0.67 | -0.79 | -0.10 | +0.08 | +0.93 | -0.37 | -1.53 |
| pre | H | POOL_a | -0.17 | +0.13 | +0.58 | +0.26 | -0.00 | -0.82 | -3.58 |
| pre | L | B_k80_a | -2.90 | -1.71 | +0.69 | -0.22 | +1.21 | -0.22 | -0.10 |
| pre | L | B_k80_b | -0.95 | +0.00 | +0.04 | +0.08 | +1.48 | +0.61 | +0.79 |
| pre | L | POOL_a | -0.31 | +0.07 | -0.05 | -0.30 | +0.17 | +0.65 | +0.15 |

*Read.* The signs flip from year to year for the display variants (alone and blended), and the analogue-alone version is at its worst in 2026 (pre-open high -5.8%). The no-matching control (all past days) also deteriorates in 2026 (-3.6%), consistent with recent sessions being more informative than old ones for the high, which the baseline's trailing window already exploits and matching does not repair (descriptive).

## 5. The comparable days for Fri 16 Oct 2026 (as of the 15 Oct close and the official open Rs 3,450.0)

**Inputs.** Reference close Rs 3,428.0 (15 Oct); baseline normal move sigma = 2.43% close-to-close and 2.22% open-to-close; official open Rs 3,450.0, a gap of +0.64%, **above yesterday's high of Rs 3,445.0** (so the post-open feature 'open beyond yesterday's range' is +1). Display version fixed in Section 0: set B (BSE-own features), the 80 nearest days. **Feature gap on the day:** the delivery-percentage feature `delz` is missing (the bar files carry no delivery % for 13, 14 and 15 Oct), so the pre-open display set uses 13 of its 14 features and the post-open one 18 of 19; the pool of days that can be compared is 1,885. Sets C and L lose every market, breadth, peer and US feature (those files end 12 to 13 Oct) and so collapse to the BSE-own features plus the calendar; their lists are in the JSON but add little.

### 5.1 The 10 most similar past days, before the open (set B; distance = shrunk Mahalanobis; 'more similar than' = share of the compared past days that are further away)

| rank | date | day | distance | similarity (1 = identical) | more similar than % of past days | its gap % | its close vs prev close % | its HIGH % of prev close | its LOW % of prev close |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 2026-10-06 | Tue | 1.49 | 0.830 | 99.9 | +0.92 | +3.94 | +3.94 | +0.85 |
| 2 | 2026-04-07 | Tue | 1.58 | 0.811 | 99.9 | -0.78 | -1.06 | -0.16 | -2.16 |
| 3 | 2026-08-25 | Tue | 1.63 | 0.799 | 99.8 | +0.07 | -0.29 | +0.34 | -0.83 |
| 4 | 2021-04-23 | Fri | 1.65 | 0.795 | 99.8 | -0.14 | -0.40 | +1.11 | -0.97 |
| 5 | 2024-08-19 | Mon | 1.67 | 0.791 | 99.7 | +0.98 | +1.14 | +2.80 | +0.00 |
| 6 | 2023-06-13 | Tue | 1.71 | 0.781 | 99.7 | +0.51 | -1.31 | +0.80 | -2.00 |
| 7 | 2026-03-17 | Tue | 1.73 | 0.778 | 99.6 | +0.96 | +3.88 | +4.10 | +0.19 |
| 8 | 2026-03-18 | Wed | 1.76 | 0.770 | 99.6 | +0.29 | +0.74 | +1.19 | -0.52 |
| 9 | 2020-09-15 | Tue | 1.77 | 0.767 | 99.5 | +1.83 | +5.73 | +7.97 | -0.51 |
| 10 | 2026-09-23 | Wed | 1.80 | 0.761 | 99.5 | +0.43 | +1.10 | +1.39 | -0.64 |

*The five most similar past days ended with a high of -0.16% to +3.94% (median +1.11%) and a low of -2.16% to +0.85% (median -0.83%) of the previous close (at Rs 3,428: high about Rs 3,466, low about Rs 3,400); the ten: median high +1.29%, median low -0.58%. For scale, all 1,885 past days compared: median high +1.59% (middle 90%: -0.18% to +6.80%), median low -1.14% (middle 90%: -5.37% to +0.73%). The five days are as spread out as the whole history: they do not narrow the picture. In the walk-forward test the median of the 5 nearest was a worse guess than the baseline median (Section 4.4).*

### 5.2 The 10 most similar past opens, after the 09:08 open (set B plus gap, size of gap, open beyond yesterday's range, open's place in yesterday's range, volatility of the open-to-close move)

| rank | date | day | distance | similarity (1 = identical) | more similar than % of past days | its gap % | its close vs prev close % | its HIGH % of open | its LOW % of open |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 2026-10-06 | Tue | 1.55 | 0.890 | 99.9 | +0.92 | +3.94 | +2.99 | -0.08 |
| 2 | 2026-03-17 | Tue | 1.81 | 0.853 | 99.9 | +0.96 | +3.88 | +3.11 | -0.76 |
| 3 | 2024-11-06 | Wed | 1.95 | 0.831 | 99.8 | +0.98 | +1.77 | +3.59 | -0.64 |
| 4 | 2026-09-15 | Tue | 1.96 | 0.829 | 99.8 | +0.98 | -2.19 | +1.04 | -3.57 |
| 5 | 2026-03-18 | Wed | 1.96 | 0.829 | 99.7 | +0.29 | +0.74 | +0.90 | -0.81 |
| 6 | 2024-11-19 | Tue | 1.97 | 0.828 | 99.7 | +0.89 | +0.45 | +2.32 | -1.15 |
| 7 | 2022-07-20 | Wed | 1.98 | 0.827 | 99.6 | +1.09 | +0.16 | +1.02 | -1.40 |
| 8 | 2026-08-03 | Mon | 1.99 | 0.825 | 99.6 | +0.38 | -1.95 | +0.31 | -2.73 |
| 9 | 2020-07-20 | Mon | 1.99 | 0.824 | 99.5 | +0.64 | +2.55 | +2.55 | -0.34 |
| 10 | 2025-11-17 | Mon | 2.05 | 0.814 | 99.5 | +0.31 | -0.56 | +0.00 | -1.45 |

*The five most similar past openings ended with a high of +0.90% to +3.59% (median +2.99%) and a low of -3.57% to -0.08% (median -0.76%) of the open (at Rs 3,450: high about Rs 3,553, low about Rs 3,424); the ten: median high +1.68%, median low -0.98%. All 1,885 past days: median high +1.30%, median low -1.32%.*

### 5.3 Other sets pick other days (top 5, pre-open and post-open; the dates are in `results/hl5_2026-10-16_analogues.csv`)

| set | phase | features used | 5 nearest days | median high % | median low % |
|---|---|---|---|---|---|
| V | pre-open | 1 | 2025-04-28, 2023-03-10, 2023-03-15, 2021-06-18, 2022-05-16 | +3.22 | -2.24 |
| V | post-open | 1 | 2020-11-24, 2021-10-22, 2020-09-14, 2021-04-07, 2025-03-26 | +2.93 | -3.14 |
| A | pre-open | 6 | 2019-06-26, 2024-09-10, 2022-02-03, 2024-11-19, 2020-09-15 | +3.23 | -0.51 |
| A | post-open | 11 | 2024-11-19, 2020-09-02, 2024-02-28, 2019-04-10, 2024-11-06 | +2.32 | -1.00 |
| B | pre-open | 13 | 2026-10-06, 2026-04-07, 2026-08-25, 2021-04-23, 2024-08-19 | +1.11 | -0.83 |
| B | post-open | 18 | 2026-10-06, 2026-03-17, 2024-11-06, 2026-09-15, 2026-03-18 | +2.99 | -0.76 |
| C | pre-open | 18 | 2021-04-23, 2022-06-10, 2026-04-10, 2025-01-24, 2024-08-23 | +2.23 | -0.97 |
| C | post-open | 23 | 2026-04-10, 2024-12-06, 2024-11-08, 2026-05-15, 2025-12-12 | +1.04 | -2.30 |
| L | pre-open | 18 | 2019-06-21, 2026-09-04, 2026-03-27, 2022-07-20, 2026-01-28 | +2.12 | -0.33 |
| L | post-open | 23 | 2024-11-19, 2024-11-06, 2019-04-10, 2026-09-15, 2026-10-06 | +2.32 | -0.64 |

*The lists share almost no days across sets: the 'nearest five' depend on which features are used, which is another reason not to read them as forecasts.*

### 5.4 The forecast the 80 nearest days give, next to the baseline (rupees; description of the method's output; the baseline stays the headline)

| when | side | model | 5% | 25% | median | 75% | 95% |
|---|---|---|---|---|---|---|---|
| before the open | HIGH | baseline (headline) | 3,421 | 3,449 | 3,475 | 3,513 | 3,591 |
| before the open | HIGH | comparable days alone (B, 80) | 3,436 | 3,461 | 3,489 | 3,519 | 3,590 |
| before the open | HIGH | blend | 3,421 | 3,449 | 3,475 | 3,513 | 3,591 |
| before the open | LOW | baseline (headline) | 3,269 | 3,352 | 3,390 | 3,419 | 3,450 |
| before the open | LOW | comparable days alone (B, 80) | 3,308 | 3,371 | 3,401 | 3,421 | 3,448 |
| before the open | LOW | blend | 3,288 | 3,362 | 3,395 | 3,420 | 3,449 |
| after the open (Rs 3,450.0) | HIGH | baseline (headline) | 3,451 | 3,468 | 3,488 | 3,526 | 3,591 |
| after the open (Rs 3,450.0) | HIGH | comparable days alone (B, 80) | 3,450 | 3,468 | 3,483 | 3,532 | 3,598 |
| after the open (Rs 3,450.0) | HIGH | blend | 3,451 | 3,468 | 3,488 | 3,527 | 3,592 |
| after the open (Rs 3,450.0) | LOW | baseline (headline) | 3,294 | 3,374 | 3,410 | 3,430 | 3,447 |
| after the open (Rs 3,450.0) | LOW | comparable days alone (B, 80) | 3,310 | 3,378 | 3,412 | 3,433 | 3,447 |
| after the open (Rs 3,450.0) | LOW | blend | 3,296 | 3,374 | 3,410 | 3,430 | 3,447 |

*Blend weights on the comparable-days side, fitted on the trailing 500 scored sessions before the target (separately per target): pre-open high 0.0, low 0.5; post-open high 0.1, low 0.1. Typical misses measured out of sample on 320 sessions (Final window) are in the JSON next to each band (the JSON converts post-open misses at the open, Rs 3,450, so they read slightly larger than the Rs 3,428 figures elsewhere in this report): baseline 42.7 / 47.7 / 35.0 / 37.7, comparable days alone 43.4 / 47.6 / 34.7 / 37.7 Rs. The 5%-to-95% band of the post-open high is a 19-in-20 band, not 9-in-10, because the open can itself be the high (Section 3.1). The medians of the two methods differ by Rs 14 (pre-open high), 11 (low), 5 (post-open high), 2 (post-open low).*

### 5.5 The same forecast by feature set (80 nearest days alone; rupees; median and 5%-95% band)

| phase | set | HIGH median | HIGH 5-95% | LOW median | LOW 5-95% |
|---|---|---|---|---|---|
| pre-open | V | 3,491 | 3,413 to 3,645 | 3,395 | 3,239 to 3,478 |
| pre-open | A | 3,479 | 3,434 to 3,628 | 3,395 | 3,287 to 3,444 |
| pre-open | B | 3,489 | 3,436 to 3,590 | 3,401 | 3,308 to 3,448 |
| pre-open | C | 3,480 | 3,426 to 3,562 | 3,397 | 3,311 to 3,438 |
| pre-open | L | 3,479 | 3,436 to 3,562 | 3,402 | 3,311 to 3,455 |
| post-open | V | 3,498 | 3,451 to 3,649 | 3,412 | 3,271 to 3,450 |
| post-open | A | 3,483 | 3,450 to 3,657 | 3,412 | 3,293 to 3,447 |
| post-open | B | 3,483 | 3,450 to 3,598 | 3,412 | 3,310 to 3,447 |
| post-open | C | 3,488 | 3,450 to 3,592 | 3,411 | 3,277 to 3,447 |
| post-open | L | 3,490 | 3,451 to 3,573 | 3,411 | 3,315 to 3,447 |

*The medians differ by at most Rs 12 (pre-open high), 7 (pre-open low), 14 (post-open high), 1 (post-open low) between feature sets; the tails differ more. The typical miss of the baseline is Rs 35 to 48. This is the picture of Section 4: the context changes the answer a little, and not in a way the history shows to be more accurate.*

### 5.6 Today's feature values (set B and the others; blank = not available on the day)

| feature | group | value used (unfilled) | value with the early-ending inputs completed (sensitivity) |
|---|---|---|---|
| rng1 | BSE own | +0.456 | +0.456 |
| cloc | BSE own | +0.871 | +0.871 |
| gap1 | BSE own | +0.049 | +0.049 |
| r5 | BSE own | +0.506 | +0.506 |
| r20 | BSE own | +0.518 | +0.518 |
| lnsig_rel | volatility state | +0.004 | +0.004 |
| pk5 | BSE own | -0.313 | -0.313 |
| gk20 | BSE own | -0.241 | -0.241 |
| volz | BSE own | +0.516 | +0.516 |
| turnz | BSE own | +0.556 | +0.556 |
| delz | BSE own |  | -1.135 |
| dhi | BSE own | -2.390 | -2.390 |
| dlo | BSE own | +3.561 | +3.561 |
| streak | BSE own | +1.000 | +1.000 |
| dow_mon | calendar | +0.000 | +0.000 |
| dow_tue | calendar | +0.000 | +0.000 |
| dow_wed | calendar | +0.000 | +0.000 |
| dow_thu | calendar | +0.000 | +0.000 |
| mend | calendar | +0.000 | +0.000 |
| nifty_r1 | market |  | +2.270 |
| nifty_rng1 | market |  | +2.535 |
| bank_r1 | market |  | +1.204 |
| bank_rng1 | market |  | +1.912 |
| vix_ln | market |  | +2.641 |
| vix_d1 | market |  | -0.042 |
| vix_rv | market |  | -0.127 |
| adv | breadth |  | +0.305 |
| tailbal | breadth |  | -0.031 |
| mktturn_z | breadth |  | +0.276 |
| peers_r1 | peers |  | +0.287 |
| peers_rng1 | peers |  | -0.169 |
| sp_r1 | US overnight |  | -1.606 |
| usvix_ln | US overnight |  | +2.825 |
| usvix_d1 | US overnight |  | +0.100 |
| us10y_d5 | slow macro |  |  |
| brent_r5 | slow macro |  |  |
| dxy_r5 | slow macro |  |  |
| inr_r5 | slow macro |  |  |
| gz | post-open | +0.263 | +0.263 |
| agz | post-open | +0.263 | +0.263 |
| obeyond | post-open | +1.000 | +1.000 |
| orel | post-open | +1.038 | +1.038 |
| lnsI_rel | post-open | +0.050 | +0.050 |

*Definitions and timestamp rules of every feature: `results/hl5_features.csv`.*

### 5.7 Sensitivity: what if the early-ending inputs are completed? (descriptive; not part of any test)

The index/VIX, breadth, peer, S&P 500 / US VIX and delivery-% inputs end before 15 Oct. Another specialist's fetch (`results/hl2_fill_*.csv`; I did not verify those files, their sha256 are in the JSON) supplies the missing rows (index rows: 2026-10-13, 2026-10-14, 2026-10-15, breadth rows: 2026-10-14, 2026-10-15, peers dates: 2026-10-14, 2026-10-15, US SP500 dates: 2026-10-13, 2026-10-14, 2026-10-15, US VIX dates: 2026-10-13, 2026-10-14, 2026-10-15, delivery pct dates: 2026-10-13, 2026-10-14, 2026-10-15). I re-ran the 16 Oct forecast with them added under the same timestamp rules (`python3 src/hl_analog.py --live-filled` -> `results/hl5_2026-10-16_filled.json`, `..._filled_analogues.csv`). Result:

* Set B now has all 14 features and the pool shrinks to 1,693 days (sessions before Dec 2019 have no delivery %). **Its five nearest days change to 2021-04-23, 2024-08-19, 2023-06-13, 2026-03-17, 2020-09-15** (before: 2026-10-06, 2026-04-07, 2026-08-25, 2021-04-23, 2024-08-19): 2 of 5 in common. Their median high / low: +2.80% / -0.51% (before +1.11% / -0.83%). One feature changed the comparable days; the "five nearest" are fragile.
* The 80-nearest forecast is much more stable: pre-open high median Rs 3,487 (before 3,489), low Rs 3,405 (before 3,401); post-open high Rs 3,485 (before 3,483), low Rs 3,412 (before 3,412).
* Set C, now complete (34 features), picks 2024-12-06, 2025-01-03, 2024-12-16, 2026-03-17, 2021-04-16 before the open (median high +1.89%, low -0.27%); its distances are large (nearest 4.67 in 34 dimensions, against 1.65 in 14), i.e. no past day really resembles today in all respects. Today's market context is unusual: on 15 Oct Nifty rose +2.3 standard deviations of its recent daily moves while the advance share was only 0.30, and the S&P 500 moved -1.6 standard deviations in the US session of 14 Oct (the last one the 2-day lag rule allows).

## 6. Departures from Section 0, and what was added after results were seen

Section 0 above is unchanged. Everything that differs from it, or was added after I had seen results, is listed here.

1. **Feature counts in Section 0.3/0.4 are wrong; the feature lists are right.** Section 0.3 says C has 31 and L 35 features and 0.4 says 35 / 40 candidate features. The named features add up to B = 14, C = 14 + 5 calendar + 12 market + 3 US = 34, L = 38 (pre-open) and 43 with the 5 post-open features (`results/hl5_features.csv` lists all 43). The variants, the family size (172) and every rule are unaffected.
2. **Set B is not complete on 16 Oct** (Section 0.3 said V, A, B are). The delivery-% feature `delz` is valid only from 2019-12-03 (the bar files carry no delivery % in 2017 to Sept 2019) and is missing again for the last three sessions (194 of the sessions from the 500th on have no value). Consequences: the 16 Oct display result uses 13 of 14 features (the missing-feature rule of Section 0.3 handles it); the pools for sets B, C and L start in Dec 2019 rather than Feb 2019; and the first block of 20 evaluated sessions (25 Feb to 24 Mar 2020, Development window) has fewer than 60 complete training rows, so those 20 sessions fall back to the baseline in B, C and L (the 'fallbacks 20' in the run logs). Validation and Final are unaffected.
3. **Market files end early.** Index/VIX end 12 Oct, breadth and peers 13 Oct, FRED series 2 to 12 Oct. In the Final window the feature vectors of sessions 14 and 15 Oct are therefore incomplete in C and L (sub-vector distance, as pre-fixed): 2 of 320 Final sessions. On 16 Oct sets C and L reduce to BSE-own plus calendar features (as Section 0.3 anticipated).
4. **`cloc` (close location in yesterday's range) is measured in log prices** (ln(C/L)/ln(H/L)), which is what the bar-adjusted log series gives; Section 0.3 did not say. Within one session this is exactly the same as the log version of the raw-price ratio.
5. **Data cut.** `STUDY_END = 2026-10-16` was added to the code so that every study run uses sessions strictly before 16 Oct, whatever the data files later contain (the file `bse_daily_extra.csv` gained a 16 Oct row after my first runs). Re-running with the cut reproduced my earlier result files byte for byte (sha256 of `hl5_eval_summary.csv`, `hl5_dm_holm.csv`, `hl5_predictions.csv` unchanged). I did not use or score the 16 Oct session; I saw the new row once in a printout of the end of the file while checking dates, and nothing in the code or the report uses it. The committed 16 Oct JSON from before that row existed is reproduced by the same code to the last digit (only added keys differ).
6. **Added after the first results (post hoc, labelled where used):** secondary analyses S4 (matching against random draws), S5 (gain by year) and S6 (age of the neighbours) in Section 4.3 and 4.6; the independent re-computation `--selfcheck` (Section 3.7), the headline table `hl5_headline.csv`, the sensitivity `--live-filled` (Section 5.7) and the extra JSON fields (`features_today`, `k80_analogue_alone_by_space`, `all_compared_sessions`). None of them changes a forecast or the adoption decision. The adoption table was produced by the rule exactly as in Section 0.1.
7. **Two leakage-test attempts crashed before the third passed** (pandas refused to put float junk into integer columns of the test harness; fixed in `junkify`). No forecast code changed in between; the evaluation files of the first full run and of the final run are byte-identical (sha256 of `hl5_eval_summary.csv`, `hl5_dm_holm.csv`, `hl5_predictions.csv` recorded in my scratch directory after run 1).
8. **Order of knowledge.** The pre-fixed text is in git commit 2072844 (committer time 08:00 UTC on 16 Oct); the first result files in git are in commit 68032e4 (08:27 UTC). The text file's own modification time (05:39 UTC) is my working record, not an independent one. I have no complete record of what was run between those two times (code writing and short debugging runs); the first full-evaluation log in my scratch directory is from about 08:02 UTC.
9. **One unsupported sentence removed.** The first version of the 16 Oct JSON `reading` text said the five nearest days' range was "about as wide as the whole spread of past days"; that was not backed by a number in a file. It now quotes the middle 90% of all compared past days and the walk-forward misses (Section 5.1).

## 7. What failed, and honest limits

* **Nothing was adopted.** 0 of 172 pairs. The analogue methods did not beat the baseline on any target; for the pre-open and post-open highs most analogue-alone variants are significantly worse (Section 3.2).
* **The likely reason, said carefully (not proven).** The baseline's trailing-500 pool of standardised outcomes after the S6 sigma already carries the predictable part; the features add almost no linear information about the standardised extremes (Section 4.5), and picking 40 to 160 outcomes instead of 500 costs sampling noise (Section 4.1). A 'more parameters' version of this idea has to beat that noise price before it can help.
* **Limited power.** A gain below about 2.3% to 3.0% could not have been confirmed with 320 Final sessions and 172 tests (Section 3.6). The data exclude a gain of more than about 1.5% for the blended display variant, not a gain of 0.5%.
* **"Out-of-sample tested", not "validated".** The Final window was also used earlier in the project to choose the baseline model (`verify_A_dayahead.md`), which favours the baseline slightly against anything tried later.
* **Overlap and dependence.** The last 5 sessions are excluded from the pool, and the DM test uses a lag-5 Newey-West variance; features such as the 5- and 20-day returns still overlap between neighbouring days, so the effective number of independent comparable days is smaller than the count of days used.
* **Short samples and untested items.** BSE option implied volatility and skew (461 sessions from 29 Nov 2024) and F&O expiry flags (from 18 Nov 2024) were not tested: with the 5-session exclusion and 150+ days needed the pool would be too small and the Validation window empty. The Capital Markets index (history from Apr 2023), the NSE pre-open order book (2 snapshots), GIFT Nifty and FII/DII flows (no verified dated series) are **untested**. The US overnight features use a conservative lag (the last observation dated at least 2 days before the session; FRED publication lag is not provably zero), which discards the freshest US session.
* **Live-day limits.** On 16 Oct the pre-open display set uses 13 of 14 features and sets C and L are reduced to BSE-own plus calendar (Section 5); the comparable days change with one feature (Section 5.7). `analog_forecast()` re-fits the standardisation, covariance and blend weight at the target session itself, whereas the walk-forward fits them every 20 sessions, so its quantiles differ from a walk-forward row of the same date: median difference Rs 0.11, 95th percentile Rs 3.0, largest Rs 47.7 (one deep-tail quantile where a single neighbour changes; `results/hl5_live_checks.csv`, 5 replayed dates x 2 forms x 2 phases x 2 targets x 5 quantiles).
* **Costs not considered.** This is about the precision of the forecast, not about trading profit; nothing here is a direction call.

## 8. Numbers to quote (each with n and its file)

All Final window (1 Jul 2025 to 15 Oct 2026, n = 320), rupees at Rs 3,428, out-of-sample walk-forward, source `results/hl5_eval_summary.csv`, `hl5_dm_holm.csv`, `hl5_adoption.csv`, `hl5_headline.csv`.

1. **Adoption.** 0 of 172 variant-target pairs meet the pre-fixed rule (family size 172; 38 pre-open and 43 post-open candidate features). Best pinball gain of any variant: +0.02% (pre-open high), +0.78% (pre-open low), +0.41% (post-open high), +0.39% (post-open low); needed at least +2% with Holm p < 0.05.
2. **Baseline (kept).** Typical miss of the median: pre-open high Rs 42.7, low Rs 47.7; after the open: high Rs 34.8, low Rs 37.4 ('price stays' Rs 62.9 / 61.3).
3. **Comparable days, display version (set B, 80 nearest), typical miss:** alone Rs 43.4 / 47.6 / 34.4 / 37.5; blended Rs 42.8 / 47.4 / 34.5 / 37.2. Pinball gain against the baseline: alone -5.0% / -1.4% / -3.1% / -2.1%; blended -1.4% / -0.1% / -1.1% / -0.5%.
4. **Range over all 43 variants of the typical miss:** high Rs 41.8 to 44.0; low 47.2 to 49.3; post-open high 34.2 to 35.7; post-open low 37.2 to 39.4.
5. **Median of the 5 nearest days** misses by Rs 46.2 / 51.9 / 40.5 / 41.9 (baseline median 42.7 / 47.7 / 34.8 / 37.4); `hl5_secondary_5nearest_point.csv`.
6. **Beyond volatility clustering:** no detectable gain (S1: 0 of 32 comparisons significant after Holm; ridge out-of-sample R-squared -0.070 to +0.032).
7. **16 Oct 2026 (as of the 15 Oct close Rs 3,428.0; open Rs 3,450.0)**, comparable days alone vs baseline medians: pre-open high Rs 3,489 vs 3,475; low 3,401 vs 3,390; after the open high 3,483 vs 3,488; low 3,412 vs 3,410. The 5 nearest days (set B, 13 features): 2026-10-06, 2026-04-07, 2026-08-25, 2021-04-23, 2024-08-19; median high +1.11% / low -0.83% of the previous close (range of the five: -0.16% to +3.94% / -2.16% to +0.85%); `results/hl5_2026-10-16.json`.

**Do not quote:** the 5-nearest-day medians as a forecast (Section 4.4); the ridge feature weights as 'what matters' (R-squared about zero); set C against the volatility-only control as a finding (Holm 0.08, one of 52 secondary tests); the list of comparable days as stable (Section 5.7); anything about the 16 Oct session outcome (not used here).

**Contradictions with project claims.** None. My baseline reproduction agrees with `A_dayahead.md` and `verify_A_dayahead.md` to the last digit, and the null result agrees with `B_liveintraday.md` (context added to the live bands did not help after Holm) and with the 'no variant adopted' result of specialist A. I did not find any earlier project claim that systematic analogue matching helps. (The 16 hand-picked, dated event analogues in `FORECAST_REPORT.md` for the SEBI scenario overlay are a different thing, chosen after the fact; this study does not test them.)

## 9. Reproduce

From the repo root, no network access, python3 with numpy, pandas, scipy (about 15 minutes in all; the leakage test takes 6 to 8 minutes):

```
python3 src/hl_analog.py --eval        # walk-forward evaluation of all variants -> results/hl5_eval_summary.csv, hl5_dm_holm.csv, hl5_predictions.csv, hl5_baseline_repro.csv, hl5_posthoc_*.csv, hl5_secondary_*.csv ...
python3 src/hl_analog.py --leak        # leakage test, 8 sessions                 -> results/hl5_leakage.csv
python3 src/hl_analog.py --adopt       # the pre-fixed rule, 172 pairs            -> results/hl5_adoption.csv
python3 src/hl_analog.py --live        # 16 Oct 2026, close Rs 3,428.0, open Rs 3,450.0 -> results/hl5_2026-10-16.json, hl5_2026-10-16_analogues.csv
python3 src/hl_analog.py --live-filled # sensitivity with the early-ending inputs completed -> results/hl5_2026-10-16_filled.json
python3 src/hl_analog.py --check       # analog_forecast() vs walk-forward rows, baseline vs hl_model.hl_forecast -> results/hl5_live_checks.csv
python3 src/hl_analog.py --selfcheck   # independent loop re-computation        -> results/hl5_selfchecks.csv
python3 src/hl_analog.py --tables      # report tables + results/hl5_headline.csv
python3 src/hl_analog.py --date 2026-10-16 --open 3450.0          # plain words for any date (only earlier sessions are used)
```

In Python: `from hl_analog import analog_forecast; analog_forecast('2026-10-16', 3450.0)` returns the same keys as `hl_model.hl_forecast` (pre_open, post_open, sigma, hashes ...) plus `variants` (comparable days alone, blend, baseline), `analogues` (the dated comparable days for each feature set), `reading`, `features_today`. The result files are deterministic: a second run reproduces them byte for byte.

How this report was made: every number in the result block and Sections 1 to 8 was written into the text by a script that reads the result files listed below (nothing typed by hand); that script is a helper kept in my scratch directory, not part of the repo, and the files it reads are all reproduced by the commands above. The hl_analog.py `--tables` option prints the same tables.

Files written by this study: `src/hl_analog.py`; `results/hl5_eval_summary.csv`, `hl5_dm_holm.csv`, `hl5_adoption.csv`, `hl5_blend_weights.csv`, `hl5_variants.csv`, `hl5_features.csv`, `hl5_predictions.csv`, `hl5_baseline_repro.csv`, `hl5_leakage.csv`, `hl5_selfchecks.csv`, `hl5_live_checks.csv`, `hl5_headline.csv`, `hl5_secondary_*.csv`, `hl5_posthoc_*.csv`, `hl5_ridge_*.csv`, `hl5_2026-10-16.json`, `hl5_2026-10-16_analogues.csv`, `hl5_2026-10-16_filled.json`, `hl5_2026-10-16_filled_analogues.csv`; this report.
