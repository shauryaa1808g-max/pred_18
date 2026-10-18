# Specialist D: do extra parameters make the day's high and low more precise? (NSE:BSE)

*Status: SECTION 0 (the pre-fixed rule, the feature menu with timestamp rules, the model, and the list of variants) was written BEFORE any variant was evaluated on the real data. Clock when written: Fri 16 Oct 2026 08:18 UTC = 13:48 IST (the brief said "about 11:00 IST"; the machine clock is the one used). The session of 16 Oct is in progress: nothing dated 16 Oct is used anywhere (official history through the 15 Oct close; US data through the 15 Oct US session, which closed at 01:30 IST on 16 Oct). The results sections are appended below Section 0; they were completed by a second session on 16 Oct 2026 (see Section 1). A third session on 17 Oct 2026 re-verified the stored results and scored the single fresh day of 16 Oct after the adoption decision (Section 14); it changed no result and no verdict. Start with Section 2, 'The answer in plain words'.*

**What had been run before this text was written (disclosed):** the baseline reproduction (Section 0.9, identical to the stored numbers); a timing and sanity run of five variants on sessions 1700 to 1759 (only "finite" and "quantiles ordered" were printed, no loss was looked at); synthetic-data tests of the regression code (a known effect is recovered, pure noise is shrunk); coverage and timestamp spot checks of the feature panel (share of non-missing values, a few dates compared by hand with the source tables). No pinball, coverage or miss of any variant on real data had been seen.

## 0. Pre-fixed section

### 0.1 Question, targets, windows
Does adding information beyond the baseline (src/hl_model.py: S6 volatility x filtered historical simulation) make the forecast of the session HIGH and LOW more precise, for the four targets
* pre-open high Hp = ln(H/P0) and low Lp = ln(L/P0) (information to the previous official close P0), baseline `P_S6`;
* post-open high HO = ln(H/O) and low LO = ln(L/O) (plus the official open O, final 09:08 IST), baseline `W_I6`.

Evaluation sessions: walk-forward, expanding, session 750 onward (25 Feb 2020, as the baseline) to 15 Oct 2026 (n = 1,640). Windows (by target date): Validation 2024-07-01 to 2025-06-30 (n = 248), Final 2025-07-01 to 2026-10-15 (n = 320), Development before 2024-07-01 (n = 1,072, descriptive), post closing-auction slice from 2026-08-03 (n = 52). Rupees: log errors times Rs 3,428 (the 15 Oct close). The baseline is the benchmark; "price stays" and the trailing-250 empirical quantiles (`P_EMP250`, `W_EMP250`) are reported as additional benchmarks.

### 0.2 Adoption rule (verbatim from the brief, with my operational reading)
A variant counts as an improvement for a target ONLY IF ALL hold:
1. **(i)** pinball loss (mean over the 9-level grid 2.5 ... 97.5%) in the Final window is at least 2% lower than the baseline's, with Diebold-Mariano (HAC lag 5, Harvey-Leybourne-Newbold, `src/metrics.py`) two-sided p < 0.05 AFTER Holm across EVERY variant-target pair tried. *Reading:* gain >= 2.0%, DM statistic positive, Holm-adjusted two-sided Final-window p < 0.05, Holm over all **46** pairs of Section 0.5 (the 23 candidate variants x their 2 targets). The two placebo diagnostics are not candidates, are not in the family and cannot be adopted.
2. **(ii)** the Validation window shows the same sign of improvement. *Reading:* the variant's mean pinball in Validation is strictly lower than the baseline's. For the own-window variants (short samples, 0.4) the variant must also have used at least one feature on at least half of the Validation sessions; otherwise (ii) is "not testable" = not met.
3. **(iii)** Final coverage of the 50% and 90% central bands is not worse than the baseline's and Kupiec p > 0.05. *Reading:* for BOTH bands, |coverage - nominal| of the variant <= |coverage - nominal| of the baseline, AND the unconditional-coverage p-value > 0.05. Pre-open targets: nominal 50% / 90% and the Kupiec test of `src/metrics.py`. Post-open targets (HO and LO have an atom at zero because the open is the day's high / low on about 4% / 2% of sessions, so the 5-95% band of HO is not a 90% band): the **atom-at-zero-aware check**, i.e. nominal = the coverage the model's OWN draws assign to the band on each day (P(draws <= q_hi) - P(draws < q_lo)), and a z-test on sum(hits) - sum(nominal) with Poisson-binomial variance; this is also what the "nominal" and "dev" columns report for all targets.
4. **(iv)** in the post-closing-auction slice (2026-08-03 on, n = 52) the pinball loss is not more than 5% worse than the baseline's (ratio <= 1.05).
5. **(v)** a leakage test passes: all input data from the target session onward is replaced by junk (random OHLC for BSE, index, breadth, peers, F&O IV, US and FRED series, expiry and results flags; for post-open variants the target session's own open and previous close are kept because they are legitimately known), the whole pipeline is rerun and the forecasts for the target session must be unchanged (max absolute difference < 1e-9 in log points) for EVERY variant. Sessions tested: spread over Development, Validation, Final and the auction slice, plus the live 16 Oct forecast.

The adoption decision is made separately for each of the four targets. Only a variant that meets all five for a target may replace the baseline for that target. Everything else is reported as a tie, a null or worse. Also reported for every variant: the typical rupee miss of the median (mean absolute error of the 50% quantile at Rs 3,428) and the half-the-time miss.

### 0.3 Feature menu and timestamp rule of every feature (each is known before the t open at 09:00 IST unless marked)
Dates are IST sessions; "t-1" = the previous BSE session. A table dated t-1 is read at exactly that date (a missing t-1 row makes the feature missing, never stale). All rolling windows end at t-1. Full per-feature table with first valid date and counts: `results/hl2_feature_timestamps.csv` (written by the run); the panel itself: `results/hl2_features_panel.csv.gz`.

| block | features (scale model) | timestamp rule |
|---|---|---|
| **a** implied / VIX | ln India VIX, ln change of VIX, VIX-minus-realised-vol spread (ln(VIX/100/sqrt 252) - ln Nifty 10-session daily vol) | India VIX close of t-1 (value fixed at 15:30 IST t-1) |
| **b** US overnight | abs S&P 500 return, ln US VIX, ln change US VIX, abs change USD/INR, abs Brent, abs dollar index, abs US 10y change | last observation dated STRICTLY BEFORE the IST date of t. S&P 500 (closes 01:30 IST) and US VIX (01:45 IST): the closing fact is public before the IST open, lag zero. USD/INR: ECB reference rate (fixed 14:15 CET, posted 16:00 CET), lag zero; **the repo's `usdinr_ecb_2017_2026.json` is an HTML error page, so the series is rebuilt from Frankfurter/ECB (`results/hl2_data_usdinr_ecb.csv`)**. Brent (EIA), broad dollar index (weekly Fed release), US 10y (H.15, next day): FRED publication lag is NOT provably zero, so the value is shifted ONE MORE observation back; an observation older than 9 days (6 days for the zero-lag series) is treated as missing. |
| **c** Indian market / peers | Nifty 50 ln range and abs return, Bank Nifty ln range, share of names with abs return >= 5%, abs(advance share - 0.5), median of peers' ln range relative to each peer's own 60-session mean (CDSL MCX ANGELONE CAMS IEX KFINTECH NUVAMA MOTILALOFS ANANDRATHI, >= 3 listed), z-score of ln total turnover | index file / bhavcopy of t-1 (index file posted ~23:20 IST t-1, bhavcopy ~16:34 IST t-1) |
| **d** BSE own / microstructure | ln ln(H/L) of t-1, abs gap of t-1, z-score (60 sessions) of ln turnover and of delivery %, ln Parkinson vol (10 and 20 sessions) minus ln sigma_S6,t, distance of the adjusted close from the 250-session high and low | BSE official bars of t-1 (bhavcopy ~16:34 IST; delivery file ~18:00 IST). Prices are bonus-adjusted through the log-return chain (only `prev` in the processed file is adjusted; OHLC levels are raw traded prices) |
| **e** calendar | Tue/Wed/Thu/Fri dummies (Monday is the reference), one of the last two weekdays of the month, previous session >= 4 calendar days earlier | exchange calendar, known in advance |
| **s** SHORT samples | ln ATM implied vol of BSE options, put-minus-call IV skew, IV-minus-realised-vol (BSE 20 sessions), F&O expiry-day flag, results-next-session flag, ln range of the Nifty Capital Markets index | IV: NSE F&O settlement prices of t-1 (bhavcopy ~17:00 IST), **data only from 2024-11-29 (462 sessions)**; expiry dates read from the contract rows in `data/raw/fo_bse` (from 2024-11-18); results flag from `data/results_dates.csv` (7 events, from 2024-11-13); Capital Markets index high/low exist from 2024-11-11. **Tested only on its own window and labelled so.** |
| **o** post-open (09:08 IST) | abs gap in sigma units |G_t|/sigma_S6,t (capped 4), open beyond yesterday's high or low, abs distance of the open from the middle of yesterday's range | official open O_t (NSE pre-open auction, final 09:08 IST), sigma_S6,t and yesterday's bar |

Signed features for the **location** model (shift of the median of H and L): b: signed S&P 500 return, USD/INR change, US VIX change, Brent / dollar / US10y changes (same lag rules); c: Nifty and Bank Nifty returns of t-1, advance share - 0.5, median peer return (each clipped +-15%), ln change of VIX; d: BSE returns of t-1 / 5 / 20 sessions, close location in the range, distance from the 250-session high / low, up-down streak (capped +-5), BSE minus Nifty; e: the calendar dummies; o: signed gap in sigma units, position of the open in yesterday's range, +1/-1/0 for open beyond yesterday's high/low.

**Count of features searched: 58 distinct a-priori features (40 in the scale models, 28 in the location models, 10 in both), in 7 blocks, entering 23 candidate variants.** Menu items NOT entered, and why: GIFT Nifty, NSE pre-open order book (2 snapshots only), FII/DII flows (no dated series in `data/`): untested. Volume z-score (collinear with the turnover z-score, so not entered separately), 5-day Parkinson/Garman-Klass and 1-5-22 day realised variance (already inside the baseline's HAR term: only the 10/20-day Parkinson vol RELATIVE to the baseline sigma enters), Capital Markets index return (only its range, from 2024-11), individual peers (only the median). The 13-15 Oct 2026 rows missing from the repo's processed index, breadth, peers, IV, delivery and US files were filled from NSE archives, local UDiFF files, Yahoo (S&P 500, US VIX) and Frankfurter/ECB (`results/hl2_fill_*.csv`, rebuilt by `--refresh-fill`). **Live 16 Oct caveat:** the FRED files end 6 Oct (Brent), 2 Oct (dollar index), 8 Oct (US 10y), so those three features are missing (= zero effect) in the 16 Oct forecast; they exist for all backtest sessions.

### 0.4 Model (identical machinery for every variant; "no features" reproduces the baseline exactly)
* **Scale.** sigma'_t = sigma_S6,t x exp(clip(z_t' gamma, -1, 1)), z = standardised features (winsorised at the 1st / 99th percentile of the training rows, 0/1 columns not winsorised, missing = 0 = training mean; a column needs >= 120 non-missing training rows). gamma from a log-link (Poisson pseudo-ML) ridge regression of the ratio r_s = y_s / sigma_S6,s on z_s, intercept unpenalised: min mean[exp(a + z'g) - r (a + z'g)] + (lambda/2)|g|^2. The baseline's own GARCH and HAR terms are in the offset sigma_S6, so the regression measures the INCREMENTAL effect of the features. y = max(Hp,0) + max(-Lp,0) (pre-open, range of the path P0 -> day) or HO - LO = ln(H/L) (post-open) for the symmetric variants; the tail-specific variants (`TS`) regress the high side (max(Hp,0) or HO) and the low side (max(-Lp,0) or -LO) separately (each with its own ridge strength). (The log-link mean regression is used instead of OLS on ln y because the one-sided excursions can be exactly zero.)
* **Ridge strength.** lambda in {0.01, 0.03, 0.1, 0.3, 1, 3, 10, infinity}; infinity = no features = baseline. Chosen by forward-chaining CV inside the training rows (train on the first 50%, 62.5%, 75%, 87.5% of the rows, validate on the next 12.5%; features standardised inside each fold; pooled Poisson loss; ties go to stronger shrinkage), re-selected every 5th refit (every 100 sessions), coefficients refitted every 20 sessions on sessions strictly before the block (first refit at session 640; the baseline's sigma exists from session 500).
* **Location.** The same walk-forward ridge, but ordinary least squares on the winsorised standardised residual u_s = V_s / sigma'_s of H and of L (separately), ridge strength by the same forward-chaining CV on squared error (infinity = no shift). The quantiles are those of sigma'_t x (e_s + shift_t) where e_s = u_s - shift_s are the shift-corrected residuals of the trailing 500 sessions; post-open draws are clipped at HO >= 0 and LO <= 0 before the quantiles are taken.
* **Quantiles.** The baseline's filtered historical simulation: trailing 500 sessions of V_s / sigma'_s (the current block's multiplier applied to all pool rows), times sigma'_t. Baseline sigma_S6 is the project's own (src/models.py) for the close-to-close return R (pre-open) and for the open-to-close return I with Garman-Klass (post-open).
* **Live forecast.** `hl2_forecast(date, open_price)` refits the regressions at the forecast session (one step fresher than the evaluated blocks, as `hl_model.hl_forecast` does) and, for any target where no variant was adopted, returns the baseline numbers.

### 0.5 Variants (23 candidates = 46 variant-target pairs = the Holm family; all tried, all reported)
| pre-open (baseline `P_S6`; targets H, L) | features |
|---|---|
| `P_SC_a`, `P_SC_b`, `P_SC_c`, `P_SC_d`, `P_SC_e` | symmetric scale from block a / b / c / d / e alone |
| `P_SC_f` | symmetric scale, all of a + b + c + d + e (ridge) |
| `P_SC_s` | block s alone, own window (from the first refit with >= 120 rows of the IV features, about May 2025) |
| `P_SC_fs` | all of a + b + c + d + e + s, own window |
| `P_TS_f` | tail-specific scale (separate high-side and low-side regressions), all of a to e |
| `P_LO_f` | location only, all signed features (b, c, d, e) |
| `P_SL_f` | scale (a to e) + location (b, c, d, e) |

| post-open (baseline `W_I6`; targets HO, LO) | features |
|---|---|
| `W_SC_a` ... `W_SC_e` | symmetric scale from block a / b / c / d / e alone (5 variants) |
| `W_SC_o` | post-open block alone |
| `W_SC_fo` | all of a to e + o |
| `W_SC_s`, `W_SC_fso` | block s alone / a to e + s + o, own window |
| `W_TS_fo` | tail-specific scale, a to e + o |
| `W_LO_fo` | location only, b to e + o |
| `W_SL_fo` | scale (a to e + o) + location (b to e + o) |

Diagnostics, NOT candidates, not in the family, cannot be adopted: `P_PLACEBO`, `W_PLACEBO` = ten N(0,1) columns (fixed seed 20261016) through the identical symmetric-scale machinery (what the ridge + CV pipeline does on pure noise).

### 0.6 Rules for the report
Every variant x target x window is reported (n beside it). Tested results (DM, Holm, adoption) are labelled tested; coefficient tables, correlations, by-year tables and anything else are labelled descriptive and cannot lead to adoption. If a variant is added after the first results it is labelled post hoc and the family size reported with it is increased. A result that contradicts a project claim is flagged explicitly. Feature selection happens only inside the walk-forward (the CV picks the ridge strength; the blocks and features were fixed here, a priori, not chosen on the Final window).

### 0.7 What counts as a null
A variant is a **tie** if its pinball gain is positive but the rule is not met, **worse** if the baseline is better, and a **null** for a block if all its variants are ties or worse. A block that helps in the own-window comparison but cannot meet (ii) is reported as "own-window result, not adoptable".

### 0.8 Reproduction commands
See the last section of this file.

### 0.9 Baseline reproduction (run before any variant; `results/hl2_baseline_repro.csv`)
The engine with no features reproduces `hl_model.build()` quantiles to 0.0 (max absolute difference, 1,640 sessions, pre- and post-open) and the stored Final-window numbers exactly: pre-open P_S6 pinball x1e4 31.15 (high) / 36.58 (low), typical miss Rs 42.7 / 47.7 (Rs 42.69 / 47.67), 90% coverage 90.3% / 88.8%; post-open W_I6 pinball 23.85 / 28.03, typical miss Rs 34.8 / 37.4. (n = 320.)

## 1. Status, chronology and what was changed after Section 0 (read this first)

* **Who wrote what, and when.** Section 0 above (14,864 characters, from the heading `## 0. Pre-fixed section` to the end of 0.9) was written by the first working session of this study on Fri 16 Oct 2026 at 08:19 UTC (13:49 IST), before any variant had been evaluated on the real data; its SHA-256 `1274b181b0e084066db1f05698009441570cf5d84dfcc186ae7ba3ce84c83239` is in `results/hl2_prefixed_sha256.txt` (that session's own record, not an independent timestamp). That session ran the evaluation (result files stamped 08:24 UTC) and then stopped: the code file is stamped 08:26 UTC, two minutes later, and contains fixed-ridge sensitivity variants and an 'all sessions' window that the stored 08:24 results do not, so those were added after the first results existed (they are labelled post hoc below). It never wrote the leakage test, the forecast function, the command line or the results part of this report. **A second session (this one, from about 13:30 UTC) completed those parts.** Before doing so it recomputed the SHA-256 of the Section 0 text in this file: it still equals the stored value, i.e. Section 0 is unchanged. Nothing below changes the adoption rule, the windows, the family size (46 pairs) or the 58 features.
* **The 16 Oct bar is in the repo now, and was kept out.** `data/processed/bse_daily_extra.csv` now also holds the official bar of the session of 16 Oct 2026 (it arrived with the lead's commit `e9027cc` 'After-close 16 Oct: official bar ...', 11:19 UTC; it was not there when the first session ran, whose evaluation ended at 15 Oct, n = 2,390 sessions). The brief says that session's data must not be used by any study, so `load_tables()` cuts every input table at the 15 Oct 2026 session (`LAST_OFFICIAL`), and the forecast function only ever reads rows dated before the forecast date. Proof in Section 9: a test in which the real 16 Oct bar and everything after it is replaced by junk, and one in which it is simply left in, both leave the 16 Oct forecast unchanged (largest difference 0.0 log points). I saw that row once, when printing the tail of that file at the start of this session; nothing in this study uses it and no choice below was made with it. **Heads-up for the lead:** because `hl_model.load_ohlc()` concatenates that file, re-running `python3 src/hl_model.py --eval` now would silently add the 16 Oct session (n = 2,391 sessions, Final n = 321) to the stored baseline tables.
* **Everything was re-run** with the final code (`--baseline-check`, `--eval`, `--leakage`, `--spotcheck`, `--sp-buckets`, the live forecast). The 23 pre-fixed variants and the two placebos give exactly the same numbers as the first session's run (largest relative difference 0, every row of `hl2_eval_summary.csv` and `hl2_eval_dm_holm.csv` that existed before; the five verdict columns of `hl2_adoption.csv` are identical for all 50 rows).
* **Post hoc additions (all outside the Holm family, none can be adopted):** (a) fixed-ridge sensitivity versions (`*_fix0.3`, `*_fix3`) of five pre-fixed variants (10), of the two short-sample variants (4) and of the random-column placebos (4); (b) three location variants narrowed after the coefficient table of `P_LO_f` was seen: `P_LO_b` (signed US block), `P_LO_sp` (S&P 500 return only) and its after-open twin `W_LO_sp`; (c) supplementary tables: the 'all 1,640 sessions' and 'since 9 Mar 2026' windows, paired tests on the rupee miss of the median, HAC lags 10 and 20, a univariate screen, a Holm count that includes the post hoc variants, and a descriptive S&P table. In total 21 post hoc variants (42 pairs); counting them with the 46 pre-fixed pairs and the 4 placebo pairs gives 92 pairs.
* **One definition tightened** (it cannot change any verdict): in condition (ii) for the short-sample variants, a block counts as 'feature used' only when the ridge strength was finite (the first session's code also counted blocks in which the ridge had shrunk every coefficient to zero). For the two own-window variants (block s alone) the number of Validation sessions on which features were used is 0 of 248 under the stricter definition (it was 30 of 248 under the looser one): 'not testable' either way.


## 2. The answer in plain words (Fri 16 Oct 2026; n beside every number; 'tested' = the pre-fixed rule of Section 0)

**Question.** Do extra inputs (India VIX and BSE option-implied volatility; the US overnight move, US VIX, USD/INR, oil, dollar index, US 10-year; Nifty, Bank Nifty, market breadth and the peer stocks; BSE's own yesterday range, volume, delivery and position in its yearly range; calendar items; and, from 09:08, the opening gap) make the forecast of the day's HIGH and LOW more precise than the project's baseline (volatility model S6 times the shapes of the last 500 days' highs and lows)?

**Answer: no, not in any way that passes the rule I fixed before looking.** I tried 23 variants (46 variant-target pairs; 58 a-priori features in 7 blocks; every fit inside an expanding walk-forward, refitted every 20 sessions) on 320 out-of-sample sessions (1 Jul 2025 to 15 Oct 2026). **No variant met the adoption rule for any of the four targets, so the baseline stays for the pre-open high and low and for the after-open high and low.** In detail (all tested; Final window, n = 320):

* **The best-looking pair is only 2.36% better** (pre-open high, every block as scale and location, `P_SL_f`): raw p 0.072, Holm-adjusted 1.00; the typical miss of the median is Rs 41.8 instead of Rs 42.7, i.e. Rs 0.9 better. It fails condition (i) (not significant after correction) and (iii) (its 90% band is 0.9 points off nominal coverage against the baseline's 0.3).
* **Of the 46 pairs, 22 have a positive Final gain** (4 are identical to the baseline in that window because the ridge switched the features off), **1 reaches 2%, 1 has a raw p below 0.05 in the right direction** (chance alone gives about 1.1 of 42) **and 0 survives the correction for 46 comparisons.** On the other side **8 pairs are worse at raw p < 0.05** (7 on the after-open low, 1 on the after-open high) and **1 stays worse after Holm**: after-open low, every block as scale and location, 3.86% worse (Holm 0.004), typical miss Rs 38.6 instead of Rs 37.4.
* **Volatility-type inputs add nothing to the scale the baseline already has.** Pre-open Final gains (high / low): India VIX +0.00% / +0.00% (the ridge switched the VIX features on in only 12% of its refits); US block -0.17% / +0.07%; Indian market and peers +0.66% / -0.40%; BSE's own volume and range history +0.11% / -0.15%; calendar -0.05% / -0.14%; all five together +0.60% / -0.09%; BSE option-implied volatility (about 460 sessions only) +0.01% / +0.00% (Section 6). None is distinguishable from zero.
* **After the 09:08 open the extras hurt the low.** All blocks plus the opening-gap block as scale: high +1.20% (p 0.058), low -1.93% (p 0.002, Holm 0.091). The open already carries the overnight and market news; feeding it in again adds estimation noise.
* **The one input that does move the pre-open numbers consistently is not a volatility input: it is the sign and size of the S&P 500's last session, used as a SHIFT of the whole high-low band (Section 5).** It was picked after the coefficients were seen, so it is post hoc and cannot be adopted by the rule; it is worth about Rs 1.1 (high) and Rs 1.3 (low) off the typical pre-open miss and nothing after the open.

**What the typical miss looks like with everything I tried** (Final window, n = 320; mean absolute error of the median, rupees at Rs 3,428; in brackets the variant and its pinball gain; the 'best on Final' column is picked with hindsight and is therefore optimistic):

| target | baseline | all blocks, scale only | all blocks, scale + location | best of the 23 on Validation | best of the 23 on Final (hindsight) | S&P shift only (post hoc, Section 5) |
|---|---|---|---|---|---|---|
| pre-open HIGH | **42.7** | 42.6 (`P_SC_f`, +0.60%) | 41.8 (`P_SL_f`, +2.36%) | 41.8 (`P_SL_f`, +2.36%) | 41.8 (`P_SL_f`, +2.36%) | 41.6 (`P_LO_sp`, +2.14%) |
| pre-open LOW | **47.7** | 47.7 (`P_SC_f`, -0.09%) | 47.3 (`P_SL_f`, +1.32%) | 47.3 (`P_SL_f`, +1.32%) | 47.1 (`P_LO_f`, +1.55%) | 46.3 (`P_LO_sp`, +2.94%) |
| after-open HIGH | **34.8** | 34.3 (`W_SC_fo`, +1.20%) | 34.5 (`W_SL_fo`, +0.69%) | 34.5 (`W_SC_o`, +0.39%) | 34.3 (`W_SC_fo`, +1.20%) | 34.8 (`W_LO_sp`, -0.05%) |
| after-open LOW | **37.4** | 37.9 (`W_SC_fo`, -1.93%) | 38.6 (`W_SL_fo`, -3.86%) | none beat the baseline on Validation | 37.4 (`W_SC_s`, +0.22%) | 37.4 (`W_LO_sp`, +0.05%) |

**Plain reading.** No pre-fixed variant improves the typical miss by more than Rs 0.9 before the open or Rs 0.5 after it (and the worst makes it Rs 1.2 worse). The numbers you already have are the honest ones: before the open the day's high is good to about Rs 43 and the low to about Rs 48 (on average, at today's price), after the 09:08 open to about Rs 35 and Rs 37; 'price stays' would miss by Rs 62.9 / Rs 61.3 and 'open stays' by Rs 51.3 / Rs 59.0. More parameters do not sharpen that, because most of what is left is the genuine day-to-day randomness of where the extremes land, not information I failed to feed in.

**Not tested** (no usable history, so I cannot say anything): GIFT Nifty, the NSE pre-open order book (2 snapshots only), FII/DII flows (no dated series in `data/`). Everything else on the menu was tested, except the few items Section 0.3 lists as not entered separately (volume z-score, 5-day realised range, the Capital Markets index return, individual peers).

**Recommendation to the lead.** Keep `hl_model.py` as it is. `hl2_forecast()` returns exactly the baseline numbers (checked to the paisa for 16 Oct, Section 10) because nothing was adopted. If the S&P shift is of interest, treat it as ONE pre-registered candidate to be scored forward (Section 5), not as an adopted improvement.


## 3. What was run (method recap; the definitions are Section 0)

* **Engine** (`src/hl_model2.py`): the baseline's own S6 scale paths (re-used from `hl_model.py`; walk-forward, refit every 20 sessions) and its filtered historical simulation (trailing 500 standardised residuals). A variant changes only (a) a multiplier on the scale, exp(clip(z'gamma, -1, 1)), from a log-link ridge regression of the realised high-plus-low excursion (pre-open) or of ln(H/L) (after the open) divided by the baseline scale, and/or (b) a shift of the median of the high and of the low from a ridge OLS on the standardised residual. Ridge strength: forward-chaining cross-validation inside the training rows, with 'no features' in the grid. Refit every 20 sessions on sessions strictly before the block; first refit at session 640; evaluated sessions 750 on (25 Feb 2020 to 15 Oct 2026, n = 1,640).
* **Baseline reproduced first** (`--baseline-check`, `results/hl2_baseline_repro.csv`): with no features the engine equals `hl_model.build()` to 0.0 (largest absolute difference of any quantile, 1,640 sessions, pre- and post-open), and the Final window gives pre-open pinball x1e4 31.15 (high) / 36.58 (low), typical miss Rs 42.7 / 47.7, post-open 23.85 / 28.03, Rs 34.8 / 37.4 (n = 320): identical to the stored `hl_eval_preopen.csv` / `hl_eval_postopen.csv` (largest difference over every compared pinball, miss and coverage cell, Final and auction slice: 0.0).
* **Windows (n):** Development 1,072, Validation 248, Final 320, post-auction slice 52.
* **Features and timestamp rules:** Section 0.3 and `results/hl2_feature_timestamps.csv` (58 features; first valid date and counts); checked in Section 9. US series: the last observation dated strictly before the IST session date. S&P 500, US VIX and USD/INR (ECB) are closing facts that exist before 09:00 IST (lag zero: the later FRED posting date does not change what was knowable); Brent, the dollar index and the US 10-year are shifted one more observation back. Assuming a delay for the S&P as well would make that feature staler, which can only weaken the already null scale results (it would weaken the S&P shift of Section 5 as well).
* **Input fix-ups** (`results/hl2_fill_*.csv`): the repo's processed index, breadth, peers, implied-vol, delivery and US files stop between 12 and 13 Oct 2026; the missing rows to 15 Oct come from NSE archives, the local UDiFF zips, Yahoo (S&P 500, US VIX) and Frankfurter/ECB (USD/INR). The repo's `usdinr_ecb_2017_2026.json` is an HTML error page and was not used.


## 4. Results of the pre-fixed variants (tested)

### 4.1 Final window, every variant (n = 320)
**Pre-open (baseline P_S6): Final window (n = 320), every pre-fixed variant.** pinball x1e4 (lower is better); gain = % lower than baseline; DM p raw and Holm over the 46 pairs; miss = mean absolute error of the median in Rs at 3,428 (baseline in brackets); Val = Validation gain %; CAS = pinball ratio to baseline in the 52 auction sessions; cov dev = coverage minus nominal in percentage points (50% / 90%).

| variant | target | pinball | base | gain % | p raw | Holm | miss Rs (base) | Val gain % | CAS ratio | cov dev 50 / 90 | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `P_SC_a` | H | 31.15 | 31.15 | 0.00 | - | 1.000 | 42.7 (42.7) | -0.00 | 1.000 | -3.1 / 0.3 | worse or equal |
| `P_SC_a` | L | 36.58 | 36.58 | 0.00 | - | 1.000 | 47.7 (47.7) | -0.01 | 1.000 | 0.3 / -1.2 | worse or equal |
| `P_SC_b` | H | 31.20 | 31.15 | -0.17 | 0.222 | 1.000 | 42.8 (42.7) | -0.34 | 0.997 | -2.2 / 0.0 | worse or equal |
| `P_SC_b` | L | 36.55 | 36.58 | 0.07 | 0.605 | 1.000 | 47.6 (47.7) | 0.23 | 1.002 | 0.3 / -1.6 | tie: fails (i) gain/DM/Holm, (iii) coverage |
| `P_SC_c` | H | 30.95 | 31.15 | 0.66 | 0.111 | 1.000 | 42.5 (42.7) | 0.23 | 1.002 | -2.8 / -0.3 | tie: fails (i) gain/DM/Holm |
| `P_SC_c` | L | 36.72 | 36.58 | -0.40 | 0.233 | 1.000 | 47.8 (47.7) | 0.41 | 1.005 | 0.6 / -2.2 | worse or equal |
| `P_SC_d` | H | 31.12 | 31.15 | 0.11 | 0.699 | 1.000 | 42.7 (42.7) | -0.03 | 1.002 | -4.1 / 0.9 | tie: fails (i) gain/DM/Holm, (ii) Validation sign, (iii) coverage |
| `P_SC_d` | L | 36.63 | 36.58 | -0.15 | 0.577 | 1.000 | 47.7 (47.7) | 0.06 | 0.987 | 0.9 / -0.9 | worse or equal |
| `P_SC_e` | H | 31.17 | 31.15 | -0.05 | 0.622 | 1.000 | 42.7 (42.7) | -0.21 | 1.001 | -3.4 / 0.3 | worse or equal |
| `P_SC_e` | L | 36.63 | 36.58 | -0.14 | 0.099 | 1.000 | 47.7 (47.7) | 0.04 | 0.999 | 0.6 / -1.2 | worse or equal |
| `P_SC_f` | H | 30.96 | 31.15 | 0.60 | 0.122 | 1.000 | 42.6 (42.7) | -0.38 | 0.997 | -3.4 / 0.6 | tie: fails (i) gain/DM/Holm, (ii) Validation sign, (iii) coverage |
| `P_SC_f` | L | 36.61 | 36.58 | -0.09 | 0.814 | 1.000 | 47.7 (47.7) | 0.82 | 0.990 | 0.0 / -1.9 | worse or equal |
| `P_SC_s` | H | 31.15 | 31.15 | 0.01 | 0.927 | 1.000 | 42.8 (42.7) | 0.00 | 1.002 | -3.1 / -0.3 | tie: fails (i) gain/DM/Holm, (ii) Validation sign |
| `P_SC_s` | L | 36.58 | 36.58 | 0.00 | 0.980 | 1.000 | 47.6 (47.7) | 0.00 | 0.999 | 0.6 / -0.9 | tie: fails (i) gain/DM/Holm, (ii) Validation sign, (iii) coverage |
| `P_SC_fs` | H | 30.82 | 31.15 | 1.06 | 0.041 | 1.000 | 42.5 (42.7) | -0.40 | 0.999 | -3.1 / 0.6 | tie: fails (i) gain/DM/Holm, (ii) Validation sign, (iii) coverage |
| `P_SC_fs` | L | 36.57 | 36.58 | 0.04 | 0.921 | 1.000 | 47.7 (47.7) | 0.83 | 0.988 | 0.6 / -1.2 | tie: fails (i) gain/DM/Holm, (iii) coverage |
| `P_TS_f` | H | 31.02 | 31.15 | 0.43 | 0.584 | 1.000 | 42.2 (42.7) | -0.06 | 0.996 | -2.8 / 0.0 | tie: fails (i) gain/DM/Holm, (ii) Validation sign |
| `P_TS_f` | L | 36.62 | 36.58 | -0.10 | 0.923 | 1.000 | 47.0 (47.7) | 2.64 | 1.002 | 0.6 / -1.6 | worse or equal |
| `P_LO_f` | H | 30.59 | 31.15 | 1.79 | 0.241 | 1.000 | 41.9 (42.7) | 0.58 | 0.987 | -1.9 / 1.9 | tie: fails (i) gain/DM/Holm, (iii) coverage |
| `P_LO_f` | L | 36.01 | 36.58 | 1.55 | 0.312 | 1.000 | 47.1 (47.7) | 2.59 | 0.985 | -3.1 / 0.3 | tie: fails (i) gain/DM/Holm, (iii) coverage |
| `P_SL_f` | H | 30.42 | 31.15 | 2.36 | 0.072 | 1.000 | 41.8 (42.7) | 1.06 | 0.983 | -0.9 / 0.9 | tie: fails (i) gain/DM/Holm, (iii) coverage |
| `P_SL_f` | L | 36.10 | 36.58 | 1.32 | 0.403 | 1.000 | 47.3 (47.7) | 3.11 | 0.979 | -1.9 / -0.9 | tie: fails (i) gain/DM/Holm, (iii) coverage |
| `P_PLACEBO` | H | 31.15 | 31.15 | 0.00 | - | - | 42.7 (42.7) | 0.00 | 1.000 | -3.1 / 0.3 | diagnostic |
| `P_PLACEBO` | L | 36.58 | 36.58 | 0.00 | - | - | 47.7 (47.7) | 0.00 | 1.000 | 0.3 / -1.2 | diagnostic |

**Post-open (baseline W_I6): Final window (n = 320), every pre-fixed variant.** pinball x1e4 (lower is better); gain = % lower than baseline; DM p raw and Holm over the 46 pairs; miss = mean absolute error of the median in Rs at 3,428 (baseline in brackets); Val = Validation gain %; CAS = pinball ratio to baseline in the 52 auction sessions; cov dev = coverage minus nominal in percentage points (50% / 90%).

| variant | target | pinball | base | gain % | p raw | Holm | miss Rs (base) | Val gain % | CAS ratio | cov dev 50 / 90 | verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `W_SC_a` | HO | 23.83 | 23.85 | 0.09 | 0.324 | 1.000 | 34.8 (34.8) | -0.12 | 0.999 | -0.6 / 2.0 | tie: fails (i) gain/DM/Holm, (ii) Validation sign |
| `W_SC_a` | LO | 28.05 | 28.03 | -0.09 | 0.399 | 1.000 | 37.4 (37.4) | -0.07 | 1.003 | 0.0 / -0.3 | worse or equal |
| `W_SC_b` | HO | 23.79 | 23.85 | 0.28 | 0.175 | 1.000 | 34.7 (34.8) | -0.14 | 0.995 | -1.6 / 1.7 | tie: fails (i) gain/DM/Holm, (ii) Validation sign, (iii) coverage |
| `W_SC_b` | LO | 28.09 | 28.03 | -0.22 | 0.256 | 1.000 | 37.5 (37.4) | -0.44 | 1.001 | 0.0 / -0.3 | worse or equal |
| `W_SC_c` | HO | 23.75 | 23.85 | 0.45 | 0.205 | 1.000 | 34.6 (34.8) | 0.22 | 1.007 | -1.2 / 2.0 | tie: fails (i) gain/DM/Holm, (iii) coverage |
| `W_SC_c` | LO | 28.33 | 28.03 | -1.06 | 0.041 | 1.000 | 37.4 (37.4) | -0.29 | 1.002 | 0.3 / -0.6 | worse or equal |
| `W_SC_d` | HO | 23.86 | 23.85 | -0.03 | 0.804 | 1.000 | 34.8 (34.8) | -0.29 | 1.000 | -0.6 / 2.3 | worse or equal |
| `W_SC_d` | LO | 28.08 | 28.03 | -0.19 | 0.115 | 1.000 | 37.5 (37.4) | -0.37 | 1.000 | 0.3 / -0.9 | worse or equal |
| `W_SC_e` | HO | 23.85 | 23.85 | 0.00 | - | 1.000 | 34.8 (34.8) | 0.00 | 1.000 | -0.6 / 2.3 | worse or equal |
| `W_SC_e` | LO | 28.03 | 28.03 | 0.00 | - | 1.000 | 37.4 (37.4) | 0.00 | 1.000 | 0.3 / -0.6 | worse or equal |
| `W_SC_o` | HO | 23.76 | 23.85 | 0.39 | 0.548 | 1.000 | 34.5 (34.8) | 1.63 | 1.027 | -1.2 / 1.1 | tie: fails (i) gain/DM/Holm, (iii) coverage |
| `W_SC_o` | LO | 28.40 | 28.03 | -1.31 | 0.019 | 0.788 | 37.9 (37.4) | -1.61 | 0.996 | 1.2 / -0.9 | worse or equal |
| `W_SC_fo` | HO | 23.57 | 23.85 | 1.20 | 0.058 | 1.000 | 34.3 (34.8) | 1.53 | 1.014 | 0.0 / 1.4 | tie: fails (i) gain/DM/Holm |
| `W_SC_fo` | LO | 28.57 | 28.03 | -1.93 | 0.002 | 0.091 | 37.9 (37.4) | -1.95 | 0.995 | 1.9 / -0.6 | worse or equal |
| `W_SC_s` | HO | 23.86 | 23.85 | -0.01 | 0.874 | 1.000 | 34.8 (34.8) | 0.00 | 1.003 | -0.6 / 2.0 | worse or equal |
| `W_SC_s` | LO | 27.97 | 28.03 | 0.22 | 0.197 | 1.000 | 37.4 (37.4) | 0.00 | 0.989 | 0.6 / -0.6 | tie: fails (i) gain/DM/Holm, (ii) Validation sign, (iii) coverage |
| `W_SC_fso` | HO | 23.60 | 23.85 | 1.07 | 0.103 | 1.000 | 34.3 (34.8) | 1.52 | 1.015 | -0.6 / 1.7 | tie: fails (i) gain/DM/Holm |
| `W_SC_fso` | LO | 28.51 | 28.03 | -1.70 | 0.006 | 0.270 | 37.9 (37.4) | -1.97 | 0.992 | 1.2 / -0.6 | worse or equal |
| `W_TS_fo` | HO | 23.84 | 23.85 | 0.04 | 0.960 | 1.000 | 34.5 (34.8) | 1.51 | 1.034 | -2.2 / 1.4 | tie: fails (i) gain/DM/Holm, (iii) coverage |
| `W_TS_fo` | LO | 28.12 | 28.03 | -0.34 | 0.029 | 1.000 | 37.5 (37.4) | -0.64 | 1.001 | 0.0 / -0.3 | worse or equal |
| `W_LO_fo` | HO | 24.13 | 23.85 | -1.15 | 0.043 | 1.000 | 34.9 (34.8) | -2.11 | 1.006 | -1.6 / -0.9 | worse or equal |
| `W_LO_fo` | LO | 28.63 | 28.03 | -2.14 | 0.003 | 0.113 | 38.1 (37.4) | -1.26 | 1.012 | -1.9 / -3.6 | worse or equal |
| `W_SL_fo` | HO | 23.69 | 23.85 | 0.69 | 0.319 | 1.000 | 34.5 (34.8) | -0.33 | 1.015 | -1.6 / -0.5 | tie: fails (i) gain/DM/Holm, (ii) Validation sign, (iii) coverage |
| `W_SL_fo` | LO | 29.11 | 28.03 | -3.86 | <0.001 | 0.004 | 38.6 (37.4) | -4.84 | 1.008 | -1.6 / -2.7 | worse or equal |
| `W_PLACEBO` | HO | 23.85 | 23.85 | 0.00 | - | - | 34.8 (34.8) | 0.00 | 1.000 | -0.6 / 2.3 | diagnostic |
| `W_PLACEBO` | LO | 28.03 | 28.03 | 0.00 | - | - | 37.4 (37.4) | 0.00 | 1.000 | 0.3 / -0.6 | diagnostic |

*Reading the verdict column:* 'tie' = gain positive but a condition fails (the failed conditions are listed); 'worse or equal' = not better than the baseline; 'diagnostic' = the random-column placebo, not a candidate. No row says ADOPT. Condition (ii) fails for 29 of the 46 pairs, condition (iii) for 29 (mostly because a variant moves the 50% band's deviation from nominal by more than the baseline's very small one: 23 pairs on the 50% band, 13 on the 90% band), condition (iv) for none, condition (i) for all.

### 4.2 Block by block (ablation)
Gain = % lower pinball than the baseline in the window (Final n = 320, Validation n = 248); 'share of refits' = how often the walk-forward ridge chose a finite strength (the features were switched on) rather than 'no features'.

| block (as a scale model) | features | pre-open Final gain % high / low | pre-open Validation gain % | share of refits that used the features | after-open Final gain % high / low | after-open Validation gain % | share of refits that used the features |
|---|---|---|---|---|---|---|---|
| a: India VIX | 3 | +0.00 / +0.00 | -0.00 / -0.01 | 12% | +0.09 / -0.09 | -0.12 / -0.07 | 58% |
| b: US overnight, FX, oil, dollar, 10y | 7 | -0.17 / +0.07 | -0.34 / +0.23 | 88% | +0.28 / -0.22 | -0.14 / -0.44 | 88% |
| c: Indian market, breadth, peers | 7 | +0.66 / -0.40 | +0.23 / +0.41 | 76% | +0.45 / -1.06 | +0.22 / -0.29 | 94% |
| d: BSE own range, volume, delivery, 250-day position | 8 | +0.11 / -0.15 | -0.03 / +0.06 | 46% | -0.03 / -0.19 | -0.29 / -0.37 | 72% |
| e: calendar | 6 | -0.05 / -0.14 | -0.21 / +0.04 | 54% | +0.00 / +0.00 | +0.00 / +0.00 | 36% |
| a to e together (after-open: plus o) | 31 (after-open 34) | +0.60 / -0.09 | -0.38 / +0.82 | 82% | +1.20 / -1.93 | +1.53 / -1.95 | 100% |
| s: option IV, skew, expiry, results (own short window) | 6 | +0.01 / +0.00 | +0.00 / +0.00 | 44% | -0.01 / +0.22 | +0.00 / +0.00 | 44% |
| a to e plus s (after-open: plus o) | 37 (after-open 40) | +1.06 / +0.04 | -0.40 / +0.83 | 82% | +1.07 / -1.70 | +1.52 / -1.97 | 100% |
| o: opening gap block (after-open only) | 3 | - / - | - / - | - | +0.39 / -1.31 | +1.63 / -1.61 | 100% |
| a to e, high and low sides fitted separately (after-open: plus o) | 31 (after-open 34) | +0.43 / -0.10 | -0.06 / +2.64 | 82% | +0.04 / -0.34 | +1.51 / -0.64 | 86% |
| location only: signed b, c, d, e (after-open: plus o) | 25 (after-open 28) | +1.79 / +1.55 | +0.58 / +2.59 | 94% | -1.15 / -2.14 | -2.11 / -1.26 | 88% |
| scale and location together | 56 (after-open 62) | +2.36 / +1.32 | +1.06 / +3.11 | 92% | +0.69 / -3.86 | -0.33 / -4.84 | 92% |

* **VIX / implied volatility (a, s):** nothing. The ridge switched the VIX block on in only 12% of refits pre-open and the Final gain is +0.00% / +0.00%.
* **US overnight (b):** as a SCALE nothing (-0.17% / +0.07% pre-open). As a LOCATION shift it is where the only consistent gain sits (the post hoc `P_LO_b`, Section 5).
* **Indian market, breadth, peers (c):** pre-open +0.66% / -0.40%; after the open the low is -1.06% (raw p 0.041).
* **BSE's own volume, range, delivery, position (d):** +0.11% / -0.15% pre-open, -0.03% / -0.19% after.
* **Calendar (e):** -0.05% / -0.14% pre-open; after the open the Final gain is +0.00% / +0.00% (zero to two decimals). The weekday multiplier of the A study was a null too.
* **Opening-gap block (o):** high +0.39%, low -1.31% (raw p 0.019); its Validation gains are +1.63% / -1.61% and the auction-slice gain for the high is -2.68%: no stable sign.
* **High and low sides fitted separately:** pre-open +0.43% / -0.10%; after the open +0.04% / -0.34%. No better than the symmetric version.

### 4.3 Pinball gain % in every window (descriptive context; the rule uses Final only)
**Pinball gain % by window** (positive = variant better; n: dev 1,072, val 248, val+final 568, final 320, auction 52, all evaluated 1,640; 'all' is supplementary, not part of the rule; the rows below the pre-fixed ones are the POST HOC variants).

| variant | target | dev | val | val+final | final | auction | all | p raw (all) |
|---|---|---|---|---|---|---|---|---|
| `P_SC_a` | H | -0.01 | -0.00 | -0.00 | 0.00 | 0.00 | -0.00 | 0.835 |
| `P_SC_a` | L | -0.08 | -0.01 | -0.01 | 0.00 | 0.00 | -0.05 | 0.211 |
| `P_SC_b` | H | -0.20 | -0.34 | -0.26 | -0.17 | 0.31 | -0.22 | 0.023 |
| `P_SC_b` | L | 0.51 | 0.23 | 0.15 | 0.07 | -0.23 | 0.37 | 0.017 |
| `P_SC_c` | H | -0.21 | 0.23 | 0.42 | 0.66 | -0.21 | -0.01 | 0.960 |
| `P_SC_c` | L | 0.31 | 0.41 | 0.01 | -0.40 | -0.52 | 0.20 | 0.195 |
| `P_SC_d` | H | -0.02 | -0.03 | 0.03 | 0.11 | -0.23 | -0.00 | 0.977 |
| `P_SC_d` | L | 0.23 | 0.06 | -0.04 | -0.15 | 1.26 | 0.13 | 0.151 |
| `P_SC_e` | H | -0.18 | -0.21 | -0.14 | -0.05 | -0.07 | -0.17 | 0.042 |
| `P_SC_e` | L | 0.10 | 0.04 | -0.05 | -0.14 | 0.08 | 0.04 | 0.622 |
| `P_SC_f` | H | -0.20 | -0.38 | 0.05 | 0.60 | 0.25 | -0.12 | 0.474 |
| `P_SC_f` | L | 0.80 | 0.82 | 0.36 | -0.09 | 1.02 | 0.64 | 0.013 |
| `P_SC_s` | H | 0.00 | 0.00 | 0.01 | 0.01 | -0.16 | 0.00 | 0.926 |
| `P_SC_s` | L | 0.00 | 0.00 | 0.00 | 0.00 | 0.07 | 0.00 | 0.980 |
| `P_SC_fs` | H | -0.20 | -0.40 | 0.24 | 1.06 | 0.09 | -0.06 | 0.745 |
| `P_SC_fs` | L | 0.80 | 0.83 | 0.43 | 0.04 | 1.23 | 0.66 | 0.009 |
| `P_TS_f` | H | 0.07 | -0.06 | 0.15 | 0.43 | 0.44 | 0.10 | 0.729 |
| `P_TS_f` | L | 0.49 | 2.64 | 1.27 | -0.10 | -0.22 | 0.78 | 0.136 |
| `P_LO_f` | H | 0.16 | 0.58 | 1.11 | 1.79 | 1.25 | 0.47 | 0.348 |
| `P_LO_f` | L | 2.80 | 2.59 | 2.07 | 1.55 | 1.54 | 2.53 | 0.001 |
| `P_SL_f` | H | 0.16 | 1.06 | 1.62 | 2.36 | 1.75 | 0.65 | 0.225 |
| `P_SL_f` | L | 3.61 | 3.11 | 2.21 | 1.32 | 2.05 | 3.09 | <0.001 |
| `W_SC_a` | HO | -0.04 | -0.12 | -0.03 | 0.09 | 0.06 | -0.04 | 0.305 |
| `W_SC_a` | LO | -0.08 | -0.07 | -0.08 | -0.09 | -0.30 | -0.08 | 0.247 |
| `W_SC_b` | HO | 0.07 | -0.14 | 0.04 | 0.28 | 0.54 | 0.06 | 0.538 |
| `W_SC_b` | LO | 0.07 | -0.44 | -0.33 | -0.22 | -0.13 | -0.07 | 0.621 |
| `W_SC_c` | HO | -0.12 | 0.22 | 0.31 | 0.45 | -0.73 | 0.02 | 0.921 |
| `W_SC_c` | LO | 0.66 | -0.29 | -0.68 | -1.06 | -0.20 | 0.19 | 0.397 |
| `W_SC_d` | HO | -0.02 | -0.29 | -0.18 | -0.03 | 0.00 | -0.07 | 0.383 |
| `W_SC_d` | LO | 0.06 | -0.37 | -0.28 | -0.19 | 0.00 | -0.06 | 0.513 |
| `W_SC_e` | HO | 0.03 | 0.00 | 0.00 | 0.00 | 0.00 | 0.02 | 0.566 |
| `W_SC_e` | LO | -0.06 | 0.00 | 0.00 | 0.00 | 0.00 | -0.04 | 0.243 |
| `W_SC_o` | HO | 0.88 | 1.63 | 1.12 | 0.39 | -2.68 | 0.96 | 0.007 |
| `W_SC_o` | LO | 0.56 | -1.61 | -1.45 | -1.31 | 0.38 | -0.15 | 0.706 |
| `W_SC_fo` | HO | 0.61 | 1.53 | 1.39 | 1.20 | -1.40 | 0.86 | 0.011 |
| `W_SC_fo` | LO | 1.02 | -1.95 | -1.94 | -1.93 | 0.45 | -0.02 | 0.959 |
| `W_SC_s` | HO | 0.00 | 0.00 | -0.01 | -0.01 | -0.31 | -0.00 | 0.874 |
| `W_SC_s` | LO | 0.00 | 0.00 | 0.11 | 0.22 | 1.08 | 0.04 | 0.201 |
| `W_SC_fso` | HO | 0.61 | 1.52 | 1.33 | 1.07 | -1.48 | 0.84 | 0.013 |
| `W_SC_fso` | LO | 1.02 | -1.97 | -1.83 | -1.70 | 0.80 | 0.02 | 0.965 |
| `W_TS_fo` | HO | -0.32 | 1.51 | 0.90 | 0.04 | -3.39 | 0.06 | 0.877 |
| `W_TS_fo` | LO | 0.39 | -0.64 | -0.49 | -0.34 | -0.07 | 0.08 | 0.891 |
| `W_LO_fo` | HO | -0.53 | -2.11 | -1.71 | -1.15 | -0.61 | -0.90 | 0.008 |
| `W_LO_fo` | LO | 0.80 | -1.26 | -1.71 | -2.14 | -1.20 | -0.09 | 0.886 |
| `W_SL_fo` | HO | 0.31 | -0.33 | 0.09 | 0.69 | -1.54 | 0.24 | 0.571 |
| `W_SL_fo` | LO | 1.78 | -4.84 | -4.34 | -3.86 | -0.77 | -0.37 | 0.668 |
| `P_SC_f_fix0.3` | H | -1.49 | -0.77 | -0.18 | 0.58 | 0.10 | -1.06 | 0.011 |
| `P_SC_f_fix0.3` | L | 1.78 | 1.08 | 0.47 | -0.15 | 2.26 | 1.29 | 0.010 |
| `P_SC_f_fix3` | H | -0.36 | -0.09 | 0.16 | 0.49 | 0.17 | -0.19 | 0.249 |
| `P_SC_f_fix3` | L | 1.04 | 0.48 | 0.19 | -0.10 | 0.23 | 0.72 | 0.002 |
| `P_LO_f_fix0.3` | H | -0.81 | 0.58 | 1.10 | 1.79 | 1.23 | -0.18 | 0.799 |
| `P_LO_f_fix0.3` | L | 3.26 | 2.60 | 2.20 | 1.80 | 2.47 | 2.86 | 0.001 |
| `P_LO_f_fix3` | H | 0.39 | 0.66 | 0.96 | 1.34 | 0.87 | 0.58 | 0.076 |
| `P_LO_f_fix3` | L | 2.83 | 2.18 | 1.78 | 1.38 | 0.42 | 2.44 | <0.001 |
| `P_SL_f_fix0.3` | H | -1.25 | 1.13 | 1.86 | 2.80 | 1.75 | -0.23 | 0.792 |
| `P_SL_f_fix0.3` | L | 4.40 | 3.16 | 2.29 | 1.42 | 3.59 | 3.61 | <0.001 |
| `P_SL_f_fix3` | H | 0.25 | 0.70 | 1.28 | 2.03 | 1.34 | 0.59 | 0.110 |
| `P_SL_f_fix3` | L | 3.68 | 2.49 | 1.85 | 1.22 | 0.76 | 2.99 | <0.001 |
| `W_SC_fo_fix0.3` | HO | 0.03 | 1.39 | 1.30 | 1.17 | -2.49 | 0.43 | 0.422 |
| `W_SC_fo_fix0.3` | LO | 0.94 | -2.49 | -2.67 | -2.85 | 1.88 | -0.33 | 0.595 |
| `W_SC_fo_fix3` | HO | 0.71 | 1.41 | 1.29 | 1.12 | -1.40 | 0.90 | 0.005 |
| `W_SC_fo_fix3` | LO | 0.95 | -1.33 | -1.40 | -1.47 | 0.45 | 0.12 | 0.742 |
| `W_LO_fo_fix0.3` | HO | -1.82 | -1.81 | -1.84 | -1.88 | -2.34 | -1.83 | 0.002 |
| `W_LO_fo_fix0.3` | LO | 0.68 | -1.26 | -2.34 | -3.38 | -1.88 | -0.39 | 0.613 |
| `W_LO_fo_fix3` | HO | -0.37 | -0.89 | -0.77 | -0.60 | -0.61 | -0.50 | 0.049 |
| `W_LO_fo_fix3` | LO | 1.13 | 0.08 | -0.59 | -1.23 | -1.20 | 0.53 | 0.178 |
| `P_SC_s_fix0.3` | H | 0.00 | -0.03 | 0.34 | 0.81 | -0.23 | 0.11 | 0.124 |
| `P_SC_s_fix0.3` | L | 0.00 | 0.03 | 0.06 | 0.09 | 0.04 | 0.02 | 0.691 |
| `P_SC_s_fix3` | H | 0.00 | -0.01 | 0.11 | 0.25 | 0.10 | 0.04 | 0.020 |
| `P_SC_s_fix3` | L | 0.00 | 0.01 | 0.01 | 0.01 | 0.01 | 0.00 | 0.739 |
| `W_SC_s_fix0.3` | HO | 0.00 | -0.02 | -0.10 | -0.21 | -0.50 | -0.03 | 0.450 |
| `W_SC_s_fix0.3` | LO | 0.00 | -0.04 | 0.33 | 0.70 | 2.01 | 0.12 | 0.152 |
| `W_SC_s_fix3` | HO | 0.00 | -0.00 | -0.01 | -0.03 | -0.19 | -0.00 | 0.567 |
| `W_SC_s_fix3` | LO | 0.00 | -0.01 | 0.09 | 0.18 | 0.56 | 0.03 | 0.068 |
| `P_LO_b` | H | 1.27 | 1.92 | 2.23 | 2.64 | 3.33 | 1.59 | 0.002 |
| `P_LO_b` | L | 2.09 | 1.40 | 2.34 | 3.29 | 3.99 | 2.19 | <0.001 |
| `P_LO_sp` | H | 1.94 | 0.95 | 1.47 | 2.14 | 3.30 | 1.79 | <0.001 |
| `P_LO_sp` | L | 3.02 | 1.31 | 2.13 | 2.94 | 2.96 | 2.69 | <0.001 |
| `W_LO_sp` | HO | -0.08 | -0.31 | -0.20 | -0.05 | 0.00 | -0.12 | 0.426 |
| `W_LO_sp` | LO | 0.18 | 0.04 | 0.05 | 0.05 | 0.23 | 0.13 | 0.615 |
| `P_PLACEBO_fix0.3` | H | -0.13 | 0.23 | -0.14 | -0.61 | 0.63 | -0.13 | 0.383 |
| `P_PLACEBO_fix0.3` | L | -0.23 | -0.25 | 0.06 | 0.38 | 0.07 | -0.12 | 0.387 |
| `P_PLACEBO_fix3` | H | 0.00 | 0.12 | -0.04 | -0.24 | 0.26 | -0.01 | 0.886 |
| `P_PLACEBO_fix3` | L | -0.06 | -0.11 | 0.01 | 0.13 | 0.03 | -0.03 | 0.566 |
| `W_PLACEBO_fix0.3` | HO | 0.03 | 0.27 | -0.10 | -0.62 | -0.27 | -0.01 | 0.958 |
| `W_PLACEBO_fix0.3` | LO | -0.34 | -0.34 | 0.15 | 0.62 | 0.14 | -0.16 | 0.328 |
| `W_PLACEBO_fix3` | HO | 0.04 | 0.14 | -0.02 | -0.25 | -0.18 | 0.02 | 0.784 |
| `W_PLACEBO_fix3` | LO | -0.06 | -0.13 | 0.08 | 0.29 | 0.08 | -0.01 | 0.886 |

*Reading:* the signs flip between Development, Validation, Final and the auction slice for almost every scale variant, which is what noise looks like. The exceptions are the location variants of the pre-open LOW (positive in all five windows; Section 5) and the after-open location variants (negative in most windows).

### 4.4 Coverage of the 50% and 90% bands (Final, n = 320)
Baseline (pre-open): 50% band 46.9% (high) and 50.3% (low), 90% band 90.3% and 88.8%; after the open: 50% 49.4% / 50.3%, 90% 95.0% / 89.4%. The after-open high's 90% band has an atom at zero (the open is the day's high on a few percent of sessions); the plain Kupiec test rejects 90% (p 0.001) but against the model's own nominal 92.7% the deviation is not significant (p 0.11, the atom-at-zero-aware check of `verify_A`), which is the check used. Every variant's deviation from nominal and its p-value are in `results/hl2_adoption.csv` (`dev50_*`, `dev90_*`, `p50_var`, `p90_var`). Only 1 of the 46 pairs has a 50% or 90% band whose coverage differs significantly from nominal in Final (`W_LO_fo` LO: 90% band -3.6 points, p 0.022).

### 4.5 Post closing-auction slice (since 3 Aug 2026, n = 52)
Baseline pinball x1e4: high 31.22, low 34.02; after the open 22.34 / 25.86. Condition (iv) (variant not more than 5% worse than the baseline) is met by every pre-fixed pair: the worst ratio is 1.034 (`W_TS_fo`, HO), the best 0.979 (`P_SL_f`, L). With 52 sessions this is a weak screen, as the rule intended.

### 4.6 Diagnostics: what pure noise does, and how much power this study has
* **Random placebo through the identical ridge + CV pipeline** (10 N(0,1) columns, fixed seed 20261016): the CV switched them on in 30% of refits, with such strong shrinkage that the Final gain is +0.00% / +0.00% pre-open and +0.00% / +0.00% after the open: the pipeline does not manufacture gains out of noise (this is the check that the cross-validation does its job).
* **The same random columns FORCED in with a fixed ridge** (post hoc, `*_PLACEBO_fix*`): Final gains between -0.62% and +0.62%. That is the size of 'gain' that ten useless columns can show by chance in 320 sessions. The pre-open scale blocks (-0.40% to +1.06%) are close to that range; the after-open low variants (-1.93% to -1.06% for the blocks that include market, gap or all inputs) are worse than noise alone explains, which is the harm noted above.
* **Power, honestly.** The standard error of a Final pinball gain is 0.2 to 1.6 percentage points for the variants that really change the forecast (the all-block variants). To be flagged after correcting for 46 comparisons a gain would have to be roughly 4 to 5 points. So this study cannot exclude true gains of one to three percent. What it shows is that no gain large enough to matter in rupees is visible (1% of pinball is about Rs 0.4 on a Rs 43 miss), and that nothing reached the rule's 2% bar with significance.


## 5. POST HOC finding (not adoptable by the rule): the S&P 500's last session as a shift of the high and low

**Status of this section.** `P_LO_sp` (location shift from the signed S&P 500 return only), `P_LO_b` (the signed US block: S&P, USD/INR, US VIX change, Brent, dollar, 10-year) and the after-open twin `W_LO_sp` were added AFTER I had seen the coefficient table of the pre-fixed `P_LO_f`, in which the S&P return had the largest weight on both sides and the most stable one (positive in every refit) (mean 0.13 on the high side and 0.16 on the low side, in units of the standardised residual per standard deviation of the S&P move; positive in all 83 refits, smallest 0.04 / 0.08; the table covers every walk-forward block including the Final window). They are NOT in the Holm family of 46 pairs and cannot be adopted by the pre-fixed rule; their p-values are optimistic because the variant was chosen after looking. The pre-fixed `P_LO_f` (all 25 signed features) is weaker (Final +1.79% / +1.55%, raw p 0.24 / 0.31), presumably because the other, noisier columns dilute the one that carries the signal.

**What it is in plain words.** Whatever the S&P 500 did in its last session shows up as a shift in the Indian open, and with it in the whole day's band. Without any model, over the 1,640 evaluated sessions (`results/hl2_sp_buckets.csv`; descriptive, no test):

| window | S&P 500 last session | n | median gap | median HIGH vs previous close | median LOW vs previous close | median HIGH vs open | median LOW vs open |
|---|---|---|---|---|---|---|---|
| all evaluated (1,640) | S&P down >= 0.5% | 397 | -0.01% | +1.39% | -1.72% | +1.42% | -1.46% |
| all evaluated (1,640) | S&P within +-0.5% | 729 | +0.32% | +1.69% | -1.22% | +1.35% | -1.39% |
| all evaluated (1,640) | S&P up >= 0.5% | 514 | +0.52% | +2.01% | -0.90% | +1.39% | -1.42% |
| Development+Validation | S&P down >= 0.5% | 336 | +0.00% | +1.42% | -1.75% | +1.40% | -1.47% |
| Development+Validation | S&P within +-0.5% | 559 | +0.36% | +1.82% | -1.18% | +1.46% | -1.39% |
| Development+Validation | S&P up >= 0.5% | 425 | +0.54% | +2.06% | -0.97% | +1.39% | -1.50% |
| Final | S&P down >= 0.5% | 61 | -0.07% | +1.14% | -1.57% | +1.45% | -1.22% |
| Final | S&P within +-0.5% | 170 | +0.21% | +1.27% | -1.32% | +1.00% | -1.38% |
| Final | S&P up >= 0.5% | 89 | +0.41% | +1.87% | -0.75% | +1.41% | -1.09% |
| auction slice | S&P down >= 0.5% | 9 | -0.79% | +1.14% | -2.91% | +2.26% | -0.99% |
| auction slice | S&P within +-0.5% | 29 | +0.00% | +0.89% | -1.64% | +0.73% | -1.64% |
| auction slice | S&P up >= 0.5% | 14 | +0.10% | +2.20% | -0.65% | +1.97% | -0.55% |

After an S&P fall of 0.5% or more (n = 397) the median day's high was +1.39% and the low -1.72% from the previous close; after a rise of 0.5% or more (n = 514) +2.01% and -0.90%: the whole band sits roughly 0.6 to 0.8 percentage points (Rs 21 to 28 at Rs 3,428) higher. Measured from the OPEN the two kinds of day look the same (high +1.42% against +1.39%, low -1.46% against -1.42%): the news is in the open already, which is why the same shift gives nothing after 09:08 (`W_LO_sp`: -0.05% / +0.05%).

**How much it improves the numbers** (tested against the baseline; gains are % lower pinball; Final n = 320 unless stated; the 'all sessions' column is a supplementary window; HAC = the lag of the Diebold-Mariano variance, 5 in the rule):

| variant | target | gain % dev (1,072) | val (248) | final (320) | auction (52) | Final p, HAC lag 5 / 10 / 20 | all 1,640 sessions: p lag 5 / 20 | Final miss Rs (baseline) | miss gain Rs (paired p) |
|---|---|---|---|---|---|---|---|---|---|
| `P_LO_sp` | H | +1.94 | +0.95 | +2.14 | +3.30 | 0.071 / 0.10 / 0.16 | <0.001 / <0.001 | 41.6 (42.7) | +1.1 (0.049) |
| `P_LO_sp` | L | +3.02 | +1.31 | +2.94 | +2.96 | 0.003 / 0.009 / 0.028 | <0.001 / <0.001 | 46.3 (47.7) | +1.3 (0.019) |
| `P_LO_b` | H | +1.27 | +1.92 | +2.64 | +3.33 | 0.050 / 0.077 / 0.12 | 0.002 / 0.003 | 41.7 (42.7) | +1.0 (0.11) |
| `P_LO_b` | L | +2.09 | +1.40 | +3.29 | +3.99 | 0.002 / 0.007 / 0.021 | <0.001 / <0.001 | 46.3 (47.7) | +1.4 (0.018) |
| `P_LO_f` | H | +0.16 | +0.58 | +1.79 | +1.25 | 0.24 / 0.26 / 0.33 | 0.35 / 0.36 | 41.9 (42.7) | +0.8 (0.24) |
| `P_LO_f` | L | +2.80 | +2.59 | +1.55 | +1.54 | 0.31 / 0.37 / 0.45 | <0.001 / 0.002 | 47.1 (47.7) | +0.5 (0.49) |
| `P_SL_f` | H | +0.16 | +1.06 | +2.36 | +1.75 | 0.072 / 0.075 / 0.10 | 0.23 / 0.24 | 41.8 (42.7) | +0.9 (0.13) |
| `P_SL_f` | L | +3.61 | +3.11 | +1.32 | +2.05 | 0.40 / 0.46 / 0.54 | <0.001 / <0.001 | 47.3 (47.7) | +0.4 (0.63) |
| `W_LO_sp` | HO | -0.08 | -0.31 | -0.05 | +0.00 | 0.16 / 0.12 / 0.13 | 0.43 / 0.22 | 34.8 (34.8) | -0.0 (0.32) |
| `W_LO_sp` | LO | +0.18 | +0.04 | +0.05 | +0.23 | 0.18 / 0.17 / 0.22 | 0.62 / 0.65 | 37.4 (37.4) | +0.0 (0.086) |

* **The direction is consistent.** `P_LO_sp` gains are positive in the Development, Validation, Final and auction windows for both sides, and by calendar year positive in 6 of 7 years for the high and 6 of 7 for the low (not positive in 2024):

| target | 2020 (n=212) | 2021 (n=247) | 2022 (n=247) | 2023 (n=245) | 2024 (n=246) | 2025 (n=248) | 2026 (n=195) |
|---|---|---|---|---|---|---|---|
| H | +3.35 | +0.10 | +4.52 | +2.24 | -1.21 | +0.78 | +4.79 |
| L | +6.59 | +1.60 | +5.10 | +2.07 | -0.23 | +0.32 | +5.10 |

* **Size.** +2.14% (high) and +2.94% (low) pinball in Final; the typical pre-open miss falls by Rs 1.1 (paired p 0.049) and Rs 1.3 (p 0.019). In the Validation window alone the gains are +0.95% / +1.31% (Rs -0.1 / +2.0), not significant on their own (248 sessions).
* **Significance, honestly.** Pooled over all 1,640 evaluated sessions the gain is clearly non-zero (raw p <0.001 for the high and <0.001 for the low; <0.001 and <0.001 with HAC lag 20); inside the Final window alone it is 0.071 (high) and 0.003 (low), 0.16 / 0.028 at lag 20. Because the variant was picked after looking, the pooled p-values overstate the evidence.
* **If it HAD been in the pre-fixed list** (the five conditions evaluated as if, with the Holm that counts every pair I tried; `results/hl2_adoption_posthoc.csv`):

| variant | target | gain % Final | p raw | Holm over all 92 pairs tried | gain % Validation | 50% / 90% band deviation, variant (baseline), points | auction ratio | (i) | (ii) | (iii) | (iv) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `P_LO_b` | H | +2.64 | 0.050 | 1.00 | +1.92 | -1.6 (-3.1) / +1.9 (+0.3) | 0.967 | NO | yes | NO | yes |
| `P_LO_b` | L | +3.29 | 0.002 | 0.18 | +1.40 | +0.0 (+0.3) / -0.3 (-1.2) | 0.960 | NO | yes | yes | yes |
| `P_LO_sp` | H | +2.14 | 0.071 | 1.00 | +0.95 | -0.9 (-3.1) / +1.2 (+0.3) | 0.967 | NO | yes | NO | yes |
| `P_LO_sp` | L | +2.94 | 0.003 | 0.25 | +1.31 | +0.0 (+0.3) / -1.2 (-1.2) | 0.970 | NO | yes | yes | yes |

  `P_LO_sp` on the low would fail only (i) (the Holm-corrected p is not below 0.05 once all the pairs I tried are counted); on the high it would fail (i) and (iii) (its 90% band deviates 1.2 points from nominal against the baseline's 0.3). The leakage test (v) passes for both (Section 9).
* **Size in rupees on 16 Oct.** For the +0.33% S&P move of 15 Oct the shift of the 16 Oct pre-open medians is Rs +3.5 (high) and Rs +4.9 (low) (`results/hl2_2026-10-16.json`, `all_variants`). The effect matters on days when the S&P moved by 1% or more.
* **Consistency with the project's earlier work.** The v2 report validated 'previous US session S&P 500 to BSE gap' (slope 0.276 pp per 1%, walk-forward out-of-sample R2 +7.85%, `FORECAST_REPORT_V2.md` section 2 row 5), and `A_dayahead.md` listed the S&P cue (about Rs 2 on the median) as 'not used, on purpose'. This section is the high/low version of the same channel (through the gap); its size, Rs 1 to 1.4 on the typical miss, is of the same order. It is an echo of a known relationship, not a new one.
* **What I would do (a suggestion, not a test result).** Pre-register `P_LO_sp` as ONE candidate with its two targets (a Holm family of 2), score it forward from the first session after the lead decides (the lead can call `hl2_forecast(date, variant='P_LO_sp')` and compare it with the baseline), and decide after about 120 sessions. Do not switch it on now on this evidence alone.


## 6. The option-implied volatility block (own short window; tested only on that window)

* **History.** BSE ATM implied volatility from NSE F&O settlement prices exists for about 460 sessions, from 29 Nov 2024 (used from the next session, so the first feature value is for 2 Dec 2024; `data/processed/bse_iv_daily.csv` plus the three filled sessions). The walk-forward needs 120 usable rows before a block can be fitted and the cross-validation needs more, so the block was fitted with a finite ridge strength for the first time at the refit of 9 Mar 2026 (`results/hl2_meta.json`, `first_active_block_start_ownwindow`). Only the last seven months of the Validation window (Jul 2024 to Jun 2025) have IV data, and the block cannot be fitted before it has 120 rows: condition (ii) is 'not testable' (counted as not met) for `P_SC_s` and `W_SC_s`; for `P_SC_fs` and `W_SC_fso` the 'features used' part is met through blocks a to e and (ii) is judged on the sign of the Validation gain.
* **Result (tested).** `P_SC_s` Final +0.01% / +0.00% (pre-open), `W_SC_s` -0.01% / +0.22% (after the open), n = 320 (the ridge used the block in 44% of refits). With the other blocks (`P_SC_fs`) the pre-open high is +1.06% (raw p 0.041, Holm 1.00); its Validation gain is -0.40%.
* **Post hoc sensitivity.** With a fixed ridge strength instead of cross-validation (`P_SC_s_fix0.3`, `_fix3`) the Final gains are +0.81% / +0.09% and +0.25% / +0.01%; restricted to the 150 sessions since the block was first usable they are -0.06% / -0.10% and +0.10% / -0.03% (supplementary window, n = 150).
* **Descriptive, not a test.** The 'IV minus recent realised volatility' spread is the one scale feature with a visible univariate association with how far the day's path ranges beyond the baseline scale: Spearman correlation +0.19 in its first window (n = 143, raw p 0.022, Holm within the screen 0.56) and +0.27 in Final (n = 319, raw p <0.001). It did not turn into a forecast gain, which is what one expects if S6 (GARCH plus HAR on gap and Garman-Klass) already carries the same information.
* **Consistent with the project.** `FORECAST_REPORT.md` reports for the options-implied 2.43% per day 'on par with S6 (p = 0.76), no extra edge' (339 sessions). Same verdict here, now for the day's high and low.
* **Verdict.** The IV block cannot be validated out of sample on about 460 sessions; the little that can be tested shows nothing. Keep collecting sessions and re-test when there are about 1,000.


## 7. Post hoc sensitivity: fixed ridge strength instead of cross-validation

The cross-validated ridge switches features off in many refits (Section 4.2). To check that this caution is not what makes everything null, the same models were re-run with the ridge strength FIXED (0.3 or 3 on standardised features, so the features are always on). These are post hoc, outside the family, and cannot be adopted.

| variant (post hoc) | target | Final gain % | raw p | Validation gain % | all 1,640 sessions gain % | Final miss Rs (baseline) |
|---|---|---|---|---|---|---|
| `P_SC_f_fix0.3` | H | +0.58 | 0.29 | -0.77 | -1.06 | 42.6 (42.7) |
| `P_SC_f_fix0.3` | L | -0.15 | 0.80 | +1.08 | +1.29 | 47.8 (47.7) |
| `P_SC_f_fix3` | H | +0.49 | 0.038 | -0.09 | -0.19 | 42.6 (42.7) |
| `P_SC_f_fix3` | L | -0.10 | 0.67 | +0.48 | +0.72 | 47.7 (47.7) |
| `P_LO_f_fix0.3` | H | +1.79 | 0.26 | +0.58 | -0.18 | 41.8 (42.7) |
| `P_LO_f_fix0.3` | L | +1.80 | 0.27 | +2.60 | +2.86 | 47.2 (47.7) |
| `P_LO_f_fix3` | H | +1.34 | 0.067 | +0.66 | +0.58 | 42.0 (42.7) |
| `P_LO_f_fix3` | L | +1.38 | 0.089 | +2.18 | +2.44 | 47.0 (47.7) |
| `P_SL_f_fix0.3` | H | +2.80 | 0.096 | +1.13 | -0.23 | 41.7 (42.7) |
| `P_SL_f_fix0.3` | L | +1.42 | 0.41 | +3.16 | +3.61 | 47.4 (47.7) |
| `P_SL_f_fix3` | H | +2.03 | 0.009 | +0.70 | +0.59 | 41.9 (42.7) |
| `P_SL_f_fix3` | L | +1.22 | 0.16 | +2.49 | +2.99 | 47.0 (47.7) |
| `P_SC_s_fix0.3` | H | +0.81 | 0.10 | -0.03 | +0.11 | 42.5 (42.7) |
| `P_SC_s_fix0.3` | L | +0.09 | 0.77 | +0.03 | +0.02 | 47.6 (47.7) |
| `P_SC_s_fix3` | H | +0.25 | 0.012 | -0.01 | +0.04 | 42.6 (42.7) |
| `P_SC_s_fix3` | L | +0.01 | 0.86 | +0.01 | +0.00 | 47.6 (47.7) |
| `W_SC_fo_fix0.3` | HO | +1.17 | 0.19 | +1.39 | +0.43 | 34.1 (34.8) |
| `W_SC_fo_fix0.3` | LO | -2.85 | <0.001 | -2.49 | -0.33 | 38.2 (37.4) |
| `W_SC_fo_fix3` | HO | +1.12 | 0.041 | +1.41 | +0.90 | 34.4 (34.8) |
| `W_SC_fo_fix3` | LO | -1.47 | 0.004 | -1.33 | +0.12 | 37.7 (37.4) |
| `W_LO_fo_fix0.3` | HO | -1.88 | 0.088 | -1.81 | -1.83 | 34.9 (34.8) |
| `W_LO_fo_fix0.3` | LO | -3.38 | <0.001 | -1.26 | -0.39 | 38.7 (37.4) |
| `W_LO_fo_fix3` | HO | -0.60 | 0.13 | -0.89 | -0.50 | 34.8 (34.8) |
| `W_LO_fo_fix3` | LO | -1.23 | 0.031 | +0.08 | +0.53 | 37.7 (37.4) |
| `W_SC_s_fix0.3` | HO | -0.21 | 0.49 | -0.02 | -0.03 | 34.7 (34.8) |
| `W_SC_s_fix0.3` | LO | +0.70 | 0.12 | -0.04 | +0.12 | 37.4 (37.4) |
| `W_SC_s_fix3` | HO | -0.03 | 0.61 | -0.00 | -0.00 | 34.8 (34.8) |
| `W_SC_s_fix3` | LO | +0.18 | 0.051 | -0.01 | +0.03 | 37.4 (37.4) |

Reading: forcing the features in does not rescue the scale blocks (pre-open all-block scale: +0.58% / -0.15% at 0.3, +0.49% / -0.10% at 3), keeps the pre-open location variants at +1.2% to +2.8% in Final (with the low consistently positive in Development and Validation, Section 4.3 table), and keeps the after-open low negative (-2.85% / -1.47% for the all-block scale, -3.38% / -1.23% for the location). The cross-validation was therefore not hiding a scale effect.


## 8. Descriptive: which inputs carry any association at all (cannot lead to adoption)

**Univariate screen** (`results/hl2_univariate.csv`; Spearman correlation of a feature with what the baseline leaves unexplained; Development+Validation sessions and Final sessions kept apart; the Holm column corrects within each screen of about 20 to 40 features; 183 correlations in all, so expect a few false positives; descriptive).

*Pre-open, location of the HIGH (high / baseline scale):*
| feature (block) | Spearman, Dev+Val (n) | Holm in screen | Spearman, Final (n) | raw p Final | same sign |
|---|---|---|---|---|---|
| `sp_ret` (b) | +0.18 (1320) | <0.001 | +0.23 (320) | <0.001 | yes |
| `dvixus` (b) | -0.14 (1320) | <0.001 | -0.24 (320) | <0.001 | yes |
| `close_loc_c` (d) | +0.13 (1320) | <0.001 | +0.09 (320) | 0.100 | yes |
| `ret1` (d) | +0.10 (1320) | 0.005 | +0.08 (320) | 0.17 | yes |
| `rel_nifty` (d) | +0.08 (1320) | 0.037 | +0.10 (320) | 0.074 | yes |

*Pre-open, location of the LOW:*
| feature (block) | Spearman, Dev+Val (n) | Holm in screen | Spearman, Final (n) | raw p Final | same sign |
|---|---|---|---|---|---|
| `sp_ret` (b) | +0.22 (1320) | <0.001 | +0.27 (320) | <0.001 | yes |
| `br_adv` (c) | +0.20 (1320) | <0.001 | -0.04 (320) | 0.45 | no |
| `nifty_ret` (c) | +0.18 (1320) | <0.001 | +0.07 (320) | 0.23 | yes |
| `dvixus` (b) | -0.17 (1320) | <0.001 | -0.26 (320) | <0.001 | yes |
| `close_loc_c` (d) | +0.16 (1320) | <0.001 | +0.06 (320) | 0.29 | yes |

*Pre-open, scale (path range / baseline scale):*
| feature (block) | Spearman, Dev+Val (n) | Holm in screen | Spearman, Final (n) | raw p Final | same sign |
|---|---|---|---|---|---|
| `cap_lnrange` (s) | +0.20 (156) | 0.28 | +0.07 (320) | 0.24 | yes |
| `iv_rv_spread` (s) | +0.19 (143) | 0.56 | +0.27 (319) | <0.001 | yes |
| `peers_lnrange_rel` (c) | +0.12 (1320) | <0.001 | +0.06 (320) | 0.30 | yes |
| `iv_skew` (s) | +0.11 (140) | 1.00 | -0.01 (319) | 0.79 | no |
| `abs_sp` (b) | +0.08 (1320) | 0.18 | +0.06 (320) | 0.32 | yes |

*After the open, scale:*
| feature (block) | Spearman, Dev+Val (n) | Holm in screen | Spearman, Final (n) | raw p Final | same sign |
|---|---|---|---|---|---|
| `cap_lnrange` (s) | +0.18 (156) | 0.42 | +0.09 (320) | 0.13 | yes |
| `iv_rv_spread` (s) | +0.15 (143) | 1.00 | +0.20 (319) | <0.001 | yes |
| `orel_abs` (o) | +0.14 (1320) | <0.001 | +0.06 (320) | 0.27 | yes |
| `peers_lnrange_rel` (c) | +0.12 (1320) | <0.001 | +0.07 (320) | 0.24 | yes |
| `pk20_rel` (d) | -0.11 (1320) | 0.002 | -0.16 (320) | 0.004 | yes |

Reading: the strong, same-signed-in-both-windows associations are with the LOCATION of the pre-open high and low and come from the US overnight block (S&P return positive, US VIX change negative; they are the same news seen twice). For the SCALE the strongest associations are small (|rho| about 0.1 to 0.3) and are for the implied-vol spread (own short window), Capital Markets index range, peers' relative range and (after the open) the position of the open in yesterday's range, none of which survived as a forecast gain above.

**Coefficients of the all-block models** (mean over the refits in which the features were switched on; scale coefficients are effects on ln(scale) per standard deviation of the feature before the clip at +-1; location coefficients are shifts in units of the standardised residual per standard deviation):
* `P_SC_f` (pre-open scale): `abs_sp` +0.020 (100% of 68 refits positive); `pk10_rel` +0.016 (100% of 68 refits positive); `br_tails` +0.015 (100% of 68 refits positive); `peers_lnrange_rel` +0.013 (100% of 68 refits positive); `fri` -0.013 (4% of 68 refits positive); `abs_dxy` -0.012 (0% of 68 refits positive).
* `W_SC_fo` (after-open scale): `absgap_z` +0.027 (100% of 83 refits positive); `orel_abs` +0.024 (100% of 83 refits positive); `br_tails` +0.016 (100% of 83 refits positive); `beyond_any` +0.014 (100% of 83 refits positive); `peers_lnrange_rel` +0.013 (100% of 83 refits positive); `pk20_rel` -0.012 (2% of 83 refits positive).
* `P_LO_f` (pre-open location): `sp_ret`/L +0.083 (100% of 83 refits positive); `sp_ret`/H +0.077 (100% of 73 refits positive); `br_adv`/L +0.063 (100% of 83 refits positive); `tue`/L +0.057 (100% of 83 refits positive); `close_loc_c`/H +0.040 (99% of 73 refits positive); `dvixus`/L -0.032 (0% of 83 refits positive); `tue`/H +0.030 (100% of 73 refits positive); `close_loc_c`/L +0.027 (100% of 83 refits positive).
The scale coefficients are small (about 0.01 to 0.03 per standard deviation, i.e. a 1 to 3% change of the scale), consistent with S6 already carrying most of the predictable variation of the range.


## 9. Leakage and timestamp checks (condition v and the feature rules)

**Leakage test** (`--leakage`, `results/hl2_leakage.csv`). For 12 target sessions spread over Development (3), Validation (3) and Final (6, of which the last three are in the closing-auction slice) (21 Mar 2022 and 23 May 2025 are the bonus ex-dates), every pre-fixed variant, the baseline, the placebos and the three post hoc location variants, I rebuilt the whole pipeline (S6 paths, features, ridge, cross-validation, quantiles) from tables in which everything dated from the target session onward is junk (random coherent OHLC, volumes and delivery for BSE; bootstrap-times-noise for the index, breadth, peers, F&O IV and the US / FRED series; random expiry and results dates after the session), and compared with the forecast from the real tables.

| test | comparisons | largest difference (log points) | forecasts that changed (> 1e-9) |
|---|---|---|---|
| all data from the target session on replaced by junk, open junked too (pre-open variants) | 180 | 0 | 0 |
| same, the session's own official open and previous close kept (after-open variants) | 208 | 0 | 0 |
| POSITIVE CONTROL: BSE bars junked from the day BEFORE the target session (4 sessions; must change every forecast) | 120 | 0.028 | 120 |
| POSITIVE CONTROL: index, breadth, peers, IV, US series junked from the day before (4 sessions; must change every variant that uses them) | 120 | 0.046 | 69 |
| live 16 Oct forecast: the real 16 Oct bar and later rows present vs removed (28 variants + default) | 29 | 0 | 0 |

Pass = largest difference below 1e-9; every one of the 417 leakage comparisons is identical (largest difference 0.0). The positive controls show that the test can see a leak: junking the BSE bars from the day before the target changes all 120 forecasts, junking the other tables from the day before changes 69 of 120 (consistent with: the variants whose features come from those tables and are switched on in that refit change; the baseline, the placebos, the calendar and BSE-own-bars blocks cannot depend on them). For the after-open variants the target session's own official open and previous close are kept because they are legitimately known at 09:08. **Flags known in advance:** the target session's own expiry / results flag is kept (calendar facts); every F&O expiry date from 18 Nov 2024 to 15 Oct 2026 (22 dates) first appears in a contract list dated at least 27 days earlier (median 90; `results/hl2_expiry_advance_check.csv`), and the results dates are announcements made after the close of the previous session (`data/results_dates.csv`).

**The 16 Oct session.** Junking the real 16 Oct bar and every later row leaves all 28 variants' live quantiles unchanged (largest difference 0.0), and so does simply leaving the real 16 Oct bar in the tables (`real_16Oct_data_present_vs_removed`): the live forecast uses rows dated before 16 Oct only.

**Timestamp spot check** (`--spotcheck`, `results/hl2_spotcheck.csv`): 1280 feature values (64 sessions, including 12 and 15 Oct 2026 and the bonus ex-dates 21 Mar 2022 and 23 May 2025, x 20 features across all blocks) recomputed from the input tables with a separate plain implementation of the rules; 1280 of 1280 match. The US rule was also checked by hand for the session of 15 Oct: it uses the S&P 500 / US VIX of the US session dated 14 Oct (closed 01:30 IST on 15 Oct), -1.11% and 16.87.

**Coverage of the live inputs.** For the 16 Oct forecast four features are missing and enter as zero effect: Brent and the dollar index (levels and changes), because the FRED files stop on 6 Oct and 2 Oct. They would matter only for variants that are not in use. S&P 500 and US VIX for the 15 Oct US session, USD/INR (ECB, 15 Oct), India VIX, breadth, peers, BSE option IV and delivery % of 15 Oct were filled from the sources listed in Section 3 (the last few US / FX numbers come from Yahoo and Frankfurter: unofficial feeds).


## 10. The 16 Oct 2026 forecast: baseline and every variant (as of the 15 Oct close; official open Rs 3,450.0; `results/hl2_2026-10-16.json`)

Reference: official close of 15 Oct Rs 3,428.0; open Rs 3,450.0 (gap +0.64%); baseline sigma 2.43% (close-to-close) and 2.22% (open-to-close). Medians in rupees, with the 50% band in brackets. **Because no variant was adopted, `hl2_forecast('2026-10-16', 3450.0)` returns the baseline** (`variants_used`: `P_S6` for the pre-open high and low, `W_I6` for the after-open high and low; difference to `hl_model.hl_forecast` over every printed quantile: 0.00 rupees).

| model | pre-open HIGH median (q25-q75) | pre-open LOW median (q25-q75) | after-open HIGH median (q25-q75) | after-open LOW median (q25-q75) |
|---|---|---|---|---|
| BASELINE `P_S6` / `W_I6` (the live forecast) | 3,475.0 (3,449-3,513) | 3,390.1 (3,352-3,419) | 3,488.5 (3,468-3,526) | 3,409.9 (3,374-3,430) |
| all blocks, scale: `P_SC_f` / `W_SC_fo` | 3,471.9 (3,448-3,506) | 3,394.1 (3,357-3,420) | 3,490.4 (3,468-3,529) | 3,408.5 (3,371-3,429) |
| scale + location: `P_SL_f` / `W_SL_fo` | 3,479.9 (3,456-3,514) | 3,400.3 (3,364-3,424) | 3,492.0 (3,470-3,531) | 3,409.6 (3,372-3,431) |
| location only: `P_LO_f` / `W_LO_fo` | 3,480.6 (3,455-3,518) | 3,398.3 (3,362-3,424) | 3,490.5 (3,469-3,527) | 3,410.6 (3,376-3,432) |
| IV + all blocks: `P_SC_fs` / `W_SC_fso` | 3,473.1 (3,448-3,507) | 3,393.6 (3,357-3,420) | 3,490.8 (3,468-3,529) | 3,408.4 (3,371-3,429) |
| high / low sides separate: `P_TS_f` / `W_TS_fo` | 3,475.9 (3,451-3,515) | 3,396.5 (3,365-3,421) | 3,494.5 (3,469-3,535) | 3,409.9 (3,374-3,430) |
| POST HOC S&P shift: `P_LO_sp` / `W_LO_sp` | 3,478.6 (3,452-3,515) | 3,394.9 (3,357-3,422) | 3,488.5 (3,468-3,526) | 3,410.2 (3,374-3,430) |
| POST HOC US block shift: `P_LO_b` | 3,478.3 (3,452-3,515) | 3,395.0 (3,357-3,424) | - | - |

* **Baseline, as quoted before:** pre-open high 3,475.0 (90%: 3,421 to 3,591), low 3,390.1 (3,269 to 3,450); after the open high 3,488.5 (3,451 to 3,591), low 3,409.9 (3,294 to 3,447). These are the lead's 3,475 / 3,390 / 3,488 / 3,410 to the rupee.
* **How far any variant moves the median** on this day: at most Rs 10.2 pre-open and Rs 6.1 after the open, against typical misses of Rs 43 to 48 and Rs 35 to 37. On this day the choice of model would not matter in practice; the S&P move of 15 Oct was small (+0.33%).
* **Missing inputs on this date** (zero effect in every variant): `abs_brent`, `abs_dxy`, `brent_ret`, `dxy_ret`.


## 11. What failed or came out null, honest limits, and where this meets earlier project statements

**Null or worse (all tested, Final n = 320):** every scale block a to e and s; all of them together; the tail-specific version; the calendar block; the opening-gap block; the location variants after the open (worse: -1.15% / -2.14%); scale plus location after the open (low -3.86%, Holm 0.004). The pre-fixed `P_LO_f` / `P_SL_f` (all signed features) are ties that fail the significance condition. Untested for lack of history: GIFT Nifty, NSE pre-open order book, FII/DII flows.

**Honest limits.**
* **Power.** With 320 Final sessions the standard error of a pinball gain is 0.2 to 1.6 points for the all-block variants. A null here means 'no gain large enough to see after correcting for 46 comparisons', not 'proved zero'. The largest plausible true gains (1 to 3%) are worth Rs 0.4 to 1.3 on the typical miss.
* **One regime.** The Final window is 1 Jul 2025 to 15 Oct 2026; the auction slice (n = 52) is one drawdown episode after the closing auction began. Signs flip across windows for almost every variant.
* **Design choices that could hide an effect.** The scale model is a log-link multiplier clipped to [e^-1, e^1] on top of S6, with winsorised standardised features, missing values set to the training mean, and a ridge chosen by forward-chaining CV; the location model is a linear shift. Non-linear learners, quantile regression and analogue methods are the other specialists' work (`E_quantile.md`, `G_analogue.md`) and are not covered here. The fixed-ridge check (Section 7) argues against the shrinkage being the culprit.
* **Selection history.** The baseline S6 was itself chosen by the project on the Validation + Final windows (`verify_A`, items 9 and 10), so 'out-of-sample tested' is the right phrase for the Final results, not 'validated'. The post hoc variants of Sections 5 to 7 were added after results were seen.
* **Rupees** are log errors times Rs 3,428 (the 15 Oct close); the OHLC levels in `bse_daily.csv` are raw traded prices before the bonus ex-dates, so rupee figures from the file itself are not comparable across them. Targets are the NSE official high and low; a Yahoo chart reads a rupee or two inside them (`A_dayahead.md` 4.9).
* **Data.** The last three sessions of several input tables were filled from outside the repo's processed files (Section 3); the Yahoo / Frankfurter numbers are unofficial feeds; FRED files for Brent and the dollar index are stale for 16 Oct.
* **Condition (iii)** (coverage 'not worse than the baseline's') is strict when the baseline's deviation is tiny: 29 of 46 pairs fail it, mostly on the 50% band. It did not decide any verdict, because condition (i) fails for every pair.

**Where this meets earlier project statements (none is contradicted).**
* `FORECAST_REPORT.md` (options-implied 2.43% per day 'on par with S6 (p = 0.76), no extra edge', 339 sessions): confirmed for the day's high and low (Section 6).
* `docs/PREREGISTRATION.md` S5 `har_x` (S4 plus ln VIX, Nifty realised vol, turnover z, Nifty |ret|) did not beat S6 in the project's model selection; blocks a, c and d here are the same kind of input as an add-on to S6 and are null again.
* `FORECAST_REPORT_V2.md` validated 'previous US session S&P 500 to BSE gap' and `A_dayahead.md` listed the S&P cue as 'not used, on purpose' and 'not tested here'. Now tested for the high and low: it is the one input that helps, before the open, by Rs 1 to 1.4 on the typical miss (post hoc, Section 5), and not after the open.
* `A_dayahead.md`: 'gap size and direction add nothing beyond the open's level' and the weekday multiplier null: consistent with the null of blocks o and e.
* `B_liveintraday.md` (realised volatility so far, range so far and a day-ahead EWMA did not improve the live bands after Holm): same kind of verdict for the day-ahead scale here.
* **Note for the lead (code behaviour, not edited by me):** `hl_model.load_ohlc()` now returns the 16 Oct bar (see Section 1), so a fresh `hl_model.py --eval` would include that session; and `data/processed/bse_daily.csv` still ends on 13 Oct (14 to 16 Oct are in `bse_daily_extra.csv`).


## 12. Numbers to quote (with n; every one is read from a file I wrote)

| number | value | file and column |
|---|---|---|
| Final sessions / Validation / Development / auction slice | 320 / 248 / 1,072 / 52 | `hl2_meta.json` windows_n |
| Variants / pairs in the Holm family / features searched | 23 / 46 / 58 (40 scale, 28 location, in 7 blocks) | `hl2_meta.json` |
| Post hoc variants (outside the family) / all pairs incl. placebo | 21 / 92 | `hl2_eval_dm_holm.csv` (window final, column holm_incl_posthoc) |
| Baseline typical miss, Final n = 320 (Rs at 3,428): pre-open high / low | 42.7 / 47.7 | `hl2_eval_summary.csv` mae_med_rs_at_now (P_S6, final) |
| Baseline typical miss: after-open high / low | 34.8 / 37.4 | same (W_I6, final) |
| Baseline pinball x1e4, Final: pre-open H / L; after-open HO / LO | 31.15 / 36.58; 23.85 / 28.03 | `hl2_eval_summary.csv` pinball_x1e4; `hl2_baseline_repro.csv` |
| Variants adopted (all five conditions) for any target | none (0 of 46 pairs) | `hl2_adoption.csv` column adopted |
| Best pre-fixed pair: `P_SL_f` pre-open high, Final | +2.36% pinball, raw p 0.072, Holm 1.00; miss Rs 41.8 vs 42.7 | `hl2_eval_dm_holm.csv`, `hl2_eval_medmiss.csv` |
| Worst pre-fixed pair: `W_SL_fo` after-open low, Final | -3.86% pinball, Holm 0.004; miss Rs 38.6 vs 37.4 | same |
| Pairs with Final gain >= 2% / raw p < 0.05 and better / Holm < 0.05 and better / raw p < 0.05 and worse | 1 / 1 / 0 / 8 (of 46) | `hl2_eval_dm_holm.csv` (window final, in_family) |
| Largest improvement of the typical miss by any pre-fixed variant: pre-open / after-open | Rs 0.9 / Rs 0.5 | `hl2_adoption.csv` miss_med_rs_base - miss_med_rs_var |
| India VIX block (a), Final gain pre-open H / L | +0.00% / +0.00% | `hl2_eval_dm_holm.csv` gain_pct |
| Implied-vol block (s), Final gain pre-open H / L; after-open HO / LO | +0.01% / +0.00%; -0.01% / +0.22% | same |
| US block as scale (b), Final gain pre-open H / L | -0.17% / +0.07% | same |
| All blocks as scale, Final gain pre-open H / L; after-open HO / LO | +0.60% / -0.09%; +1.20% / -1.93% | same |
| POST HOC S&P shift `P_LO_sp`, Final gain H / L (n = 320); typical miss gain Rs | +2.14% / +2.94%; Rs 1.1 / 1.3; NOT adopted, optimistic p | `hl2_eval_dm_holm.csv`, `hl2_eval_medmiss.csv`, `hl2_adoption_posthoc.csv` |
| `P_LO_sp` gain by window H / L: Dev / Val / Final / auction | +1.94%,+3.02% / +0.95%,+1.31% / +2.14%,+2.94% / +3.30%,+2.96% | same |
| S&P down >= 0.5% vs up >= 0.5%: median day high / low vs previous close (n = 397 / 514) | +1.39% / -1.72% vs +2.01% / -0.90% | `hl2_sp_buckets.csv` |
| Leakage test: comparisons identical / largest difference | 417 of 417 / 0.0 | `hl2_leakage.csv` |
| Timestamp spot check | 1280 of 1280 feature values match | `hl2_spotcheck.csv` |
| 16 Oct 2026 baseline (unchanged, nothing adopted): pre-open high / low median | 3,475 / 3,390 | `hl2_2026-10-16.json` pre_open |
| 16 Oct 2026 baseline after the Rs 3,450.0 open: high / low median | 3,488 / 3,410 | `hl2_2026-10-16.json` post_open |
| One fresh day, 16 Oct 2026 (n = 1, descriptive): realised high / low; baseline median miss pre-open high / low; after-open high / low | 3,455.0 / 3,310.6; Rs 20.0 / 79.5; Rs 33.5 / 99.3 (a down day, close -1.9% on the previous close) | `hl2_fresh_16oct.csv` (variant `P_S6` / `W_I6`, columns miss_rs) |
| Full pipeline re-run in the third session (`--eval`, `--finalize`, `--baseline-check`): files with identical content | 32 of 32 `results/hl2_*` files (row order differs; run time in `hl2_meta.json`) | Section 14.1 |

Say 'out-of-sample tested', never 'validated'. Say 'no extra parameter improved the high/low forecast' and 'the S&P overnight shift is a post hoc candidate worth about Rs 1 on the pre-open miss'; do not say the S&P shift is proven or adopted.


## 13. Reproduce every number (repo root `/home/user/pred_18`; python3; no network except `--refresh-fill`)

```
python3 src/hl_model2.py --baseline-check             # baseline reproduced from this engine           -> results/hl2_baseline_repro.csv           (~20 s)
python3 src/hl_model2.py --eval --jobs 4              # all variants, DM, Holm, adoption conditions    -> results/hl2_eval_*.csv, hl2_adoption*.csv, hl2_coefs.csv, hl2_predictions.csv.gz,
                                                       #    hl2_features_panel.csv.gz, hl2_feature_timestamps.csv, hl2_univariate.csv, hl2_meta.json  (~4-5 min on 4 free cores)
python3 src/hl_model2.py --leakage --jobs 4           # junk-replacement leakage test + expiry check; sets 'adopted' in hl2_adoption.csv -> results/hl2_leakage.csv, hl2_expiry_advance_check.csv  (~10-15 min)
python3 src/hl_model2.py --spotcheck                  # timestamp spot check                            -> results/hl2_spotcheck.csv
python3 src/hl_model2.py --sp-buckets                 # descriptive S&P table                           -> results/hl2_sp_buckets.csv
python3 src/hl_model2.py --tables                     # the markdown tables of Section 4 from the result files
python3 src/hl_model2.py --date 2026-10-16 --open 3450 --save    # -> results/hl2_2026-10-16.json (baseline unless a variant was adopted; all variants for comparison)
python3 src/hl_model2.py --date 2026-10-16 --open 3450 [--variant P_LO_sp]   # words; --variant forces one variant (comparison only)
python3 src/hl_model2.py --finalize                   # re-merge hl2_leakage.csv into hl2_adoption.csv (also done at the end of --leakage)
python3 src/hl_model2.py --fresh-day                  # descriptive, one session (16 Oct 2026): the stored live forecasts scored against the official bar -> results/hl2_fresh_16oct.csv (Section 14.3)
python3 src/hl_model2.py --refresh-fill               # NETWORK: rebuild results/hl2_fill_*.csv and hl2_data_usdinr_ecb.csv (cached copies are in the repo)
```
```
from hl_model2 import hl2_forecast          # same dict shape as hl_model.hl_forecast
hl2_forecast("2026-10-16", open_price=3450.0)                   # default: the adopted variant per target, else the baseline (here: the baseline)
hl2_forecast("2026-10-16", open_price=3450.0, variant="P_LO_sp") # one variant for its phase, for comparison only
```
Run order matters once: `--eval` rewrites `hl2_adoption.csv` without the leakage verdict, `--leakage` (or `--finalize`) adds it. The runs are deterministic in content (fixed seeds: placebo 20261016, leakage junk seeds in the code); the row ORDER of `hl2_coefs.csv`, `hl2_eval_summary.csv` and `hl2_predictions.csv.gz` can differ between runs because the parallel workers finish in a different order, so compare them after sorting (Section 14.1); on a loaded machine they take several times longer. Per-window tables for any pair: `results/hl2_eval_dm_holm.csv` (columns window, gain_pct, p_two_sided, holm_two_sided, p_two_sided_lag10 / lag20), coverage: `hl2_eval_summary.csv`, rupee misses: `hl2_eval_summary.csv` (mae_med_rs_at_now) and `hl2_eval_medmiss.csv` (paired tests), quantile forecasts: `hl2_predictions.csv.gz` (q5 / q25 / q50 / q75 / q95 per session, variant and target).


## 14. Third session (Sat 17 Oct 2026): re-verification, a drop-in fix, and one fresh day (16 Oct 2026)

*This section was written after the adoption decision (none adopted). Nothing here changes a result, the rule, the family or a verdict.*

### 14.1 What was re-checked (tested by re-running; all deterministic in content)
* **Section 0 unchanged.** The SHA-256 of the text from `## 0. Pre-fixed section` to the end of 0.9 (14,864 characters) is still `1274b181b0e084066db1f05698009441570cf5d84dfcc186ae7ba3ce84c83239`, equal to `results/hl2_prefixed_sha256.txt`.
* **Baseline reproduced again** (`--baseline-check`): every compared cell (Final and auction slice, pre- and post-open) differs from the stored `hl_eval_*open.csv` by 0.0; the output file is byte-identical to the stored one (same md5). Final n = 320: pre-open pinball x1e4 31.15 / 36.58, typical miss Rs 42.7 / 47.7; after the open 23.85 / 28.03, Rs 34.8 / 37.4.
* **The full evaluation was re-run** (`--eval --jobs 4`, 213 s, then `--finalize`) after the small code change below. Compared with copies of the stored files, all 32 `results/hl2_*` files have identical content (the three big tables `hl2_coefs.csv`, `hl2_eval_summary.csv`, `hl2_predictions.csv.gz` only differ in row ORDER until they are sorted; after sorting the largest difference is 0.0; `hl2_meta.json` differs only in the run time in seconds). Verdict unchanged: `adopted by the full rule: none`.
* **Headline counts recomputed from `hl2_eval_dm_holm.csv` and `hl2_adoption.csv`** (Final, 46 pairs): 22 pairs with a positive gain, 1 with a gain of 2% or more (`P_SL_f` pre-open high, +2.36%, raw p 0.072, Holm 1.00), 1 better at raw p < 0.05 (`P_SC_fs` high, +1.06%), 0 better after Holm, 8 worse at raw p < 0.05, 1 worse after Holm (`W_SL_fo` low, -3.86%, Holm 0.004). Conditions met by how many of the 46 pairs: (i) 0, (ii) 17, (iii) 17, (iv) 46, (v) 46; adopted 0 of 46.
* **Leakage file recounted** (`hl2_leakage.csv`, 657 rows): junk-from-target-session 180 of 180 identical, same with the open kept 208 of 208, live 16 Oct present-versus-removed 29 of 29 identical (largest difference 0.0); the positive controls change 120 of 120 (bars) and 69 of 120 (other tables) forecasts, so the test can see a leak. The leakage test was also re-run in full with the final code (`--leakage --jobs 4`, about 17 minutes on a loaded machine): 417 of 417 comparisons identical (worst difference 0.0), positive controls 189 of 240 forecasts changed, expiry dates known at least 27 days ahead, adopted by the full rule: none; `hl2_leakage.csv`, `hl2_adoption.csv` and `hl2_expiry_advance_check.csv` have the same content as before.

### 14.2 A drop-in fix (output keys only; no forecast number changed)
`hl_model.hl_forecast()` returns two fields that `hl2_forecast()` did not: `data_sha256` (a fingerprint of the input files) and `cas_slice_tail_shares` (the closing-auction tail check, which `hl_model.words()` turns into a printed caution when more than 10% of the 52 sessions fell outside the 5% / 95% quantile; on 16 Oct it is the pre-open high, 15% below the 5% quantile). A swap would have dropped that caution silently. `hl2_forecast()` now returns both fields (the second only for pre-open variants, read from `hl2_eval_summary.csv`), and `words2()` prints the same caution. After the change, every key of the baseline's output exists in `hl2_forecast()`'s output, every numeric field they share is identical to 1e-9, and the saved `results/hl2_2026-10-16.json` differs from the earlier one only by the added keys. Extra keys of `hl2_forecast()` that the baseline does not have: `variants_used`, `adopted_variants`, `features_missing_on_the_forecast_date_pre_open_scale_and_location`, `variant` inside each side, and `all_variants` (only when asked for).

### 14.3 One fresh day: the session of 16 Oct 2026 (n = 1; descriptive; scored after the decision)
The official bar of 16 Oct is in `data/processed/bse_daily_extra.csv` (open 3,450.0, high 3,455.0, low 3,310.6, close 3,363.0; previous close 3,428.0). It was not used for any fitting, feature, choice or test above: the forecasts below are the ones stored in `results/hl2_2026-10-16.json`, made from data through 15 Oct and the official open of Rs 3,450.0. The full table for every variant is `results/hl2_fresh_16oct.csv` (command: `python3 src/hl_model2.py --fresh-day`; same quantiles as the live forecast; pinball over the same 9-level grid, x1e4 in log points).

| target | realised | baseline median (50% band) | miss of the baseline median (typical miss in Final) | where it fell in the baseline's distribution | 'price stays' / 'open stays' miss |
|---|---|---|---|---|---|
| pre-open HIGH | 3,455.0 | 3,475.0 (3,449 to 3,513) | Rs 20.0 (Rs 42.7) | inside the 50% band, between the 25% and 50% quantiles | Rs 27.0 / - |
| pre-open LOW | 3,310.6 | 3,390.1 (3,352 to 3,419) | Rs 79.5 (Rs 47.7) | below the 50% band, between the 10% and 25% quantiles | Rs 117.4 / - |
| after-open HIGH | 3,455.0 | 3,488.5 (3,468 to 3,526) | Rs 33.5 (Rs 34.8) | below the 50% band, between the 10% and 25% quantiles (the open was within Rs 5 of the high) | - / Rs 5.0 |
| after-open LOW | 3,310.6 | 3,409.9 (3,374 to 3,430) | Rs 99.3 (Rs 37.4) | below the 50% band, between the 5% and 10% quantiles | - / Rs 139.4 |

It was a down day: the close of Rs 3,363.0 was 1.9% below the previous close (2.5% below the open). The low side was therefore missed by 1.7 times (pre-open) and 2.7 times (after the open) the Final-window typical miss, and the baseline pinball on the after-open low was 56.4 against a Final mean of 28.0. Both extremes of every target were still inside the baseline's 90% bands. One session cannot show a model is right or wrong.

Scored on this one day, the 13 non-baseline variants of each target against the baseline's pinball (ties = identical to the baseline because the ridge switched the features off or the shift was zero): pre-open high better 4, worse 7, identical 2; pre-open low better 0, worse 11, identical 2; after-open high better 2, worse 8, identical 3; after-open low better 6, worse 4, identical 3. Best single result +9.2% (`P_SC_f`, pre-open high), worst -20.6% (`P_SL_f`, pre-open low). The 'all blocks' scale variants: `P_SC_f` missed the pre-open high median by Rs 16.9 (baseline Rs 20.0) and the low by Rs 83.5 (Rs 79.5); `W_SC_fo` missed the after-open high by Rs 35.4 (Rs 33.5) and the low by Rs 97.9 (Rs 99.3). The post hoc S&P shift variants (`P_LO_sp`, `P_LO_b`) moved the pre-open medians up by only Rs 3 to 5 (the S&P move of 15 Oct was a small +0.33%) and were 3.5% and 1.6% worse on the high and 5.5% and 7.5% worse on the low, because the day was down. **This single day does not change any verdict in Sections 2 to 11 and must not be used to rank the variants.**
