# Independent verification of specialist A (day-ahead and post-open high / low)

Verifier report on `research/hl/A_dayahead.md`, `src/hl_model.py` and `results/hl_dayahead_2026-10-16.json`, `results/hl_eval_*.csv`.
Written Thu 15 Oct 2026 (late evening IST). No data dated after 15 Oct 2026 22:00 IST was opened (the hourly Yahoo file ends at the 15 Oct 15:15 bar; I checked its timestamps only). I did not edit any file except this one; every run that writes files was done in an isolated copy in the scratchpad.

## 0. Verdict

**Pass with fixes needed. Severity: minor.** Every number I tested reproduces from the raw data files, to rounding, with my own code. I found no look-ahead and no arithmetic error. The fixes needed are (a) a few sentences that claim more than the numbers support, (b) one mislabelled band in the command-line output (the "nine times in ten" band for the after-open HIGH is really a 19-in-20 band), (c) the command-line output does not carry the report's own warnings (rupees scaled to today's price, 50% bands too narrow in the last 52 sessions), and (d) weak input checking in the command line tool. Section 7 lists what the lead may quote as it stands, what to correct (with the corrected value) and what not to quote.

Plain-words summary of what the evidence supports (all of it is the builder's own result, which I confirmed):
* Tonight's best guesses and ranges (HIGH median Rs 3,475, LOW median Rs 3,390) are correctly computed from the stated method.
* The best guess is good to about Rs 43 (high) and Rs 48 (low) on average at today's price, and about Rs 34 / Rs 32 half the time. Knowing the official open at 09:08 cuts that to about Rs 35 / Rs 37. These are real, out-of-sample, and statistically solid.
* Tonight the volatility model adds essentially nothing to a plain "last 250 sessions" history: its 90% band for the high is Rs 3,421 to 3,591 and the plain-history band is Rs 3,418 to 3,592; low Rs 3,269 to 3,450 versus Rs 3,278 to 3,457; medians Rs 3,475 / 3,390 versus Rs 3,479 / 3,390 (Section 5). The builder says the model's value is "in the band shape, not the best guess"; tonight even the band shape is nearly the same.

## 1. What I checked and how

My code is in `/tmp/claude-0/-home-user-pred-18/01384b6e-cd11-5bbc-b7f5-2dd03125e5eb/scratchpad/verA/` (`indep.py` is the library; it imports nothing from `src/`). It reads `data/processed/bse_daily.csv` + `bse_daily_extra.csv` directly.

Independence limit, stated plainly: I read `src/models.py` before re-typing the S6 volatility model (GARCH(1,1)-t refit every 20 sessions on data before each block, times a HAR on the variance proxy, geometric mean). So the S6 re-implementation is a second typing of the same specification, not a second specification. I checked it against the project's stored sigma (`results/forecasts_R.csv`, `forecasts_I.csv`, written by the project's earlier code): maximum relative difference 8.2e-15 (R) and 9.1e-15 (I) over 1,887 sessions. Everything built on top of sigma (bootstrap windows, standardisation, quantiles, windows, pinball, coverage, Kupiec, Diebold-Mariano with Newey-West lag 5 and the Harvey-Leybourne-Newbold factor, Holm, rupee conversion, all 18 variants) I coded from the report's definitions, not from the builder's functions.

| step | what I did | result |
|---|---|---|
| A. data | read raw files, checked adjustments | 2,390 sessions (2,388 + 14, 15 Oct); `prev` equals the previous close on all 2,387 ordinary sessions; on the two ex-dates (2022-03-21, 2025-05-23) `prev` is the prior close / 3.000 exactly |
| B. S6 sigma | re-fitted all walk-forward blocks for R and I | matches project's stored sigma to 1e-14; next-session sigma_R = 2.4348% (builder 2.4348%), sigma_I = 2.2159% |
| C. walk-forward quantiles | rebuilt P_S6 and W_I6 quantiles for all 1,640 evaluation sessions (28 stored columns per session) | maximum difference to `hl_eval_predictions.csv`: 1.8e-12 rupees |
| D. all window metrics | pinball, 50/90% coverage, Kupiec, tail shares, mean and median miss, standard error for P_S6 and W_I6 in dev / val / valfinal / final / cas | maximum absolute difference over all rows and columns: 1.4e-14 |
| E. every variant | rebuilt all 9 pre-open and 10 post-open variants, plus PRICE_STAYS and OPEN_STAYS, and compared 266 variant-window rows | identical except P_S0 and P_S1 in the Development window (Section 6, item 11) |
| F. tests | rebuilt DM (lag 5, HLN) and Holm for all six families, 208 rows | maximum difference: gain 7e-15, p 2e-15, Holm 3e-15; 0 rows missing either way |
| G. live forecast | rebuilt the 16 Oct quantiles, widths, touch probabilities, flat-open post-open table | all quantiles within Rs 0.005; widths and touch probabilities identical |
| H. look-ahead (my own test) | for sessions 900, 1500, 2100, 2250, 2330, 2389 (2020 to 15 Oct 2026) I replaced every bar from that session onward by random numbers (open of the target session kept for the post-open model) and recomputed the whole pipeline | stored P_S6 and W_I6 quantiles for that session are unchanged to 1e-12 rupees, so they use nothing from the target session or later (apart from its open for the post-open model) |
| I. reproducibility | ran `--eval`, `--replicate`, `--selftest`, `--date 2026-10-16 --save` in an isolated copy | all 14 `hl_eval_*.csv`, the replication, the selftest csv and the JSON are byte-identical to the repo files; `--eval` takes 22 s |
| J. text vs files | parsed every cell of the report's Final-window tables (4.1, 4.2) and the DM tables (4.1, 4.2, 4.4) and compared them with the CSVs | 20 + 22 + 48 + 54 + 18 cells, 0 mismatches |
| K. other tables | cas_facts, gap_bins, reliability, byyear, twodays, dow screen, Yahoo vs NSE (15-minute and hourly), touch-probability Holm | all reproduce (details in Section 2) |

## 2. Headline numbers recomputed (mine vs builder)

| claim | builder | mine | difference |
|---|---|---|---|
| Final sessions, 1 Jul 2025 to 15 Oct 2026 | n = 320 | 320 | 0 |
| Pooled Val+Final / Val / Dev / CAS n | 568 / 248 / 1,072 / 52 | 568 / 248 / 1,072 / 52 | 0 |
| P_S6 high, Final: pinball x1e4 | 31.15 | 31.1516 | 3.6e-15 |
| P_S6 high, Final: 90% / 50% coverage | 90.3% / 46.9% | 90.3125% / 46.875% | 0 |
| P_S6 low, Final: 90% / 50% coverage | 88.8% / 50.3% | 88.75% / 50.3125% | 0 |
| P_S6 high, Final: Kupiec p (90%) | 0.851 | 0.8515 | 0 |
| P_S6 low, Final: Kupiec p (90%) | 0.464 | 0.4640 | 0 |
| Typical miss of median, pre-open high / low (Rs at 3,428), mean (s.e.) | 42.7 (2.2) / 47.7 (2.9) | 42.688 (2.25) / 47.673 (2.91) | 0 |
| Half the time within, pre-open high / low | 33.6 / 32.2 | 33.575 / 32.209 | 0 |
| Post-open (W_I6) miss, high / low | 34.8 / 37.4 | 34.805 / 37.416 | 0 |
| Post-open half the time, high / low | 29.1 / 26.6 | 29.146 / 26.642 | 0 |
| 'Price stays' miss high / low | 62.9 / 61.3 | 62.87 / 61.30 | 0 |
| 'Open stays' miss high / low | 51.3 / 59.0 | 51.25 / 58.96 | 0 |
| Open known vs not, pinball gain Final (high / low) | 23.4% / 23.4% | same (DM table identical) | 0 |
| Same, pooled Val+Final; CAS | 19.8 / 24.8; 28.4 / 24.0 | same | 0 |
| Project's stored-sigma replication (n=317): 90% coverage high / low; pinball | 90.2% / 88.6%; 31.240 / 36.767 | 90.22% / 88.64%; 31.240 / 36.767 | 0 |
| With 13-15 Oct added, my own sigma (n=320) | 90.3% / 88.8% | 90.31% / 88.75% | 0 |
| CAS (n=52): 90% coverage high / low; 50% coverage | 84.6 / 88.5; 40.4 / 40.4 | 84.62 / 88.46; 40.38 / 40.38 | 0 |
| CAS: pre-open high below its q5 | 15.4% (8 of 52) | 15.38% (8 of 52) | 0 |
| Open is the day's high / low, Val+Final n=568 | 4.2% / 2.1% | 4.23% / 2.11% | 0 |
| 16 Oct: HIGH median; 50%; 90% | 3,475; 3,449-3,513; 3,421-3,591 | 3,475.01; 3,449.38-3,512.63; 3,421.15-3,590.57 | <0.01 |
| 16 Oct: LOW median; 50%; 90% | 3,390; 3,352-3,419; 3,269-3,450 | 3,390.07; 3,351.83-3,418.79; 3,268.73-3,449.85 | <0.01 |
| 16 Oct flat open 3,428: HIGH / LOW median | 3,466 / 3,388 | 3,466.23 / 3,388.13 | <0.01 |
| 16 Oct touch probabilities +1% / +2%; -1% / -2% | 61/35; 52/27 | 60.8/34.8; 52.0/27.4 | 0 |
| 14 and 15 Oct retrospective (8 comparisons): all in 90%, six in 50% | as stated | same, medians equal within Rs 0.005 | 0 |
| Yahoo vs NSE, 15-minute n=39: mean high / low, p99 abs, max | -0.89 / +1.05; 4.8 / 4.4; 5.3 / 4.5 | -0.887 / +1.051; 4.81 / 4.39; 5.30 / 4.50 | 0 |
| Yahoo vs NSE, hourly n=333: mean high / low, max | -1.12 / +1.31; 46.4 / 54.7 | -1.118 / +1.309; 46.4 / 54.7 | 0 |
| Weekday screen (Dev+Val, n=1,318): Monday low | Holm 0.016; Lp/sigma -0.70 | Holm 0.0160; -0.6999 | 0 |
| Touch-probability Holm (Final, 16 tests): high +3% pre / post | 0.024 / 0.044 | 0.0242 / 0.0438 | 0 |
| Number of variant-target pairs; adopted | 34; none | 34; 0 | 0 |
| `src/eval_hl.py` now gives Final n=318, 89.9% / 88.4% (13 Oct has no stored sigma) | as stated | I ran it: n=318, 0.899 / 0.884, pinball nan | confirmed |

No trade rule exists in this specialist's work, so there is no trade-rule return to recompute.

Robustness checks I added (not in the builder's report):
* Using sigma from the parameters that a normal walk-forward block would have (10 sessions stale) instead of the fresh fit changes sigma from 2.4348% to 2.4360% and no 16 Oct quantile by more than Rs 0.2.
* Newey-West lag. The open-known gain stays at p < 0.001 at lags 0, 5, 10 and 20 (Final, both sides). The S6-versus-S0 and S6-versus-500-day gains for the high stay below p 0.007 in the pooled sample at lag 20. The S6-versus-250-day comparison does not: pooled raw p of the pinball difference for the high is 0.016 / 0.015 / 0.016 / 0.025 at lags 0 / 5 / 10 / 20, and the median-error comparison S6 vs EMP250 for the high is pooled raw p 0.007 / 0.019 / 0.030 / 0.050 and Final raw p 0.060 / 0.086 / 0.098 / 0.104.
* Block-bootstrap (blocks of 10 sessions) standard errors of the Final typical miss: pre-open high 2.8 (builder, assuming independence: 2.2), low 3.0 (2.9); post-open high 1.8 (1.8), low 2.3 (2.6). So the builder's "Rs 2 to 3" is fair; the pre-open high is slightly understated.

## 3. Line-by-line code review for look-ahead and arithmetic

Scope: `src/hl_model.py` (all 479 lines) read against `src/models.py`, `src/common.py`, `src/metrics.py`.

No look-ahead found. Timestamps of every input, relative to the forecast for session t:
* `load_ohlc(before)` keeps sessions strictly before the forecast date. `hl_forecast(date)` fits the S6 model through session n-1 only (`s6_next`: GARCH parameters fitted on `x[lo:n]`, the placeholder at index n is excluded by `t_b = n`; HAR rows used for fitting are `< n`, regressors for row n are built from `shift(1)` so use only `<= n-1`). Verified by my corruption test (H in Section 1).
* Walk-forward sigma for sessions < n uses `P.run_scale_models` (blocks of 20 sessions, parameters fitted on data before the block, filter state `h[t]` is the state before seeing `x[t]`). Standardised residuals for session t use `sig[s]` for s < t only (`fhs_draws`: `V[lo:t] / sig[lo:t]`), then times `sig[t]`.
* The gap z used by W_HARz / W_SIZE / W_SIGN / W_SZSG is |G_t| divided by the EWMA scale known at t-1; G_t is known at 09:08 on day t (official open). It enters the HAR as an unshifted regressor on purpose (dated t); all other regressors are shifted. Correct and consistent with the report's table of timestamps.
* The 20-session refit means the live forecast (parameters refitted exactly at session n) is one step fresher than what was evaluated. Immaterial (Section 2).
* Same-row leak test (`--selftest`) is correctly designed but tests only one session (19 Aug 2026). My broader test (corrupt everything from t on, six sessions across all windows) agrees.
* Bonus adjustment: only `prev` is adjusted on the ex-date; open, high, low, close levels are raw traded prices (close 4,809.50 on 14 Oct 2024; `prev` / close ratio exactly 3.000 on 2022-03-21 and 2025-05-23). The builder is right and the task brief ("prices are bonus-adjusted in the processed history") is wrong for price levels. All log targets are correct; rupees computed from levels before 23 May 2025 are on a 3x different scale. The builder handles this correctly (log miss times Rs 3,428; "traded rupees" only for Final and CAS). The lead should warn other specialists if they use raw levels.
* Log versus simple returns: rupee levels are `reference x exp(q)` (exact). The typical miss is `P x mean|log error|`; the exact rupee miss differs by about +1.4% for highs and -1.2% for lows (about Rs 0.6). Negligible.
* Translation argument for family 3 (pre-open P_S6 loss on ln(H/P0) versus post-open W_I6 loss on ln(H/O)): `pinball(Hp, q) = pinball(HO, q - G)` for the same quantile levels, so the losses are comparable. Correct.
* DM sign convention, one-sided and two-sided p, HLN factor sqrt((n-1)/n) and Holm are correct (my independent versions agree to 1e-15).
* Selection leak (minor, moot): the weekday screen uses Development + Validation sessions, and its variant P_DOW is then evaluated in Validation too. P_DOW showed no gain, so this does not matter.
* Fallback count: the report says "the count of fallbacks is reported" for the gap-pool variants (fewer than 30 draws in the day's bin falls back to the unsplit pool); it is not in the report, only printed by `--eval`. By the builder's rule it is 23 of 1,640 sessions for W_SIZE and 36 for W_SZSG (0 for W_SIGN), all in the large-gap bins, so those variants are identical to the baseline on most large-gap days and cannot test the large-gap case.
* Timestamp of "pre-fixed before any result": cannot be verified. The scratchpad shows `prefixed.md` last written 16:44 UTC, after `xcheck.py` (16:40, computes the baseline Final H/L coverage) and `tables.py` (16:41, prints the result CSVs); and the hashes the report quotes (`e757b838...`, `e46eaf28...`) do not match any SHA-256 I can compute from the saved `prefixed.md` (whole file: `49e3fcf4...`). Section 0 of the final report is identical to `prefixed.md`, so the text was not changed afterwards, and Amendment A1 only touched variants that turned out to be nulls, so no conclusion depends on this. But "written before any H/L model result was computed" should not be repeated as an audited fact.

## 4. Sentences checked against the files ("validated", "beats", "significant", coverage and accuracy numbers)

Sentences that are correct as written (numbers reproduce, wording matches the strength of the evidence): the pre-open and post-open Final tables; "no variant meets the adoption rule"; "S4, range model and Garman-Klass are ties"; "knowing the open helps, Holm < 0.001" (robust to lag, Section 2); "W_PRE is much worse"; "the low is a tie with every unscaled benchmark"; the CAS facts; the replication; the 14/15 Oct table with "no skill claim"; the Yahoo table; the section 7 reachability shares (low <= q25 on 27%, high >= q50 on 47%, etc.: I confirmed them from the reliability file).

Sentences that overclaim, or leave out a selection or sample-size problem:

1. Section 1: "The 90% bands ... cannot be narrowed honestly from daily data." Only the variants tried were shown not to narrow them (S1, S4, range, Garman-Klass, weekday, gap variants). Reword: "none of the variants tried narrowed them without losing coverage".
2. Section 4.2 / headline: "Gap size and gap direction add nothing beyond the open's level." It is a null with almost no power for large gaps: only 19 of 568 Val+Final sessions had a gap of 1 sigma or more (12 up, 7 down; 1 each in the auction slice), and the large-gap pools fell back to the unsplit pool on 23 to 36 days. The descriptive table even shows non-flat gaps with a median high about 0.6 percentage point farther above the open (1.70 to 1.75% vs 1.14%). Reword: "no detectable gain from gap size or direction in 568 sessions; large gaps cannot be assessed".
3. Section 4.5 / 4.6: "High (pre-open) runs a little high ... median about Rs 4 too high and its top tail too long (binomial p 0.039)". Not established: 53.4% of Final highs below the median is z 1.23, p 0.24; the upper-tail share (2.5%, 8 of 320, p 0.039) is one of 8 tail tests in Final (2 targets x 2 tails x 2 models), Bonferroni 0.31. The statement "pre-open high band runs slightly high" in the lead's brief should be softened to "no significant bias found; point estimates lean high".
4. Section 4.6 / numbers to quote: "pre-open high fell below its own 5% quantile on 15.4% of days (8 of 52, binomial p 0.004)". The p-value is uncorrected: it is the most extreme of 4 tail checks of the pre-open model in this slice (8 including the post-open model); Bonferroni 0.016 (4) or 0.033 (8); the slice is one drawdown episode (mean daily return -0.12%), not pre-fixed. Related and slightly stronger as a plain fact: the day's high stayed below the previous close on 9 of 52 auction-era sessions (17.3%) against 8.2% implied by tonight's model and 9.1% in Final (binomial p 0.024 one-sided, still one of several looks).
5. Section 4.1: "against the 250-day empirical quantiles [the model] is better for the high in Final (Holm 0.013) but not pooled (Holm 0.191)". Both numbers are right, but the pre-fixed primary test is the pooled one, where it is a tie; the Final-only Holm is a secondary window. Do not quote "beats the 250-day history" for the high.
6. Section 4.3: "S6 median vs EMP250 median: high +3.4% pooled, p 0.019, Holm 0.039". The Holm is over a family of 2 (high, low) that was added after seeing results, with no correction for the other ~200 tests in the study, and it does not survive a longer HAC lag (raw p 0.030 at lag 10, 0.050 at lag 20; Final p 0.086 to 0.104). The builder says "borderline"; it should say "not established".
7. Section 4.2 table, column "HO: 90% cov": the builder flags it. But the command-line output and the section 7 table still call the after-open band "nine times in ten". Corrected in Section 7 below.
8. Section 4.9: "'up to about Rs 4' holds at the 99th percentile". On 39 sessions the 99th percentile is essentially the maximum (Rs 4.8 / 4.4; maxima 5.3 / 4.5), so one session in 39 exceeded Rs 5; in the hourly feed 15 (high) and 20 (low) of 333 sessions exceeded Rs 5, and 6 and 5 exceeded Rs 10. The typical session is much closer (90th percentile Rs 2.6 to 2.7 for 15-minute bars, 2.3 to 3.1 hourly; median Rs 0.2 to 0.7).
9. Selection that is not stated: S6 was chosen by the project from S0 to S6 using the Validation + Final gate (v2 report 3.2, pre-registered gate), so comparing S6 against S0 / S1 / 250-day / 500-day history in Val+Final and Final favours S6 a little; the 'Final' window is not untouched for S6. It does not change the S6-versus-S4/range/GK ties.
10. The "Final = out of sample" label is fine for quantile construction (my corruption test), but Final was also used to choose the project's baseline model, so "validated" is too strong a word anywhere. The report mostly avoids it; the lead's brief should say "out-of-sample tested".
11. Section 4.8 gap-bin medians for the 12 and 7 session bins are shown with medians (2.35%, 4.41%); the report says "nothing can be said", which is right; the lead must not quote them.

Contradictions with earlier project statements: the builder lists them. I confirm: (a) Final 90% H/L coverage 90.2% / 88.6% (n=317) reproduces exactly (this is `FORECAST_REPORT_V2.md` section 3.2); (b) the V2 line "vs a trailing-250-day benchmark the Final gain is weak (p 0.084)" is for the close and is not contradicted for the high or low; (c) "50% intervals ran narrow" is consistent with 46.9% (high) and about 40% in the auction slice; (d) DEVIATIONS #30 (buying the predicted low / selling the predicted high lost money) is not contradicted: no rule was tested here. One more, not stated by the builder: the task brief's "bonus-adjusted in the processed history" is false for open/high/low/close levels (Section 3).

## 5. Tonight's forecast against plain history

Computed from the same raw data, 16 Oct 2026, reference Rs 3,428.0:

| | 5% | 25% | median | 75% | 95% |
|---|---|---|---|---|---|
| HIGH, model (S6 bootstrap) | 3,421 | 3,449 | 3,475 | 3,513 | 3,591 |
| HIGH, plain last 250 sessions (no volatility model) | 3,418 | 3,450 | 3,479 | 3,519 | 3,592 |
| LOW, model | 3,269 | 3,352 | 3,390 | 3,419 | 3,450 |
| LOW, plain last 250 sessions | 3,278 | 3,352 | 3,390 | 3,417 | 3,457 |

Why: tonight's sigma (2.43%) is close to the 250-session average S6 sigma (2.60%), so the volatility model changes little. The user should be told that the numbers are "what the last year of this stock's highs and lows suggests", not an insight from a clever model; the out-of-sample evidence that the model beats plain history is weak for the high and absent for the low (Section 4, items 5 and 6).

## 6. Defects found

1. **Mislabelled band (CLI, report section 7 table)**: the after-open HIGH "nine times in ten between Rs q5 and Rs q95" is not a 90% band. In Final it covered 95.0% (Kupiec p 0.0011 against 90%) because the open is the high on about 4% of days and q5 is essentially the open (flat-open example: q5 Rs 3,428.95 against an open of 3,428.0). Corrected wording: "the high ends at or below Rs 3,569 on 19 days in 20; on about 1 day in 25 the open itself is the high".
2. **Rupee scale not stated in the CLI**: "Typical miss about Rs 43 ... measured out of sample on the last 320 sessions" is the percentage miss times today's price (Rs 3,428). The stock averaged Rs 3,012 in the Final window (range 2,040 to 4,403), so the rupees actually missed were smaller: pre-open Rs 37.5 (high) / 40.7 (low); post-open 30.7 / 32.2 (columns `mae_med_rs_traded` in the CSVs). The report states the scaling; the CLI does not.
3. **50% band reliability not carried into the CLI**: Final 46.9% / 50.3% pre-open, but 40.4% / 40.4% pre-open and 38.5% / 40.4% post-open in the 52 auction-era sessions (Kupiec/binomial p about 0.2 each; four correlated looks, suggestive). The CLI prints "Half the time between ..." with no warning (it warns only about the high's lower tail).
4. **Input checks (CLI)**: `--open -5` prints "official open Rs -5.0, gap +nan%" and a full table of "Rs -5"; `--p0 0` prints a table of "Rs 0"; `--open 0` fails with a divide-by-zero warning and a misleading "more than 20% from the previous close"; `--open 34280` and `--date notadate` end in a raw Python traceback (the message of the first is clear). It must be run from the repo root (relative paths): from another folder it raises `FileNotFoundError`.
5. **Stale or weekend dates**: handled by a WARNING line, but it is the second line and the first line still says "session of Fri 16 Oct 2026" with the older reference close. With the 15 Oct row removed it printed a forecast for 15 Oct (reference Rs 3,338.0) under the 16 Oct header. Weekend (`--date 2026-10-17`) and Monday (`--date 2026-10-19`) both warn and forecast the next session after the data. A date that has already happened (`--date 2026-10-15`) runs silently as a replay (fine), but the typical-miss figures and the auction-slice caution it prints come from files that include that day.
6. **After-open bands are valid only at 09:08 to 09:15**: nothing in the CLI says that once trading has started the high so far and low so far make them obsolete (that is specialist B's tool).
7. **`--open` must be the NSE pre-open auction price** (final at 09:08); the first 09:15 chart print differs from it by up to Rs 11.7 (INPUT_AUDIT). The CLI help does not say so.
8. **Fallback count missing from the report** (Section 3).
9. **Unverifiable pre-fixed claim and hashes** (Section 3).
10. **Wording overclaims** (Section 4, items 1 to 6, 8, 9).
11. **P_S0 and P_S1, Development window only**: my versions differ slightly in pinball (S0: high 0.33, low 0.16 in x1e-4 units; S1: 0.004, 0.013) because the project's wrapper pads sigma with NaN before session 500, so these two benchmarks have fewer residuals for the first 250 evaluation sessions (to about Feb 2021) than the others. No effect on Validation, Final, pooled or auction windows, on any p-value in the report, or on any adoption verdict.
12. **Report/CLI typical-miss sentence for stale replays**: see item 5.

Robustness to the failure cases listed in the brief: "no bars yet" and "API 429" do not apply, because `hl_model.py` makes no network calls and never reads intraday bars; the price is the last official close in the two CSVs, which someone must update (`src/official_bars.py`) after each close. With results CSVs missing, the CLI still prints the quantiles but silently drops the typical-miss sentences. After the close with the new bar appended, `--date <next day>` works. Weekend and holiday: warning, no crash.

## 7. What the lead may quote, must correct, or must not quote

### 7.1 May be quoted as they stand (reproduced; with the n beside them)
* 16 Oct pre-open, P0 Rs 3,428.0, sigma 2.43%: HIGH median Rs 3,475 (50%: 3,449 to 3,513; 90%: 3,421 to 3,591); LOW median Rs 3,390 (50%: 3,352 to 3,419; 90%: 3,269 to 3,450). Band widths 63 / 67 (50%) and 169 / 181 (90%). Label them "from the last 500 sessions' history scaled to today's volatility". Add Section 5's plain-history comparison.
* Typical miss of the median, Final n=320, at today's price: pre-open high 42.7, low 47.7; half the time 33.6 / 32.2; post-open high 34.8, low 37.4; half the time 29.1 / 26.6; 'price stays' 62.9 / 61.3; 'open stays' 51.3 / 59.0; standard errors about Rs 2 to 3 (block-bootstrap: 2.8 / 3.0 / 1.8 / 2.3). Use together with correction 2 below.
* Post-open flat-open example (open Rs 3,428): HIGH median 3,466 (50%: 3,446 to 3,504), LOW median 3,388 (50%: 3,352 to 3,408); median high about open +1.12%, median low about open -1.16%; 50% widths 58 / 56.
* Open known versus not (pinball): 23.4% / 23.4% better in Final (n=320, Holm < 0.0001), 19.8% / 24.8% pooled Val+Final (n=568); in the 52 auction-era sessions 28.4% / 24.0% with the unadjusted p 0.014 / 0.013, labelled descriptive. Typical miss falls by about Rs 8 (high) and Rs 10 (low).
* Coverage, Final n=320: pre-open 90% band 90.3% (high) and 88.8% (low); 50% band 46.9% / 50.3%. The project's 90.2% / 88.6% (n=317) reproduces exactly.
* Auction slice facts (n=52; n=51 from 4 Aug changes nothing): open equals previous close on 9 sessions (17.3%) against 6.4% in the 250 sessions before; mean daily return -0.12%; 50% bands covered 40.4% (pre-open, both sides), 90% bands 84.6% / 88.5%.
* The open is the day's high on 4.2% of sessions and the low on 2.1% (Val+Final n=568).
* No pre-open or post-open variant beat the baseline under the pre-fixed rule (34 pairs, none adopted); gap-conditioned variants tie with Holm p >= 0.48 (see correction 6).
* Yahoo versus NSE: Yahoo high lower by Rs 0.9 / 1.1 on average and low higher by Rs 1.1 / 1.3 (15-minute n=39: 0.89 / 1.05; hourly n=333: 1.12 / 1.31); typical gap (median) Rs 0.2 to 0.7; see correction 8.
* 14 Oct: realised high 3,408.3, low 3,320.0 against pre-open medians 3,423 / 3,337; 15 Oct: 3,445.0 / 3,315.2 against 3,382 / 3,302; n=2, no skill claim.

### 7.2 Must be corrected before quoting (corrected value given)
1. After-open HIGH band "nine times in ten" -> "19 days in 20 the high is at or below the upper edge (Final coverage 95.0%, n=320)"; the lower edge is about the open itself.
2. "Typical miss ... last 320 sessions" -> "at today's price Rs 43 / Rs 48 (pre-open high / low); in rupees actually missed over those sessions Rs 37.5 / Rs 40.7".
3. "Pre-open high fell below its 5% level on 15.4% of days, p 0.004" -> "8 of 52 auction-era days (15.4%) against 5% expected; suggestive: Bonferroni-corrected p 0.016 to 0.033, not pre-fixed, one drawdown episode". Optionally add: the day's high stayed below the previous close on 9 of 52 days (17.3%) against 8.2% from tonight's model.
4. "Model beats 250-day quantiles for the high (Holm 0.013)" -> "better in the Final window only; in the pooled Validation+Final test (the pre-fixed one) a tie (Holm 0.191); no gain for the low".
5. "Model median beats trailing-250 median (+3.4%, Holm 0.039)" -> "not established (post-hoc 2-test family; raw p 0.019, 0.030, 0.050 at HAC lags 5, 10, 20; Final p 0.086)".
6. "Gap size and direction add nothing" -> "no detectable gain from gap size or direction in 568 sessions (Holm p >= 0.48); too few large gaps (19) to say anything about them".
7. "Pre-open high band runs slightly high" -> "no significant bias (53.4% of Final highs below the median, p 0.24); upper-tail share 2.5% vs 5% expected, uncorrected p 0.039, Bonferroni 0.31".
8. "'Up to about Rs 4' holds at p99" -> "most sessions are within Rs 3 (90th percentile 2.3 to 3.1); worst 15-minute session Rs 5.3, and the hourly feed has 15 (high) and 20 (low) of 333 sessions off by more than Rs 5, a few by Rs 30 to 55".
9. "Written before any H/L result was computed (hashes ...)" -> drop the hashes; say "stated in the report, not independently timestamped".
10. "50% band: half the time" -> add "4 days in 10 to 5 in 10 (47% / 50% in the last 320 sessions, 40% in the last 52)".

### 7.3 Must not be quoted
* The after-open HO band as a "90%" band (Section 6, item 1).
* Holm 0.013 (Final-only, vs 250-day history) or Holm 0.039 (median comparison) as evidence that the volatility model improves the pin-point.
* The auction-slice p-values (0.004, 0.014, 0.013, etc.) as significance tests.
* Gap-bin medians for large gaps (n = 12 and 7) and any statement about large gaps.
* 14 and 15 Oct as evidence of skill or its absence (n=2).
* The touch probabilities as an edge: they beat a plain trailing frequency clearly only for the high reaching +3% (Holm 0.024, one of 16 tests); at +1% and +2% they are ties (Holm 0.57, 0.59), and the model over-predicts the high touching +1% by 4.5 points in Final (64.1% vs 59.7%). If quoted (61% / 35%, 52% / 27%), say "model estimates, within about 4 points of what happened in the last 320 sessions".
* P_S0 / P_S1 Development-window rows (Section 6, item 11).
* The word "validated" for any of this work.

## 8. Commands to reproduce every verification number

Scratch directory `S=/tmp/claude-0/-home-user-pred-18/01384b6e-cd11-5bbc-b7f5-2dd03125e5eb/scratchpad`; run from `$S/verA`:
```
cd $S/verA
python3 build_sig.py      # my S6 sigma paths for R and I; compares with results/forecasts_R.csv and forecasts_I.csv (8.2e-15, 9.1e-15); next sigma 2.4348% / 2.2159%
python3 evalA.py          # my P_S6 and W_I6 walk-forward quantiles and window metrics (my_summary.csv)
python3 cmp1.py           # vs hl_eval_predictions.csv (1.8e-12 Rs) and hl_eval_preopen/postopen.csv (1.4e-14)
python3 evalB.py          # all variants, all six DM/Holm families vs hl_eval_dm_holm.csv (208 rows, max diff 7e-15); weekday screen
python3 allvar.py         # 266 variant-window rows vs CSV; PRICE_STAYS / OPEN_STAYS; plain trailing-250/500 medians; median-bias check
python3 live.py           # 16 Oct quantiles, widths, touch probabilities, flat-open table, open-is-high share
python3 other.py          # stored-sigma replication (90.22% / 88.64%, n=317), Final to 15 Oct, CAS facts, gap bins
python3 two.py            # 14 and 15 Oct retrospective forecasts
python3 rel.py            # reliability table and by-year pinball
python3 yv.py             # Yahoo vs NSE, 15-minute and hourly
python3 leak.py           # corrupt every bar from t on, 6 sessions, recompute forecast for t (max diff 9e-13 Rs)
```
Builder commands re-run in an isolated copy (`$S/repocopy`: `src/`, `data/processed/`, the two stored forecast files) so the repo was not touched:
```
cd $S/repocopy
python3 src/hl_model.py --eval --hourly $S/h60_BSE.NS.json    # 22 s; all 14 hl_eval_*.csv byte-identical to the repo
python3 src/hl_model.py --replicate                           # 90.22% / 88.64%, pinball 31.24011 / 36.76734, n=317
python3 src/hl_model.py --selftest                            # PASSED, byte-identical csv
python3 src/hl_model.py --date 2026-10-16 --save              # JSON byte-identical
```
CLI cases run from the repo root without `--save`: `python3 src/hl_model.py --date 2026-10-16 [--open 3342.0]`, `--date 2026-10-17`, `--date 2026-10-19`, `--date 2026-10-15`, `--date 2026-10-16 --open 34280 | 0 | -5`, `--p0 0`, `--date notadate`, `--date 2026-12-25`, `--open 3500 --p0 3400`; stale and missing-file cases in the copy (extra file truncated to 14 Oct, extra file removed, `hl_eval_preopen/postopen.csv` removed). Project script check: `python3 src/eval_hl.py` (prints Final n=318, nan pinball).
