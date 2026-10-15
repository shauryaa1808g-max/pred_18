# Independent verification of workstream "intraday" (`research/v2/05_intraday_structure.md`)

Verifier: independent re-implementation from raw/processed data. Information cutoff 2026-10-13 22:00 IST.
Verifier scripts (not imported from, not copied from the analyst): `/tmp/claude-0/-home-user-pred-18/01384b6e-cd11-5bbc-b7f5-2dd03125e5eb/scratchpad/v/*.py`. The analyst's `src/behaviour/intraday.py` was read only AFTER my numbers existed, to diagnose differences and check leakage. No git command was run; no analyst file was edited.

## 0. Cutoff exposure statement (this verification)

* Data read: `data/processed/bse_daily.csv` (filtered `date <= 2026-10-13`; file ends 2026-10-13), `data/processed/xlsx_15m_clean.csv`, `data/raw/tradingview/BSE_intraday_30d_1.xlsx`, `data/raw/intraday/*.csv` (epoch timestamps converted to IST and filtered `<= 2026-10-13`; latest bar 2026-10-13 15:15 IST), `data/processed/intraday_validation.csv` (not used), the analyst's report, JSON and code, `results/intraday_profile.json` (v1).
* NOT opened: `data/raw/udiff/20261014.zip`, `results/forecast_score_2026-10-14*.json`, `results/forecast_record_2026-10-14_v2.json`, any 14/15 Oct market data or news. No network, no fetch scripts, `data/raw/macro` untouched.
* Incidental exposure, file-metadata only: a directory listing of `data/raw/udiff` showed the NAME `20261014.zip` (existence), and `ls -l` showed that the analyst's outputs carry mtimes of 14 Oct 07:33-07:55 (sandbox clock, UTC) - i.e. inside the 14-Oct session hours. This reveals no price, volume or headline. It did not influence any verdict. Content evidence on the analyst side: the script contains no network/subprocess/clock calls (grep for http, requests, urllib, subprocess, datetime.now, 1014, forecast_score, forecast_record found nothing), asserts input dates `<= 2026-10-13`, and the union CSV ends 2026-10-13. I found no content leakage; I cannot rule out from the files alone what the analyst saw on the clock, which is why the mtimes are mentioned.

## 1. Re-implementation results (reported vs mine)

Union dataset rebuilt from scratch (workbook preferred, earlier fetch for other sessions, validator rules: close +-0.02%, high/low +-0.25%, volume ratio 0.80-1.02, >=24 bars, row OHLC +-0.06, bar-open continuity 0.4%): **37 sessions, 917 bars; failing sessions 17 Aug, 2 Sep, 10 Sep** - identical to the analyst.

| # | Claim | Reported | Mine | Verdict |
|---|---|---|---|---|
| 1 | last-bar close = official close | 37/37; 15:15 bar in 29 | 37/37; 29; 15:00 close = official close in 8/8 without a 15:15 bar vs 1/29 with (Fisher p 2.3e-7) | confirmed |
| 2 | 30-min / 1-hour sheets add nothing; 1h volume defective | OHLC mismatches 0/255, 0/135; 16 volume mismatches | 0/255, 0/135 (rebuilt from the workbook's own 15m sheet); 16 volume mismatches, all 09:15; zero-volume 22 hourly bars (16 at 09:15, 6 at 15:15) | confirmed |
| 3 | volume shares | open hr 26.5 (23.4-29.8), midday 35.7, 15:00 pure 9.0, 15:15 0.86, closing window 11.3 | 26.51 (23.41-29.79), 35.71, 9.00 (n=29), 0.857, 11.35 | confirmed |
| 4 | variance share open hr; abs returns | 46.7 (38.6-54.7); 0.471 / 0.202 / first bar 0.83 | 46.3 (38.2-54.4); 0.471 / 0.202 / 0.828 | confirmed (0.4 pp gap = definition of the closing-window block, see 2.4) |
| 5 | high/low in first hour; MC benchmark | 22 / 12 / either 31; benchmark 45.6 / 45.7 / 84.9; p 0.100 / 0.137 / 0.82 | 22 / 12 / 31; benchmark 45.7 / 45.2 / 84.5; p 0.101 / 0.138 / 0.82; leave-one-out clock: expected 16.8 / 16.8 / 31.3 vs observed 22 / 12 / 31 | confirmed |
| 5b | last hour | high 4, low 9; benchmark 21.3 / 21.5 | 4, 9; benchmark 22.3 / 22.2; p 0.113 / 0.696 | confirmed in substance (benchmark +1 pp, still not significant) |
| 6 | range formed by 10:15 / 11:15 | mean 0.709, median 0.772 / 0.760; MC 0.672 / 0.751 | 0.7095, 0.7723 / 0.7598; MC 0.670 / 0.748 | confirmed |
| 7 | FH vs Rest | r -0.0636 (p 0.709); sign 19/36 (p 0.868); WF 37.0% vs 40.7% (n=27) | -0.0636 (0.709); 19/36 (0.868); WF 37.0% vs 40.7% (27); critical r 0.3246 | confirmed |
| 8 | S02 gap WF | 48.1% vs 44.4% | 48.1% vs 44.4% | confirmed |
| 9 | C04 small gap (|G|<0.46%) | n=15, +1.43%, p 0.0042, 13/15 | n=15, +1.428%, p 0.0042, 13/15 (with the 0.46% cut) | numbers confirmed; see 2.3 |
| 10 | VWAP | 16/37 p 0.51; Spearman -0.034 / +0.105 | 16/37 p 0.511; -0.0341 (0.841) / +0.1046 (0.538) | confirmed |
| 11 | gap fill L01 | 18/34 vs 25.1 expected; long history 75.3% vs 75.7% | 18/34 vs 25.10; 2,207 history sessions 75.4% vs 75.7%; 2024+ 71.2% vs 78.7% | confirmed (my Poisson-binomial two-sided p 0.003; the analyst's 0.0047 = doubled one-sided tail 2x0.00234) |
| 12 | 14-Oct touch frequencies | high 71.1% (n=584) vs 72.9%; low 23.5% (n=234) vs 29.2%; split 71.6/70.4 and 23.9/23.1 | 71.1% (584) vs 72.9%; 23.5% (234) vs 29.2%; 71.6/70.4; 23.9/23.1; sigma_R20 = 2.3426%, x = 0.350 / 1.091; P(close < 3290.2-type level) 15.0% vs RW 13.8% | confirmed |
| 13 | R01 | 827 touches, 44.1%, first 60% 38.9%, last 40% 51.8% (split 2022-11-30) | 827, 44.14%, 38.95% (n=493), 51.80% (n=334) | numbers confirmed |
| 14 | R02 | 1,012 touches, 58.4%, first 60% 55.8%, last 40% 62.6% | 1,012, 58.40%, 55.82% (n=627), 62.60% (n=385) | numbers confirmed; status NOT warranted, see 2.1 |
| 15 | auction move | mean abs 0.131% (0.088-0.180), p90 0.31, max 0.46, 6/29 zero; signed +0.070% p 0.037; corr -0.22 p 0.25; 14:45->close 0.296% | 0.1312% (0.087-0.181), 0.312, 0.459, 6; +0.0698% p 0.0374; -0.2197 (0.252); 0.296% | confirmed |
| 16 | 15:15 volume is not auction volume | 10/29 zero-volume bars, only at 15:15 | 10/29; zero-volume bars in other slots: 0; bar volume / NSE volume mean 0.942 (0.827-0.9999) | confirmed |
| 17 | 13 Oct anatomy | 14:15 bar 1,076,912 = 8.9x slot median, 27.2% of day; every earlier bar <=1.4x; 46.3% of volume by 14:15 | 1,076,912; 8.93x; 27.2%; max earlier multiple 1.42x; 46.28% | confirmed |
| 18 | 29 Sep | 22,504,261 = 74.8% of NSE volume, 75.9% of bars | 22,504,261; 74.76%; 75.92% | confirmed |
| 19 | v1 defects | v1 "15:15" mean abs move 0.1965%, vol share 4.395% mix 15:15 and 15:00 bars | recomputing "last row" over v1's 36 sessions: 0.1965% and 4.394% | confirmed |
| 20 | pitfalls | first-bar open vs official open 0.115%, equal in 3/37; 8 sessions without 15:15 | 0.1151%, 3; same 8 dates | confirmed |

Test-registry arithmetic (Holm/BH) reproduces from the stored raw p-values (R01 0.00083x24 = 0.020; C04 0.00419x23 = 0.096; L01 0.00468x22 = 0.103). The report matches `results/behaviour/intraday.json` on every number I cross-checked (windows, timing, continuation, gap, R01/R02 incl. drift-adjusted block, registry). I found no report-vs-JSON discrepancy.

## 2. Findings that matter

### 2.1 R02 "validated_out_of_sample" is not warranted (main finding)

What was done: direction fixed on the first 60% (share > 0.5), evaluated on the last 40% against 0.5 and against a model-based drift-adjusted benchmark. Why that is not a validation of a level effect:

1. **The training sample showed no level-specific excess.** The analyst's own JSON (`rejection_vs_breakthrough_long_history.R02.drift_adjusted_benchmark.first60pct`) has observed 54.8% vs expected 56.6% - BELOW the drift benchmark. The only thing the first 60% "established" is share > 0.5, which is the generic negative open-to-close drift of 2017-2022 (P(close < open) = 64.2%, mean open-to-close -0.24%/day in the first 60%; 51.4% and +0.02% in the last 40%).
2. **Level-agnostic placebo (mine).** For each session I replaced the prior-day-low distance by a distance drawn from another session of the same calendar year (also a sigma-scaled variant), 300 repetitions, and applied the identical rule (open above level, low touches it, close below it). Results for R02-analog: all 56.5% (real 59.0% in my definition, 58.4% analyst), **first 60%: placebo 57.5% vs real 56.6%** (excess -0.7 pp, block-bootstrap 95% CI -3.9 to +2.5), **last 40%: placebo 54.7% (sigma-scaled 55.4%) vs real 62.9%** (excess +8.6 pp, CI +5.0 to +12.3). So the level-specific excess is absent in training and appears only from 2023 (by-year excess: 2018 -4.9, 2019 -4.9, 2020 +5.6, 2021 +2.0, 2022 +0.7, 2023 +11.8, 2024 +9.9, 2025 +6.5, 2026 +5.6 pp). The difference between periods is +9.1 pp (CI +4.1 to +13.8). That is a late-emerging, post-hoc pattern, not a validated one. The analyst's 50.9% drift-adjusted benchmark for the last 40% is a constant-volatility Brownian-motion-with-drift model that under-predicts the empirical level-agnostic rate (about 55%) by ~4 pp in a period of ~zero drift, so "exceeds the drift-adjusted benchmark" overstates.
3. **Walk-forward log-loss (mine, expanding by year 2020-2026, and the analyst's 60/40 split).** Predicting "break rate = past real R02 rate" beats the naive 0.5 (0.672 vs 0.693), but does NOT beat the level-agnostic placebo rate (0.6719 vs 0.6726 pooled 2020-26; 0.6653 vs 0.6674 for 2023-26; on the analyst's split 0.6676 vs 0.6659, placebo slightly better). No forecasting skill specific to the prior-day low was demonstrable from information available at each point.
4. **Same pattern for R01:** placebo-adjusted excess is +0.15 pp (first 60%), +0.65 pp (last 40%). The "resistance at prior highs, 38.9% in 2017-2022" is entirely the generic drift/skew of the period, not a level effect. The report calls it "present in 2017-2022"; as a level effect it was never present.
5. The registered R01/R02 p-values (1e-7) test against 0.5; the claim "last-40% p stays below 0.05 even with Holm factor 26" is arithmetically right (8.8e-7x26) but against the wrong null. R01/R02 were added after the first output (change log), so they are post-hoc hypotheses; the module docstring header still says every test was pre-registered before any statistic was computed (internally inconsistent; the report's process record is the honest version).
6. Effective n: 48% of touch events are on a day whose previous session was also an event; lag-1 autocorrelation of the outcome indicator is 0.003; block-20 bootstrap CI for the last-40% raw rate is 58.2-67.5%, so serial dependence is not what drives the problem.

Recommended status: `descriptive_only` (observation: after a touch of the prior-day low, close-below rate 62.9% in 2023-26 vs ~55% for level-agnostic levels; exploratory, post hoc, no usable training evidence). Effect on the 14-Oct forecast: none (the analyst already says the unconditional close-below-3,290.2 probability is unchanged; empirical 15.0% for sessions at that sigma-distance vs RW 13.8%).

### 2.2 Regime-flip / break claims (independent tests)

* **R01 flip (38.9% -> 51.8%)**: real. Two-proportion z = -3.65, p = 0.0003; sup-LR break scan over the middle 70%, permutation p < 0.002, estimated break at event 242 (2020-04-08), earlier than the 60/40 date. But it is a break in the **generic intraday drift** (P(close<open) 64.2% -> 51.4%, z = 6.2, p = 4e-10; mean open-to-close -0.238% -> +0.018%, Welch p = 0.016), and the placebo-level R01 shows the same 38.7% -> 51.1%. So the flip is a drift-regime change, not a change in how prior highs behave.
* **R02 first60 vs last40 (55.8% -> 62.6%)** raw: z = -2.12, p = 0.034, sup-LR permutation p = 0.16 (not a clean break on the raw rate); placebo-adjusted the change is strong (see 2.1).
* **corr(G, I) sign change** (-0.078 for 2017 to 2024-06, n=1,729, p=0.001; +0.017 after, n=498): Fisher difference z = -1.94, p = 0.053. Marginal; the analyst's wording "unstable across periods" is fair.
* **C04 small-gap continuation (window +1.43%) vs history**: Welch t of window small-gap vs all history (same 0.46% cut) = 3.42, p = 0.004; vs 2024+ = 4.02, p = 0.0008. Rolling 34-gap-session windows in 2017 to 17 Aug 2026 (2,061 overlapping, 61 non-overlapping): **none** has a small-gap t as large as the window's 3.41 (max non-overlapping 3.21; fraction with |t| >= 3.41 is 0.9%). So the window is a statistically unusual stretch, not an ordinary streak, though the closes differ in definition before 3 Aug (30-minute VWAP), and BH q = 0.029 / Holm 0.096 within the family.
* **L01 gap-fill shortfall**: a 34-session shortfall of >= 7.1 touches vs expectation occurs in 1.6% of rolling historical windows (1/64 non-overlapping). Consistent with a recent drift of the benchmark (2024+: 71.2% vs 78.7%); unresolved.

### 2.3 Definition drift / selective reporting

* **Gap threshold.** The report says "G != 0 in 34 sessions ... median |G| 0.46%" and defines C03/C04 around that median. The code takes the median of |G| over all 37 sessions including three zeros (0.4619%) and then applies it to the 34 non-zero sessions. The median of the 34 non-zero is 0.549%; with that cut n_small = 17, mean +1.16%, p = 0.013. C04 is also sensitive to the cut (p < 0.02 for any cut 0.25-0.70%, p = 0.06 at 0.80%, p = 0.19 at 1.0%). The cut is not outcome-tuned (median rule fixed in advance), so this is a description issue, not tuning.
* **"Contradicted by the long history" (C04) is selectively supported.** The report cites -0.01% (all history), -0.37% (2024+) and -0.50% (May 2025+) but omits that the analyst's own JSON (`follow_up_F2_gap_continuation_long_history`) shows 2021-2023 small gaps with **+0.35% continuation, p = 0.010, n = 309**. The sign alternates by era (2017-20 -0.03, 2021-23 +0.35, 2024-26 -0.37), and the long-history quantity (30-minute-VWAP close) differs from the window's (auction close). "Not replicated / regime-dependent / descriptive_only" is supportable; `contradicted` is stronger than the evidence. No consequence for 14 Oct either way: G is not known at the cutoff.
* **Touch bins**: +-0.15 sigma (high) vs +-0.20 sigma (low) widths; bins centred on 14-Oct's distances after they were known. Immaterial (sigma=2.48% sensitivity stored).

### 2.4 Other design checks

* **Look-ahead.** No predictor uses same-day or future information beyond what is stated. FH (to 10:15) predicts Rest (after 10:15): legitimate. Walk-forward rules train on earlier sessions only; benchmark sign uses expanding past mean. Touch benchmarks use trailing-20 sigma shifted by one day. Drift-adjusted benchmark uses trailing-250 mean shifted by one day. The variance-clock benchmark is estimated on the same 37 sessions (mild circularity): leave-one-out clocks give expected counts 16.8 / 16.8 / 31.3, indistinguishable from the in-sample 16.9 / 16.9 / 31.4. The C04 median cut uses the whole window (future sessions) but not outcomes.
* **Outcome-dependent exclusion.** 10 Sep is dropped by a bar-continuity rule that removes a genuine +0.60% 15:00-close-to-auction jump, i.e. selection on the quantity being measured; disclosed with sensitivity (mean abs 15:00-close-to-close 0.134% -> 0.157% with the failed sessions). My replication also drops it under the same stated rule.
* **Closing-window variance block.** The analyst's 15:00 row uses the combined 15:00-15:30 return (squared), I used separate 15:00 and 15:15 squared returns; hence 46.7% vs 46.3% and closing window 4.6% vs 5.4%. Both are legitimate; the report states its convention.
* **Effective sample / overlap.** Sessions are non-overlapping; bar-level statistics correctly use n = 37 (29 for the 15:15 bar). Block-3 bootstrap alongside iid. Touch-frequency bins of 584 / 234 sessions contain ~422 / ~202 clusters of adjacent sessions; Wilson intervals are slightly narrow, conclusions unchanged.
* **Multiple testing.** Holm and BH are applied over 25 registered tests, correctly computed. Unregistered looks (sub-period splits, calibration-by-distance tables, sensitivity variants, F1/F2, spike rule, slot CI table) are descriptive and labelled so. The Holm result "only R01, R02 pass" is right, but both pass only against the 0.5 null (2.1). Power statements check out (critical |r| 0.3246 at n=37).
* **Power / negative results.** The report states correctly that effects of rho ~0.2-0.3 and a 60% hit rate cannot be detected at n=27-37; its `not_found` labels for timing, VWAP and first-hour continuation are the right labels and each reproduces.

## 3. Validation-status audit

| Claim | Stated | My assessment |
|---|---|---|
| Last-bar close = official close | verified_source | warranted (independent source: bhavcopy vs Yahoo, 37/37) |
| 30m/1h add nothing | verified_source | warranted (I rebuilt the sheets: 0 mismatches) |
| Volume / variance profiles | descriptive_only | warranted |
| First-hour extremes, range share, FH->Rest, VWAP | not_found | warranted; benchmark circularity immaterial (LOO) |
| C04 gap continuation | contradicted | too strong; use descriptive_only / not_replicated (2.3) |
| L01 gap fill | descriptive_only | warranted |
| R01 prior-high resistance | not_found | label fine; but the 2017-22 "resistance" was never level-specific (placebo) |
| **R02 prior-low break persistence** | **validated_out_of_sample** | **not warranted** (2.1); descriptive_only |
| Touch frequencies at 14-Oct distances | descriptive_only | warranted |
| Auction move | descriptive_only | warranted |
| 15:15 volume as auction volume | unverifiable | warranted |

## 4. Overall

Every numeric headline reproduces from raw data to the stated precision; report and stored JSON agree; no content-level look-ahead found. Two issues require correction before downstream use: (1) R02 must not carry `validated_out_of_sample` (training evidence of a level effect is nil; walk-forward does not beat a level-agnostic baseline; the late excess is exploratory), and R01's 2017-22 "resistance" must not be read as a level effect; (2) the C04 `contradicted` label rests on a selective summary of the long history and on a quantity defined differently before 3 Aug. Severity: **major** (for the single mis-labelled validation status and selective C04 summary); **no effect on the 14-Oct central forecast or interval**, as the analyst itself states.
