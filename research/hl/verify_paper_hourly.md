# Independent verification: hour-by-hour paper trade (rules R-A to R-E) for NSE:BSE

Verifier: independent re-computation from the raw CSVs only (no import from `src/` in the main re-computation). Date of check: Fri 16 Oct 2026, after the close. Branch `claude/dreamy-albattani-k94wba`. Nothing outside this file was edited, nothing committed. No data dated after 16 Oct 2026 was used.

## 1. Verdict

**pass_with_fixes. Severity: low.** The lead's numbers reproduce to the last digit and the conclusion (no rule passes the pre-fixed verdict rule) is correct and robust. Four statements must be corrected before quoting (section 6) and three must not be quoted. None of the corrections can turn any rule into a pass.

Key numbers (original 39 sessions, 195 windows; mean net return per filled trade, 0.10% round-trip cost):

| rule | windows | filled trades | mean net % | t (lead, session means) | first half % | second half % | passes verdict rule? |
|---|---|---|---|---|---|---|---|
| R-A limit buy at L* | 195 | 93 | -0.131 | -1.47 | -0.176 | -0.098 | no |
| R-B limit short at H* | 195 | 104 | -0.118 | -2.07 | -0.159 | -0.090 | no |
| R-C long, target H*, stop L* | 195 | 195 | -0.103 | -4.92 | -0.108 | -0.098 | no |
| R-D short, target L*, stop H* | 195 | 195 | -0.109 | -5.39 | -0.091 | -0.125 | no |
| R-E buy at P, sell at window end | 195 | 195 | -0.104 | -2.29 | -0.121 | -0.087 | no |

Every rule fails the first criterion (mean net above zero), so the verdict does not depend on the placebo, on the t-statistic definition, or on any of the sensitivity variants below.

## 2. What I checked and how (and what I found)

| # | check | method | result |
|---|---|---|---|
| 1 | Pre-registration timing | `git log`: rules commit 23a7f4c author date 2026-10-16 08:49:07 UTC = 14:19:07 IST; backtest commit 2c55677 at 14:21:07 IST; first live order logged 14:22:27 IST (`logged_utc` 08:52:27 UTC) | Consistent with "14:19 IST". Caveat: git dates are self-declared; the rules were fixed two minutes before the backtest was committed, on the same 39 sessions on which the pin-point method had been built and examined (`--eval`), and the lead says a placebo bug was fixed after a first run (the buggy version was never committed, so it cannot be audited; the committed code is correct, see 5). |
| 2 | Leave-one-session-out (LOO), line by line | `paper_hourly.backtest`: for session i it builds `others` (j != i), computes the variance profile `LN.profile(others)` and the z-pool `HT.zpool(others, ev)` from them only; medians of the pooled standardised high and low excursions. | Correct. No use of session i in profile or z. |
| 3 | Look-ahead, by experiment | Corrupted (random multiplicative noise) every bar of session i at or after checkpoint k, in the lead's code and in mine; then also corrupted the whole of session i. | Pin-points of session i at k changed in 0 of 30 (lead code, 6 sessions x 5 checkpoints) and 0 of 195 (my code, all sessions). Whole-session corruption: the ratios H*/P and L*/P unchanged in 30 of 30. Power check: corrupting session 5 changes the pins of 190 of 195 windows (the other 38 sessions), as it should. |
| 4 | Window indexing | k completed bars -> k = 3, 7, 11, 15, 19 = 10:00 ... 14:00; P = `cf[k-1]` = close of bar k-1 (09:59, 10:59 ...); window bars k..k+3; exit = close of bar k+3 (15:00 at the latest). sigma = sqrt(sum of profile variance of bars k..k+3). | Correct. Last backtest window ends 15:00, so no backtest window touches the 15:15 to 15:30 closing-auction slot. |
| 5 | Prices ("bonus/raw") | Raw prices are used throughout; no overnight step. `data/processed/corp_actions.csv` has no entry after 2025-10-23; no NaN, no duplicate (date, time), no bar with high < low or close/open outside the range; largest bar-to-bar open/close gap 0.36%; price range 3046 to 3466. 8 sessions lack the 15:15 bar (2026-08-18, 08-24, 09-03, 09-17, 09-22, 09-29, 10-08, 10-09). | Clean. The 15:15 handling only touches z-pool windows with k >= 20, never the pins used (they use slots up to 22). |
| 6 | Signs, cost, stop-first, strict-through | Re-coded all five rules independently. | Match the pre-registered text. One convention issue (F4 below): shorts are measured as entry/exit - 1 instead of (entry - exit)/entry. |
| 7 | Full re-computation | `run1.py`: my own loader, LOO pins, trades. | Trade-level identical to the lead's `results/paper_hourly_trades.csv`: 975 of 975 rows (782 filled), NaN pattern identical, maximum absolute difference 1e-16. Running the lead's own code on the 39 sessions also reproduces `results/paper_hourly_backtest.csv` exactly, including the placebo (seed 11) and the verdict column. |
| 8 | Placebo | Own simulations, different seeds, four variants (section 5). | Construction correct; one artefact inflates the placebo cost drag for R-A and R-B (F5). |
| 9 | Live ledger | Recomputed the five outcomes of the 14:22 to 15:22 window from the 1-minute cache and the logged pin-points; also re-derived the logged pin-points. | Reproduced exactly, with two caveats on the exit price and on `settle()` (section 7). |

## 3. Reproduction of the lead's table (39 sessions) and the 40-session numbers

Same definitions as the lead: mean over filled trades; win = net > 0; t = mean of session means / (sd of session means / sqrt(sessions)); first half = first 19 dates, second half = last 20 dates (39 sessions) or 20/20 (40 sessions). "t_cr" = my additional trade-weighted cluster-robust t (tests the headline trade mean itself; CR1 small-sample factor).

**39 sessions (every date except 2026-10-16), 195 windows**

| rule | n windows | n trades | fill rate | mean net % | median net % | win rate | t (lead def.) | t_cr | half 1 % (n) | half 2 % (n) | mean gross % | lead's table |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| R-A | 195 | 93 | 0.477 | -0.131 | -0.100 | 0.344 | -1.47 | -2.06 | -0.176 (40) | -0.098 (53) | -0.031 | identical |
| R-B | 195 | 104 | 0.533 | -0.118 | -0.010 | 0.490 | -2.07 | -1.92 | -0.159 (42) | -0.090 (62) | -0.018 | identical |
| R-C | 195 | 195 | 1.000 | -0.103 | -0.023 | 0.497 | -4.92 | -4.92 | -0.108 (95) | -0.098 (100) | -0.003 | identical |
| R-D | 195 | 195 | 1.000 | -0.109 | -0.240 | 0.436 | -5.39 | -5.39 | -0.091 (95) | -0.125 (100) | -0.009 | identical |
| R-E | 195 | 195 | 1.000 | -0.104 | -0.143 | 0.374 | -2.29 | -2.29 | -0.121 (95) | -0.087 (100) | -0.004 | identical |

Exact differences from the lead's numbers: none in any reported column (differences below 0.0005 in every printed column). The only additions are the t_cr column and the gross column.

**40 sessions (16 Oct appended), 200 windows**

| rule | n windows | n trades | fill rate | mean net % | win rate | t (lead def.) | t_cr | half 1 % | half 2 % | pass? |
|---|---|---|---|---|---|---|---|---|---|---|
| R-A | 200 | 95 | 0.475 | -0.130 | 0.337 | -1.50 | -2.08 | -0.163 | -0.101 | no |
| R-B | 200 | 107 | 0.535 | -0.121 | 0.477 | -2.14 | -2.02 | -0.128 | -0.115 | no |
| R-C | 200 | 200 | 1.000 | -0.101 | 0.500 | -4.95 | -4.95 | -0.112 | -0.090 | no |
| R-D | 200 | 200 | 1.000 | -0.110 | 0.435 | -5.58 | -5.58 | -0.087 | -0.132 | no |
| R-E | 200 | 200 | 1.000 | -0.099 | 0.380 | -2.25 | -2.25 | -0.133 | -0.066 | no |

**Per checkpoint (39 sessions): filled trades / windows, mean net %.** No cell is a reliable positive: the largest are R-E at 14:00 (+0.092, n = 39) and R-A at 10:00 (+0.019, n = 17); with five rules x five checkpoints these are what chance gives.

| rule | 10:00 | 11:00 | 12:00 | 13:00 | 14:00 |
|---|---|---|---|---|---|
| R-A | 17/39 +0.019 | 22/39 -0.025 | 21/39 -0.227 | 20/39 -0.262 | 13/39 -0.153 |
| R-B | 27/39 -0.088 | 20/39 +0.025 | 22/39 +0.007 | 16/39 -0.109 | 19/39 -0.461 |
| R-C | 39/39 +0.003 | 39/39 -0.175 | 39/39 -0.110 | 39/39 -0.160 | 39/39 -0.070 |
| R-D | 39/39 -0.218 | 39/39 -0.055 | 39/39 -0.102 | 39/39 -0.039 | 39/39 -0.129 |
| R-E | 39/39 +0.001 | 39/39 -0.153 | 39/39 -0.200 | 39/39 -0.259 | 39/39 +0.092 |

(The 40-session per-checkpoint table is in the scratch output of `run3.py`; the pattern is the same.)

## 4. Sensitivity (39 sessions; all variants fail the first criterion)

| variant | R-A | R-B | R-C | R-D | R-E |
|---|---|---|---|---|---|
| baseline (lead conventions), mean net % | -0.131 | -0.118 | -0.103 | -0.109 | -0.104 |
| shorts as (entry - exit)/entry, mean net % | -0.131 | -0.121 | -0.103 | -0.109 (t -5.43) | -0.104 |
| target-first when stop and target share a bar (best case, mean net %) | -0.131 | -0.118 | -0.091 (t -4.50) | -0.096 (t -4.62) | -0.104 |
| entry at the open of bar k instead of P, mean net % | n/a | n/a | -0.101 | -0.112 | -0.102 |
| zero cost (gross), mean % | -0.031 | -0.018 | -0.003 | -0.009 | -0.004 |
| gross t (trade-weighted, clustered) | -0.49 | -0.29 | -0.13 | -0.42 | -0.08 |
| R-C minus R-E, same 195 windows | | | +0.001, t 0.02 | | |
| R-D minus R-E, same 195 windows | | | | -0.005, t -0.09 | |

Reading: before costs every rule earns zero within noise; after costs every rule earns about minus the cost. The stop-first convention costs R-C and R-D about 0.012 percentage points; even the best case is far from positive.

Power (what the verdict rule could have detected): the standard error of a rule's mean (trade-weighted, session-clustered) is about 0.064% (R-A), 0.062% (R-B), 0.021% (R-C), 0.020% (R-D), 0.045% (R-E). To pass (t above 2) a rule needed a gross edge of roughly +0.23%, +0.23%, +0.14%, +0.14% and +0.19% per hourly trade. Small edges, say 0.05% per trade, would not have been found. "Not found" is the right wording; "no edge exists" is not supported.

## 5. Placebo, independently re-run, and the verdict rule applied by me

Code check: the lead's construction (4 bars x 15 one-minute steps, `base` = cumulative level at the start of each bar, bar high/low from the bar's minute closes and the previous close) equals a plain cumulative sum of the 60 steps to 2e-16 over 2000 random windows, so the "bar continuity" fix is confirmed correct. Sampling of the lead's placebo with his seed reproduces the CSV exactly.

My simulations (all use the 39-session profile and z-medians, 5 checkpoints, same rules; "z" = (rule mean - placebo mean) / sqrt(se_rule^2 + se_placebo^2), the lead's formula; need z > 2):

| placebo | reps per checkpoint | seed | R-A mean % (fill) | R-B | R-C | R-D | R-E |
|---|---|---|---|---|---|---|---|
| lead's committed (1-min closes, Gaussian) | 400 | 11 | -0.159 (0.54) | -0.154 (0.57) | -0.102 | -0.100 | -0.099 |
| A. same design, my code | 400 | 2024 | -0.145 (0.55) | -0.150 (0.59) | -0.104 | -0.103 | -0.087 |
| B. same design, my code | 4000 | 7 | -0.151 (0.55) | -0.152 (0.58) | -0.109 | -0.096 | -0.102 |
| C. continuous monitoring (Brownian-bridge extremes inside each minute) | 4000 | 8 | -0.101 (0.60) | -0.102 (0.64) | -0.111 | -0.104 | -0.101 |
| D. continuous + Student-t(4) steps | 4000 | 9 | -0.118 (0.58) | -0.109 (0.62) | -0.105 | -0.108 | -0.098 |
| real data, for comparison (fill rate) | | | -0.131 (0.48) | -0.118 (0.53) | -0.103 | -0.109 | -0.104 |

Standard errors of the placebo means: 0.015 to 0.016 (A) and 0.005 (B, C, D) for R-A/R-B; 0.002 to 0.007 for R-C/R-D; 0.004 to 0.014 for R-E.

z versus placebo (39 sessions): lead's design A/B: R-A +0.23/+0.33, R-B +0.40/+0.43, R-C +0.06/+0.32, R-D -0.25/-0.63, R-E -0.36/-0.04. Continuous placebo C: R-A -0.52, R-B -0.19, R-C +0.40, R-D -0.24, R-E -0.07 (D: -0.24, -0.10, +0.12, -0.02, -0.13). On 40 sessions (placebo built on 40): lead-design z = +0.29, +0.43, +0.35, -0.67, -0.04; continuous z = -0.61, -0.23, +0.21, -0.04, -0.16.

Verdict rule applied by me (39 sessions, placebo C), criterion by criterion:

| rule | mean net > 0 | t > 2 | both halves > 0 | beats placebo by > 2 se | called "better than nothing" |
|---|---|---|---|---|---|
| R-A | no | no | no | no | no |
| R-B | no | no | no | no | no |
| R-C | no | no | no | no | no |
| R-D | no | no | no | no | no |
| R-E | no | no | no | no | no |

Same on 40 sessions and with every placebo variant. 0 of 5 pass.

## 6. Findings

**F1 reproduction (pass).** 975 of 975 trade rows and every summary figure match, 39 and 40 sessions.

**F2 look-ahead (pass).** None found; tested by perturbation, not only by reading.

**F3 prices and indexing (pass).**

**F4 short-return convention (minor, favours the rules).** `run_rules` and `settle` measure a short as `entry/exit - 1` (R-B: `Hs/c_end - 1`; R-D: `P/stop - 1`, `P/tgt - 1`, `P/c_end - 1`). The usual return on a short is `(entry - exit)/entry = 1 - exit/entry`. The lead's form overstates short gains and understates short losses by about the squared move (roughly 0.003 percentage points on average). Corrected: R-B -0.121% (t_cr -1.96, session-mean t -2.10), R-D -0.109% (t -5.43). Also, stops and targets are filled at exactly the stop/target price with no gap slippage and "strictly through" applies to stops and targets as well; both are stated or generous and do not matter here.

**F5 placebo artefact (moderate in wording, none in verdict).** The lead's placebo forms bar highs/lows from 15 one-minute closes only. A limit order is then assumed filled at the limit although the sampled path had already jumped past it; the average overshoot (about 0.05%) produces a negative gross return of about -0.05% for R-A and R-B that does not exist in a continuous market (where, by the martingale argument, gross is zero). With continuous monitoring (variant C) the placebo means for R-A and R-B are -0.101% and -0.102%, not -0.159% and -0.154%. The quoted placebo range "about -0.10% to -0.16%" should read "about -0.10% to -0.11%; the -0.15/-0.16 values for R-A and R-B come from sampling the path at 1-minute closes". The corrected z for R-A and R-B is slightly negative (-0.5, -0.2), not +0.44.
Second point: no placebo variant reproduces the real fill rates (real 48% / 53% for R-A / R-B against 55% to 64% in the placebo). The pins sit at pooled z-medians of +0.47 (high) and -0.52 (low), against 0.674 for a Gaussian random walk, because real hourly excursions are smaller than a random walk with the same sum of squared 15-minute returns (fat tails, mean reversion). So the placebo works as a "cost-drag" benchmark (about -0.10% per filled trade) but is not a calibrated null for fills.

**F6 t-statistic definition (minor).** The reported t uses the mean of session averages in the numerator but the table prints the trade-weighted mean. For R-A these differ (session-average -0.087%, trade mean -0.131%); for R-B -0.167% against -0.118%. Testing the printed trade means with session clustering gives t -2.06 (R-A) and -1.92 (R-B) instead of -1.47 and -2.07. No effect on the verdict. For R-C, R-D and R-E the two coincide.

**F7 interpretation of the large t's (wording).** R-C and R-D have t of -4.9 and -5.4 only because their returns are tightly bound near the cost: gross t is -0.13 and -0.42. They show that the rules earn nothing before costs, not that they "lose" more than the cost.

**F8 live ledger (two code and design issues, see section 7).**

**F9 data (caveat).** The 39 sessions come from two sources: `earlier_fetch` (2026-08-18 to 09-11, 17 sessions, mean 15-minute log range 0.44%) and `xlsx_workbook` (09-15 to 10-13, 20 sessions, 0.54%). Fill rates differ by block (R-A 41% against 51%; R-B 44% against 63%). That is either a volatility regime change or a difference in how bars were built; without 1-minute history it cannot be told apart. No verdict effect (every mean is negative in both blocks, except two tiny cells of 7 and 10 trades in the 14 to 15 Oct refresh).

## 7. Live ledger (results/paper_hourly_ledger.csv, 14:22 to 15:22 window of 16 Oct, n = 1 window)

Inputs from `results/paper_hourly_orders.jsonl`: P = 3372.3 (close of the 14:21 one-minute bar, confirmed), H* = 3383.7, L* = 3359.5. I also re-derived H* and L* from the 39 earlier sessions with the minute-weighted sigma (0.726%): 3383.7 and 3359.5, exactly the logged values.

Window facts from `results/live_hl_bars_1m.csv` (65 rows, 53 with volume): high 3373.5, low 3352.1; first minute with low < L* is 15:06; no bar above H*. The cache has no 1-minute bar between 15:15 and 15:28 (closing-auction slot): the last bar of the window is a zero-volume snapshot row stamped 15:15:00 at 3355.0, the last traded 1-minute bar (15:14) closed 3358.9, the auction print at 15:28 is 3363.0 (outside the window).

| rule | ledger (exit 3355.0) | my recomputation, same convention | with last traded close 3358.9 | with auction print 3363.0 |
|---|---|---|---|---|
| R-A | filled, -0.234% | -0.234% | -0.118% | +0.004% |
| R-B | no fill | no fill (high 3373.5 < 3383.7) | no fill | no fill |
| R-C | stop, -0.480% | -0.480% (stop at L*) | -0.480% | -0.480% |
| R-D | target, +0.281% | +0.281% (+0.280% with correct short return) | +0.281% | +0.281% |
| R-E | hour end, -0.613% | -0.613% | -0.497% | -0.376% |

Issues:
1. The logic of `place` and `settle` is correct (strict-through, stop first, 0.10% cost); the ledger values are reproduced. But the exit price of R-A and R-E (the only rules that exit at hour end here) is a zero-volume snapshot at 15:15:00, not a traded price; and a window that crosses 15:15 cannot be exited at 15:22 in a continuous market. The live `place` accepts any start up to 14:30, so windows ending 15:21 to 15:30 (never present in the backtest, whose last window ends 15:00) will always have this problem.
2. After commit e9027cc, `settle()` requires the last bar in the window to be within 5 minutes of the window end. For this very window the last bar is 15:15:00, 7 minutes before 15:22, so the current code returns 0 settled orders for it (I ran `settle` on scratch copies of the orders and cache). The committed ledger rows were settled under the earlier rule (row count at least 90% of the minutes). Any future order placed from about 14:21 to 14:30 will stay unsettled. Same condition in `hourly_table.score_logged`. Low severity, but it is a defect.

The single settled window says nothing about the rules (n = 1; one window and five dependent outcomes).

## 8. Which statements may be quoted

**Quote as they stand**
- Rules and verdict rule were committed at 14:19 IST (git 23a7f4c), two minutes before the backtest commit (state that git times are self-declared).
- Backtest, 39 sessions, 195 windows, 0.10% round trip, strict-through fills, stop first: trades, fill rates, mean net, median, win rates, half-sample means and the session-clustered t for R-B to R-E, exactly as in `results/paper_hourly_backtest.csv`.
- "None of the five rules passes the verdict rule." Holds for 39 and 40 sessions, with the placebo of either design, with target-first, and with corrected shorts.
- "Pin-points of a session use a profile and z-pool built without that session and no bar at or after the checkpoint."
- The ledger outcomes as arithmetic given the stated convention (with the exit-price caveat).

**Quote only after correction**
- Placebo means "about -0.10% to -0.16%": use "about -0.10% to -0.11%" (continuous paths: R-A -0.101, R-B -0.102, R-C -0.111, R-D -0.104, R-E -0.101); the lead's -0.159 / -0.154 for R-A / R-B are a 1-minute sampling artefact.
- z versus placebo for R-A / R-B (+0.44): corrected to -0.52 / -0.19.
- R-A t -1.47: say it is computed on the average of session means (-0.087%); the trade mean -0.131% has t -2.06. R-B -2.07 corresponds to a session mean of -0.167%; the trade mean -0.118% has t -1.92.
- R-B mean -0.118%: with the usual short return -0.121%. R-D -0.109% unchanged.
- "Mean net per trade" for R-A and R-B must say per filled trade (per window: -0.062% and -0.063%).
- 40-session figures: R-A 95 trades -0.130%, R-B 107 trades -0.121%, R-C 200 trades -0.101%, R-D 200 trades -0.110%, R-E 200 trades -0.099%.
- Ledger R-A -0.234% and R-E -0.613%: state that the exit is the zero-volume 15:15:00 snapshot (3355.0); with the last traded close they are -0.118% and -0.497%.

**Do not quote**
- The t of -4.9 / -5.4 (R-C, R-D) as evidence of losses beyond costs (gross is zero; the t only reflects cost relative to tiny variance).
- "No edge exists" or "the pin-points carry no information" as a finding: the backtest could only have found gross edges of about 0.14% to 0.23% per hourly trade; the supportable statement is "no edge found, and gross returns are zero within noise".
- The placebo as a calibrated null (its fill rates are 55% to 64% against real 48% to 53%).
- The single settled live window as evidence for or against any rule.

## 9. Reproduce

All scratch scripts are in `/tmp/claude-0/-home-user-pred-18/01384b6e-cd11-5bbc-b7f5-2dd03125e5eb/scratchpad/verPH/` (the main re-computation `ph.py` reads only `data/processed/intraday_union_15m.csv` and `data/processed/intraday_extra_15m.csv`; the cross-checks marked * import `src/` only to compare with the lead's code and write nothing to the repository). Run from the repo root with `PYTHONDONTWRITEBYTECODE=1`:

```
V=/tmp/claude-0/-home-user-pred-18/01384b6e-cd11-5bbc-b7f5-2dd03125e5eb/scratchpad/verPH
cd /home/user/pred_18
python3 $V/run1.py        # own LOO pins and trades, 39 and 40 sessions; row-by-row comparison with results/paper_hourly_trades.csv (writes bt39.csv, bt40.csv in $V)
python3 $V/run3.py        # sensitivities (short convention, target-first), per checkpoint tables, gross t
python3 $V/run4.py        # entry at bar open, R-C/R-D minus R-E, session mean versus trade mean, gross t
python3 $V/plc.py         # placebos A to D and the verdict rule (39 sessions)
python3 $V/plc40.py       # placebo and verdict rule on 40 sessions
python3 $V/leak2.py       # look-ahead perturbation test on my code
python3 $V/leak.py *      # same perturbation test on the lead's code (monkeypatched, no writes)
python3 $V/crosscheck_lead.py *   # lead's code on 39 sessions equals the committed CSV; placebo path equivalence
python3 $V/ledger.py      # live ledger recomputation from results/live_hl_bars_1m.csv and results/paper_hourly_orders.jsonl
python3 $V/settle_check.py *      # current settle() on scratch copies: settles 0 of 5 orders
```

Other sessions were running in the same working tree while I worked (`git status` showed changes to `src/hl_analog.py`, `src/hl_ml.py`, `src/hl_model2.py`, `results/hl5_2026-10-16.json` and a new `results/hl3_baseline_repro.csv`); none of them are mine and none of the files I read for this check were changed.
