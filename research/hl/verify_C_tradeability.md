# Independent verification of specialist C (can the estimated high / low be traded?)

Verifier report on `research/hl/C_tradeability.md` (working-tree version, which differs from HEAD: the builder's last edits are not committed), `src/hl_trade_study.py` and `results/hl_trade_*`. Written Thu 15 Oct 2026, late evening IST. I opened no data dated after 15 Oct 2026 22:00 IST: the daily files end 15 Oct, the hourly Yahoo file ends at the 15:15 bar of 15 Oct (checked by timestamp), `results/hl_eval_predictions.csv` ends 15 Oct, and I did not open `results/preopen/BSE_2026-10-16.jsonl` or any commit message (I listed commit hashes and times only). I edited no file except this one. Everything that writes files was run in an isolated copy in the scratchpad.

## 0. Verdict

**Pass with fixes needed. Severity: minor.** I found no look-ahead and no arithmetic error. Every headline number in the brief and in the report's "numbers to quote" reproduces from the raw files with my own code, to rounding (differences at most 5e-6 percentage points on any trade, which is the 5-decimal rounding of the builder's CSV). A full clean re-run of the builder's pipeline in an isolated copy reproduced 34 of 35 result files and the report byte for byte; the 35th (`hl_trade_summary.json`) has the same values plus three stale keys left over from an older version.

What needs fixing is small: one unfilled template placeholder in the report text, a handful of sentences that say more than the numbers support or that were never tested, two labels that would mislead a reader who quotes them (a mean called "typical", a "51.6 times" price rise that is bonus-adjusted), and a command line that is a research pipeline and not a trader-facing tool (raw tracebacks, JSON output, hard-coded 16 Oct). None of this changes a conclusion.

Plain-words summary of what the evidence supports (all of it is the builder's result, which I confirmed):
* Trading at the project's estimated low or high (limit buy at the estimated low, limit sell at the estimated high, exit at the close) lost money after a 0.10% round-trip cost in the 320 sessions since 1 Jul 2025: about Rs 14 a share per fill at the low (85 fills) and Rs 9.9 at the high (78 fills), at today's price of Rs 3,428. I also ran the same orders at the *median* estimated low and high (the "best guess" numbers a user is shown, which the builder did not trade): same sign, Rs 16 and Rs 11 lost per fill (section 7).
* The levels are reached as often as promised (26.6% and 24.4% against 25%), so the estimates are not wrong about *how often*; being reached just does not mean the price turns.
* The one rule that looks like an edge (follow a break of the first-hour range) earned +0.47% a trade in a six-month window, +0.04% after, and -0.14% since the closing auction. I confirm those numbers. It is a fading result.
* The rupee swing and stop tables are correct descriptions of the past (I rebuilt them). They are not forecasts.

## 1. What I checked and how

| step | what I did | result |
|---|---|---|
| A. code read | read `src/hl_trade_study.py` line by line (2,603 lines, working-tree version), `common.py`, `metrics.py`, `eval_hl.py`, the model file's docstring and the report builder | no look-ahead found (section 3); 10 defects (section 4) and a list of over- and under-statements (section 5) |
| B. independent numbers | re-coded the rules, windows, fills, Newey-West, Kupiec, Diebold-Mariano, excursions, stop tables, first-hour shares, Yahoo-vs-NSE and the 16 Oct scales in my own scripts that read only the raw CSV / JSON files and import nothing from the repo | all agree (section 2) |
| C. per-trade comparison | compared my trade lists for R1, R2, R3, R4a, R5, R6, R7, R8 and the EMP250 sibling of R7 against `results/hl_trade_trades.csv`, date by date | identical trade sets in all 9; max difference 5.0e-6 percentage points |
| D. tables | rebuilt all 64 daily stop/target cells (all years and Final, long and short) and the 16 hourly-resolved Final cells | max difference 1e-16 |
| E. clean re-run | copied `src/` and the input files into the scratchpad (`vC/repo`), deleted every `hl_trade_*` result, ran `python3 src/hl_trade_study.py all --hourly <h60 file> --reps 2000 --procs 4` | 3 m 36 s; 34 of 35 result files and `research/hl/C_tradeability.md` byte-identical to the repo's; self-test 12/12, independent check 145/145 |
| F. pre-fixed section | recomputed the SHA-256 of section 0 | matches the stored value in the working tree, at HEAD and at commit 51502d4 (see 5.8 for what this does not prove) |
| G. command line | ran `today` as a user would, with missing / wrong / empty hourly file and with two synthetic future rows (section 6) | works on the happy path; poor failure behaviour |
| H. extensions | median-level orders, model vs trailing-250 median, mirror identity, analytic and Monte-Carlo check of the first-hour placebo | section 7 |

My independence limit, stated plainly: I read the builder's code and the pre-fixed rule text before re-typing the rules, so my scripts are a second typing of the same specification. They check the coding, the arithmetic and the reading of the data, not the design. The stored model quantiles (`hl_eval_predictions.csv`) were verified for look-ahead by A's verifier (replaced every bar from a session onward by random numbers; levels unchanged); I did not repeat that, I only used the file.

## 2. Headline numbers recomputed (builder vs mine)

Rupees are percent x Rs 3,428 throughout, as in the report.

| # | claim (builder) | mine | difference |
|---|---|---|---|
| 1 | sessions: 2,390 daily; Final 320; post-auction 51; hourly 479 / 306 / 42 | 2,390; 320; 51; 479; 306; 42 | 0 |
| 2 | R7 Final: 85 fills, gross -0.308%, net -0.408% = -Rs 14.0 | 85; -0.3083%; -0.4083%; -Rs 14.0 | < 5e-6 pp |
| 3 | R8 Final: 78 fills, gross -0.187%, net -0.287% = -Rs 9.9 | 78; -0.1874%; -0.2874%; -Rs 9.9 | < 5e-6 pp |
| 4 | R1 Final 86 fills, net -0.405%; R2 95, -0.321%; R5 56, -0.016%; R6 320, -0.159%; R3 45, -0.285% | same counts; same means | < 5e-6 pp |
| 5 | fill rates Final 26.6% (Kupiec p 0.52) and 24.4% (p 0.80) | 85/320 = 26.56%, p 0.5214; 78/320 = 24.38%, p 0.7957 | 0 |
| 6 | DM, model q25 low level vs trailing-250 level, Final: t -4.3, Holm p < 0.001, 320 days | t -4.308, two-sided p 2.2e-05; mean daily P&L -0.1084% vs -0.0355% | 0.00 in t |
| 7 | R4a Validation +0.47% (n 105, Holm p 0.031); Final +0.04% (246, p 0.34); post-auction -0.14% (35); with 0.05% per leg -0.06% | +0.467% (105, HAC p 0.0010, x31 = 0.031); +0.039% (246, p 0.338); -0.141% (35); -0.061% | 0 |
| 8 | R4a pooled +0.17%, n 351, HAC p 0.023 | +0.167%, 351, p 0.0229 | 0 |
| 9 | Final swing from the official open: median high Rs 41, low Rs 45; 90th pct Rs 112 / Rs 115 (n 320) | Rs 40.97 / 44.95; Rs 111.7 / 115.5 | < Rs 0.5 |
| 10 | stop touched: 0.5% (Rs 17) 81%, 1% 60%, 1.5% 42%, 2% 32% | 80.9%, 59.7%, 42.2%, 31.9% | 0 |
| 11 | 1% stop / 2% target long: stopped first 52-60%, target first 24-32%, neither 17% | 51.6-59.7%, 23.8-31.9%, 16.6% | 0 |
| 12 | entering at 10:15: Rs 28 up / Rs 30 down; at 13:15 Rs 16 / Rs 17 (n 306) | Rs 27.9 / 30.2; Rs 16.3 / 17.0 | 0 |
| 13 | high or low in the first hour: 35/42 = 83.3%, 258/306 = 84.3%, 414/479 = 86.4% | 35/42; 258/306; 414/479 | 0 |
| 14 | official open is the day's high or low in 10.6% of 1,923 sessions (119 + 85), 9.8% of 51 | 204/1,923 = 10.61% (119 + 85); 5/51 = 9.8% | 0 |
| 15 | open equals previous close on 9 of 51 post-auction sessions (17 of 269 earlier in Final, 5.4% in Development) | 9/51; 17/269; 73/1,355 = 5.39% | 0 |
| 16 | Yahoo vs NSE mean abs: high Rs 1.3, low Rs 1.9, open Rs 6.0; 90th pct 3.5 / 4.5; max 46 / 55 | 1.26; 1.93; 6.01; 3.55 / 4.52; 46.4 / 54.7 | < 0.1 |
| 17 | typical miss of A's median forecasts, Final: pre-open high Rs 43 / low Rs 48, post-open Rs 35 / Rs 37 | mean absolute 42.7 / 47.7 / 34.8 / 37.4 (median absolute 33.6 / 32.2 / 29.1 / 26.6) | < 0.1 |
| 18 | stop-distance table (section 3.6, Final): touched 44.7% / 23.1% / 6.6% (long, 50/75/90th pct), Kupiec p 0.057 / 0.435 / 0.030 | 44.7% / 23.1% / 6.6%; 0.057 / 0.435 / 0.030 (also all short rows, Development and all-years rows) | 0 |
| 19 | range already formed by 14:15 (Final): high 79%, low 73%, both 52%; hour-by-hour shares of the high 53/8/6/4/7/11/9% | 79 / 73 / 52%; 53/8/6/4/7/11/9% | 0 |
| 20 | 16 Oct scales: close-to-close 2.26% = Rs 77, gap 0.78% = Rs 27, open-to-low 1.90%, open-to-high 2.01%; R1 offset Rs 65, R2 offset Rs 70 | 2.2601% = Rs 77.5; 0.7781% = Rs 26.7; 1.9001%; 2.0101%; Rs 64.5 / Rs 69.6 | 0 |
| 21 | stop distances for a long, 50 / 25 / 10% touch: trailing-250 Rs 42 / 80 / 107; EWMA-scaled Rs 40 / 68 / 106 | Rs 42.0 / 79.9 / 107.0; Rs 40.1 / 68.5 / 106.2 | 0 |
| 22 | regime for 16 Oct: mid (expanding), mid (full sample), low (trailing 500); Final counts 3/261/56, 263/57/0, 76/212/32 | cut points 1.716 / 2.857, 2.149 / 3.045, 2.443 / 3.217 -> mid, mid, low; full-sample Final counts 76 / 212 / 32 | 0 |
| 23 | average gap +0.27% a day, open-to-close -0.03% (t -0.55), price x51.6 (Validation x3.2, Final x1.24) | +0.274%; -0.035% (t -0.549); x51.56 (x3.218, x1.2375) | 0 (but see D4) |

Coverage and pinball of the stored quantiles themselves, which the builder did not repeat (they are A's tables; I recomputed them in Final, n = 320, from the stored file): 50% / 90% central coverage pre-open high 46.9 / 90.3, pre-open low 50.3 / 88.7, post-open high 49.4 / **95.0**, post-open low 50.3 / 89.4. Kupiec p for the 90% band: 0.851, 0.464, **0.001**, 0.712. The post-open high band over-covers because the bootstrap forces the high to be at or above the open. This does not touch C's trading results (C traded the 10 / 25 / 75 / 90% levels, whose fill rates are fine: smallest Kupiec p across all post-open fill cells 0.20), but "the levels are calibrated" in section 7 is true for the traded levels only. Mean pinball over the seven stored quantile levels on the log scale, x1e4: pre-open high 36.7, low 42.8; post-open high 28.4, low 33.1 (my own convenience measure, not the same grid as A's pinball table, so do not compare the two).

## 3. Look-ahead, timing and arithmetic review

| item | finding |
|---|---|
| `ewma_rms` (all scale estimators) | value at t uses x[:t]; first 30 sessions initialise. I verified by truncation: the value at t=500, 1500 and 2389 recomputed from data[:t] equals the stored one to 1e-14. No look-ahead. |
| `roll_q` (trailing-250 quantiles) | out[t] = quantile of x[t-250:t]. Checked by window arithmetic and by recomputing the EMP250 trade list over all 510 fills: identical. |
| R1 / R2 / R7 / R8 limit orders | level fixed from the open (final 09:08) and past data; the order can only be entered at 09:15; the official low / high include only the auction print at or before the open, which cannot fill a level that is below (above) the open. Fill uses the day's extreme (ex-post event, ex-ante rule). Entry price = level. Return = C/level - 1 (long) or 1 - C/level (short): simple returns, correct sign. |
| R7_pre / R8_pre | pre-open order: fills at the open if the open is at or through the level, else at the level; correct. |
| R5 gap rule | z uses the gap and a past-only scale; entry at the official open (needs the pre-open auction; the report says so). |
| R6 brackets | stop `<=` (touch), target strict `>`; conservative reading = stop first when both are touched; shorts use `1 - C/O`. Correct. |
| R3 (fade) / R4 (breakout) | signal from the first hourly bar only (known 10:15); `sig1` is an EWMA of earlier hourly sessions with a 40-session burn-in; R4a decisions use bars up to and including the entry bar; entry at the bar's open if it gaps through the range edge, else at the edge; ambiguous bar scored as the loser; exit at the official close. I re-coded R3 and R4a from the bars and got the same trades (60 and 351, same dates). No look-ahead. |
| bar times | Yahoo label = bar start; bar k ends at 09:15 + 60k min; the report's "10:15 price = close of bar 1" is right. |
| bonus adjustment | open / high / low / close in `bse_daily.csv` are raw traded prices; only `prev` is adjusted on the two ex-dates (prev = prior close / 3.000 exactly, 2022-03-21 and 2025-05-23, my check). So every within-row ratio is exact. Yahoo hourly bars before 23 May 2025 are raw / 3; the x3 factor makes the Yahoo day high 0.9999 of the NSE high before and after the ex-date. Correct. The "51.6 times" is on the adjusted base; the quoted price went 598.4 -> 3,428 = 5.73x (see D4). This also confirms A's verifier: the brief's "prices are bonus-adjusted" is wrong for price levels. |
| rupee conversion | percent x Rs 3,428 for all windows, disclosed in section 3; it overstates what was actually traded early in Final (price Rs 2,770 on 30 Jun 2025). |
| costs | 0.10% round trip deducted once per filled trade; the 0.05% per marketable leg stress uses the leg count: R4a (2 legs) 0.039 - 0.10 = -0.061, my number matches. |
| Newey-West / Kupiec / DM | Bartlett lag 5, t reference df n-1 for trade means; DM with the HLN factor sqrt((n-1)/n); formulas match `metrics.py` and my own typing. DM result is robust: t between -4.2 and -5.1 for lags 0 to 20, and a block-bootstrap (block 10) 95% interval for the daily P&L difference is -0.105% to -0.040%, never above zero. |
| Holm | step-down on one-sided HAC p-values, family padded to 31 (windows without the hourly rules are not favoured). R4a Validation: p 0.0010 x 31 = 0.031. Final: the smallest p among the positive-mean variants is 0.158, so every Holm value is 1.0. Correct. |
| placebo | the null is calibrated on the full real sample (variance clock, volatility of volatility, window drift for setting B), so it is not a pure out-of-sample null. This is by design and disclosed; it matters only for `placebo p`, which never decides a verdict here because no rule passes the earlier gate. My own coarse Monte-Carlo of a random walk with the two variance clocks gave P(high or low in the first hour) 80.9% and 85.5% (discretised paths bias this down by 1-2 points); the analytic arcsine-law value with my simulated P(both) is about 83% and 89%; the builder's 82.3% and 87.5% lie between. The conclusion (86.4% observed sits between the two clocks, p 0.02 to 0.52) stands. |
| self-test | the first ten rows are real checks (perturb one session, compare earlier outputs bit for bit; positive controls change; placebo log-return mean within 4 standard errors of zero); the last two are labelled "(info)" and always true. 12/12 is correct and honestly described as 10 real checks plus 2 informational. |
| stop-estimator side study (3.7) | EWMA-scaled uses `sig[t]` known at t-1 and the quantile of earlier standardised values; expanding uses a[:t]. No look-ahead. |
| text-vs-code mismatch (minor) | section 0.4 writes the levels as O x (1 - k sigma_L) and O x (1 + k sigma_H); the code uses O x exp(-k sigma_L) and O x exp(+k sigma_H). The difference is sigma^2/2, about 0.018% of price at the current sigma (Rs 0.6), up to about 0.05% in volatile periods. Immaterial next to a Rs 3.4 cost, but it is a pre-fixed text that does not match the code (like the tick-rounding mismatch the builder already disclosed). |

## 4. Defects (things to fix)

* **D1. Unfilled template in the report.** Section 3.7, last sentence of the "Plain reading" paragraph (line 369 of the working-tree report) prints the literal text `{f(mx_dev, 1)}`: the string at `src/hl_trade_study.py` line 2113 is missing its `f` prefix. The value it should show is **7.2** (the EWMA-scaled 75% short stop, touched 32.2% against 25% in Final; the next largest gaps are 5.6 and 5.3). The sentence "within roughly five to seven percentage points" is then right. This was introduced in the last, uncommitted edit (HEAD says "within a few percentage points").
* **D2. "four stored ones" is wrong.** Section 6 "Not tested" says "model quantiles at levels other than the four stored ones". The stored file has seven levels (5, 10, 25, 50, 75, 90, 95%); four were traded. The 50% level, which is the "estimated high / low" number the user is actually shown, was never traded. I traded it (section 7): same sign, so the conclusion stands, but the report should say the median level was untested.
* **D3. "Typical miss" is a mean.** The numbers-to-quote line "Typical miss of A's median forecasts, Final: pre-open high Rs 43 / low Rs 48; post-open Rs 35 / Rs 37" gives the mean absolute miss. Section 7 uses "typical" for the median (Rs 34 / 32 / 29 / 27, "half the time within"). One word, two meanings. The user asked for typical-miss rupees, so label them: average miss Rs 43 / 48 / 35 / 37, half the time within Rs 34 / 32 / 29 / 27.
* **D4. "price multiplied 51.6 times".** True on the bonus-adjusted base only (two 2:1 bonus issues, each tripling the share count). The share price quoted on the exchange went from Rs 598 (31 Dec 2018 close) to Rs 3,428, i.e. 5.7 times. Section 4.10 says "(bonus-adjusted)" but the numbers-to-quote bullet does not. A trader will check the quoted price and think the number is wrong.
* **D5. R4's "descriptive" is explained incompletely.** The brief and section 1 say R4 is descriptive "only because its Final-window mean is above zero". Under the report's own rule it is also descriptive because its Validation-window *gross* edge is significant (gross +0.57%, HAC p 0.0001, unadjusted). The sentence understates how strong R4 looked in Validation; section 5.2 does give the facts.
* **D6. The command line is not a user tool** (section 6).
* **D7. Pre-fixed text vs code** for the limit levels (section 3, last row).
* **D8. `results/hl_trade_summary.json`** keeps three stale keys (`regime_for_16oct`, `tercile_cut_low_mid_pct`, `tercile_cut_mid_high_pct`) from an older code version; a clean run does not produce them. Nothing reads them.
* **D9. Run-time statement.** Section 2 says the last full run finished about 09:23 IST on 16 Oct, after the open, and that the builder saw in a git commit message that a 16 Oct pre-open snapshot exists "and what opening price it records". No number depends on it (inputs end 15 Oct; my clean re-run used only inputs dated up to 15 Oct and reproduced everything byte for byte), but the lead should know the builder was exposed to the 16 Oct opening price, and that the 16 Oct section (8) was therefore written by someone who had seen it. Section 8 is still a pure function of data to 15 Oct (I rebuilt it).
* **D10. Power sentence slightly too strong.** Section 6: "Effects of the size that survive costs (0.1-0.2% per trade) are below the detection limit of every rule." R6's minimum detectable effect is 0.17%, R4a's 0.23%. An edge of 0.2% would be detectable for R6 and borderline for R4a. The conclusion (low power for limit-order rules, MDE 0.31-0.68%) is right.

## 5. Over- and under-statements, selection, contradictions

5.1 **"describes the same fade independently"** (section 5.2). The project's earlier note (DEVIATIONS #33, `docs/LIVE_TOOLS.md`: "follow the first-hour move +0.8% per trade t 3.3 in the first 60%, about zero in the last 40%") was computed on the **same two years of Yahoo hourly bars**. C's R4 is a different rule on the same data, so the agreement is the same sample seen twice, not independent confirmation. Say "consistent with", not "independently". A related fact I computed (not in the builder's files): the Validation-to-Final drop of R4a (+0.467% to +0.039%) has t = 2.4 on the difference (unadjusted two-sided p about 0.015), so the fade is itself distinguishable from noise, but it is one half-year against the rest.

5.2 **"A target at the estimated high is a reasonable place to think about taking profit on a long you already hold"** (section 7, item 4). Nothing tested that. The builder's own R8 / M8 numbers point the other way: after the price traded through the estimated high, it closed higher on average (R8 gross -0.19% in Final, -0.41% over 2020-2026, i.e. continuation), so taking profit there gave up average gains. Remove or mark as untested opinion.

5.3 **"That is smaller than the naive guesses"** (section 7, item 4). The comparators are "price stays" (Rs 63 / 61) and "open stays" (Rs 51 / 59), the weakest ones. Against the **median of the last 250 sessions' own swings** the model is a tie: mean absolute miss in Final, model vs trailing-250 median, pre-open high 42.7 vs 43.7, low 47.7 vs 47.5, post-open high 34.8 vs 35.4, low 37.4 vs 37.6 (paired differences Rs -1.0, +0.1, -0.6, -0.2; HAC t -1.7, 0.3, -1.0, -0.6; none significant). A's verifier made the same point. The quote "good to about Rs 43 / 48" should carry "a plain 250-day history is as good".

5.4 **"late entries rarely pay their costs"** (section 1, item 3). The cost is the same Rs 3.4 at any time of day; what shrinks late in the day is the remaining swing (median Rs 16-17 after 13:15). Better wording: "after 13:15 a profit target bigger than about Rs 17 is reached on fewer than half of the days."

5.5 **"Contradictions with earlier project claims: none found"** (section 6). Two small ones: (a) `FORECAST_REPORT_V2.md` section 1.2 calls the daily OHLC "bonus-adjusted"; only `prev` is (A and its verifier already said so); (b) `docs/INPUT_AUDIT.md` says Yahoo and NSE highs / lows differ "by up to about Rs 4"; over 479 sessions the mean absolute gap is Rs 1.3 / 1.9 and 90% are within Rs 3.5 / 4.5, but 5% (high) and 9% (low) of sessions differ by more than Rs 5 and the maxima are Rs 46 and Rs 55. The report prints these but frames them as "close to". In the rows I looked at, the biggest gaps coincide with a large difference between Yahoo's first printed open and the NSE auction open (for example 4 Jul 2025: both Rs -46.4, where the NSE high is the auction open price), so the cause looks like the opening auction, not random noise. (C's "9 of 51" against V2's "8 of 50" open-equals-previous-close is not a conflict: two more sessions.)

5.6 **Section 3.7 (EWMA-scaled stops beat the trailing-250 quantile)** is a descriptive side study, correctly labelled, but the report's own numbers are thin: pinball differences are 0.2% to 7% of the loss, two of the four "significant" cells have Holm 0.0496, all of it comes from the Development years, and in Final the 75% short stop is touched 32.2% of the time against 25%. Do not quote it as "better stops". For 16 Oct, quote a range across the two estimators (Rs 40-42 / 68-80 / 106-107), not one method.

5.7 **Post-hoc "mirror" variants** (section 5.1). M1 / M2 / M7 / M8 are exact sign flips of R1 / R2 / R7 / R8: for every trade the gross return is the negative of the matching R-rule's (for example M2 all-years net +0.263% = -(R2 gross -0.363%) - 0.10%). They add no information beyond "R2 and R8 lost money gross", and they were built from the rules that lost. The 47-test Holm treats them as separate tests (conservative) but cannot undo the selection of mirroring the losers. The report calls them suggestive only; that is the right label. Do not quote +0.26% / +0.31% as evidence of an edge.

5.8 **Pre-fixed section.** The SHA-256 of section 0 is unchanged (checked). But the first commit containing result files (51502d4, 17:13 UTC) is ten minutes after the hash file (17:03:06 UTC), and that commit also contains the 28 result files of the earlier attempt, so git cannot show that no result existed when section 0 was hashed. The builder says so. And the "Final window was not used to choose a rule" sentence holds for C's own work, but the project had already tested "buy the predicted low / short the predicted high" on daily data to 12-13 Oct (DEVIATIONS #30, losses) and follow-the-first-hour rules on the same hourly sample (DEVIATIONS #33). Final is therefore not a clean hold-out for these ideas at project level. Because every one of these earlier looks pointed to "no edge", this can only have made an edge more likely to be reported, not less, so the null is not weakened.

5.9 **Selection.** The brief's "R4 is the one descriptive rule" is the best of eight primaries; the report applies Holm (31 variants) and reports all 31 and all windows. I found no best-of-many number without an adjustment, except the unadjusted p-values in the post-hoc table that are labelled as such.

5.10 **What I could not confirm.** "Two to four re-runs byte-identical" (I did one more clean run: yes). "Report-vs-files cross-check, 902 comparisons, 0 mismatches": the script is in the builder's scratchpad, not in the repo; I did not re-run it, but the report text is generated from the CSVs by code and I checked many numbers directly against raw data (section 2). Prose numbers that are typed by hand (for example "0.15-0.3% per year", "5-16 fills", "6-7% of Final days", "2,000 simulated histories", the Rs 10,000 share arithmetic) I checked and they are right.

## 6. The command line, run as a user would

Commands (isolated copy; nothing in the repo was touched). The tool has no network code, so "API 429" cannot occur; the real failure modes are missing or stale files.

| case | what happens | judgement |
|---|---|---|
| `python3 src/hl_trade_study.py today` (no `--hourly`) | `FileNotFoundError: ''` traceback | bad: `today` uses only the daily files but demands an hourly file |
| `--hourly /nonexistent.json` | `FileNotFoundError` traceback | bad: no plain-words message |
| `--hourly` pointing at `{}` | `KeyError: 'chart'` traceback | bad |
| `today --hourly <good file>` | prints a JSON block with 15-digit floats and the line `[today] 0.1s`; writes three `results/hl_trade_today_*` files | numbers are right (section 2, rows 20-21), but it is not plain words and not readable by a trader |
| `today` run alone in a fresh clone | the three `regime_*` fields print `null` (they come from `part1`) | the dependency on `part1` is not stated |
| two synthetic rows dated 16 and 17 Oct (Fri and Sat) added to the extra file in the copy | prints `[cutoff] dropping 2 daily session(s) dated after 2026-10-15` and the output is unchanged | the guard works; but the tool can never produce numbers for a later date: the cut-off, the reference price Rs 3,428, `next_session` "2026-10-16" and the file names are hard-coded |
| weekend, after the close, no bars yet, API error | not applicable: no live data is read | the report is the deliverable, the script is a research pipeline; there is no "run it tonight" mode |
| `all` | 3 m 36 s on 4 cores, reproduces all files | good |

Also: the hourly Yahoo file is not stored in the repo (its SHA-256 is in `hl_trade_summary.json`: `ef5d3b6b...`), so the exact commands in section 10 of the report cannot be run from a fresh clone. They can be run with the copy in the session scratchpad. The report says so.

The only plain-words output is the report itself. Its section 1 is clear. The glossary in "Words used" does not define HAC, Kupiec, MDE or pinball, which appear in sections 1 and 4.

## 7. Extra checks I added (verifier extensions, descriptive, not Holm-adjusted)

**Orders at the median estimated low / high (the "best guess" levels, untested by the builder).** Limit buy at the stored median low, limit sell (short) at the median high, same fill rule (strictly through), exit at the official close, 0.10% round trip, simple returns. Net % per fill; sessions and fills in brackets; Newey-West t.

| level | window | sessions | fills | gross % | net % | net Rs | t |
|---|---|---|---|---|---|---|---|
| post-open median low (W_I6 q50), buy | Final | 320 | 154 (48%) | -0.354 | -0.454 | -15.6 | -3.5 |
| post-open median high (W_I6 q50), short | Final | 320 | 159 (50%) | -0.212 | -0.312 | -10.7 | -2.8 |
| pre-open median low (P_S6 q50), buy | Final | 320 | 160 (50%) | -0.313 | -0.413 | -14.1 | -2.8 |
| pre-open median high (P_S6 q50), short | Final | 320 | 149 (47%) | -0.241 | -0.341 | -11.7 | -2.5 |
| post-open median low / high | post-auction (51) | 51 | 25 / 25 | -0.388 / -0.271 | -0.488 / -0.371 | -16.7 / -12.7 | -2.1 / -1.6 |
| post-open median low / high | all 2020-2026 (1,640) | 1,640 | 786 / 818 | -0.193 / -0.250 | -0.293 / -0.350 | -10.0 / -12.0 | -4.0 / -4.0 |

Every level the model states (10, 25, 50, 75, 90%), before or after the open, loses money net in Final. This extends the builder's null to the numbers the user is shown; it is a post-hoc extension, so read it as "same sign everywhere", not as an extra tested hypothesis.

**Model vs plain history.** See 5.3.

**Mirror identity.** See 5.7.

## 8. What the lead may quote, must correct, must not quote

**Quote as they stand** (all recomputed from raw data; rupees are percent x Rs 3,428, so say "at today's price"):
1. 0 of 8 pre-fixed rules (31 variants) validated; 7 "not found", R4 "descriptive". (Say the reason as in D5.)
2. Estimated-low limit buy, Final: 85 fills in 320 sessions, -0.31% gross, -0.41% net = -Rs 14 a share per fill. Estimated-high limit sell: 78 fills, -0.29% net = -Rs 9.9. Add: same sign at the median levels (my 7).
3. Fill frequency of the model's levels: 26.6% against 25% (Kupiec p 0.52) and 24.4% against 25% (p 0.80), n = 320.
4. R4a: Validation +0.47% (n 105, Holm p 0.031), Final +0.04% (n 246, p 0.34), since the closing auction -0.14% (n 35); -0.06% in Final with a further 0.05% per marketable leg.
5. Final-window swing from the official open (n 320): median high Rs 41 above, median low Rs 45 below; 90th percentile Rs 112 / Rs 115.
6. Stop touched on 81% (0.5%, Rs 17), 60% (1%, Rs 34), 42% (1.5%), 32% (2%, Rs 69) of Final sessions; 1% stop with 2% target (long): stopped first 52-60%, target first 24-32%, neither 17%.
7. Entering at 10:15 leaves a median Rs 28 up / Rs 30 down (n 306, Yahoo hourly extremes); at 13:15 Rs 16 / Rs 17; round trip Rs 3.4.
8. High or low in the first hour: 83.3% (35 of 42) since the closing auction, 84.3% (258/306) in Final, 86.4% (414/479) overall; random-walk placebo 82.3% to 87.5%; so not a tradable pattern.
9. Official open is the day's high or low in 10.6% of 1,923 sessions (9.8% of 51 since the closing auction); open equals the previous close on 9 of 51 sessions since the auction (17.6%, against 6.3% and 5.4% earlier).
10. Final-window power: minimum detectable effect 0.17% to 0.68% net a trade.
11. 16 Oct descriptive numbers: close-to-close scale 2.26% = Rs 77; adverse swing from the open in the last 250 sessions, long side, 50 / 25 / 10% touch: Rs 42 / 80 / 107 (trailing-250), Rs 40 / 68 / 106 (volatility-scaled); regime "mid" by two of three definitions. Present as descriptive, in rupees at Rs 3,428, not as a forecast.
12. Checks: self-test 12 of 12 (10 real checks), builder's own re-typing 145 of 145, and now a third party's clean re-run reproduced all files.

**Quote only after this correction:**
* Typical miss (D3): "average miss Rs 43 (high) and Rs 48 (low) the evening before, Rs 35 and Rs 37 after the open; half the time within Rs 34 / 32 and Rs 29 / 27; a plain 250-day history of the same swings is as good (Rs 44 / 48 / 35 / 38)".
* Price rise (D4): "51.6 times, bonus-adjusted; the quoted price went from Rs 598 to Rs 3,428 (5.7 times) since January 2019 because of two bonus issues".
* Average gap +0.27% a day against open-to-close -0.03% (t -0.55): true, but the gap is a mean of logs and the open-to-close a mean of simple returns (immaterial here), and the old closing price was a 30-minute average, so say "descriptive of this sample; not an overnight trading rule".
* Yahoo vs NSE: "usually within Rs 3.5 (high) and Rs 4.5 (low), but on 5% and 9% of sessions by more than Rs 5, up to Rs 46 and Rs 55; Yahoo's range is on average Rs 3 narrower; the first printed open differs by Rs 6 on average".
* DM result: "for the 25% low level the model's order lost about Rs 2.5 a share a day more than the same order at a plain trailing-250 level (320 days, t -4.3); in the post-auction slice and for the other three pairs no significant difference". It is a P&L comparison of two orders, not an accuracy comparison of the quantiles.
* R4 as "descriptive": add the Validation-window gross significance (D5) and "same sample as the project's earlier first-hour note, not independent".

**Do not quote:**
* The sentence with `{f(mx_dev, 1)}` (D1); if the stop-tolerance is quoted, say "within about 5 to 7 points of the promised share (largest 7.2 in Final)".
* "A target at the estimated high is a good place to take profit" (5.2), and "late entries rarely pay their costs" (5.4).
* "Smaller than the naive guesses" without the trailing-250 comparator (5.3).
* Section 3.7's "volatility-scaled stops are better" as a finding (5.6).
* The post-hoc mirror numbers (+0.26%, +0.31%, +0.12% in Final) as an edge (5.7).
* The R6 placebo p-values (the report itself says they are not a fair null).
* "The levels are calibrated" without "the traded levels"; the post-open high 90% band over-covers (95.0%, Kupiec p 0.001).
* Any statement that the Final window was a clean hold-out for these trading ideas (5.8).

## 9. Limits of this verification

* My scripts are a second typing of the builder's specification (and of the stored model quantiles, taken from the file), so they test coding and arithmetic, not whether the rules are the right ones to test. I did not re-fit the volatility model; A's verifier did and found no look-ahead.
* I did not re-derive the 2,000-history placebo independently; I checked its first-hour output against theory and a coarse simulation of my own (about 1-2 points of agreement), and its other p-values only through the full re-run (bit-identical, same seeds). No verdict depends on the placebo.
* Timing of the pre-fixed section cannot be audited from git (5.8).
* The hourly file is a single Yahoo download; I checked its SHA-256 and time range, not its contents against another source.
* Costs, fills and exit at the official close are idealised, as the report states.

## 10. Commands to reproduce my numbers

Scripts are in `/tmp/claude-0/-home-user-pred-18/01384b6e-cd11-5bbc-b7f5-2dd03125e5eb/scratchpad/vC/` (they read `/home/user/pred_18/data/processed/*.csv`, `/home/user/pred_18/results/hl_eval_predictions.csv` and the hourly file `/tmp/claude-0/-home-user-pred-18/01384b6e-cd11-5bbc-b7f5-2dd03125e5eb/scratchpad/h60_BSE.NS.json`; they import nothing from the repo). Run in that directory in this order (`ind1.py` writes `arrs.npy` and `dates.json` that the others load):

```
cd /tmp/claude-0/-home-user-pred-18/01384b6e-cd11-5bbc-b7f5-2dd03125e5eb/scratchpad/vC
python3 ind1.py    # table rows 1, 9, 10, 11, 14, 15 (sessions, swings, stops, open = high/low, open = previous close)
python3 ind2.py    # rows 2-6: R1, R2, R5, R6, R7, R8, EMP250 sibling, Kupiec, DM with lag and bootstrap robustness
python3 ind3.py    # rows 7, 8, 12, 13, 16: hourly loader, R3, R4a, first-hour shares, 10:15 and 13:15 room, Yahoo vs NSE
python3 ind4.py    # coverage, pinball and typical miss of the stored quantiles (row 17 and section 2 note)
python3 ind5.py    # rows 20, 21: 16 Oct scales and stop distances
python3 ind6.py    # rows 18, 19: range formed, hour-of-extreme, stop calibration tables
python3 ind8.py    # section 7: orders at the median estimated low / high
python3 ind9.py    # 64 daily and 16 hourly stop/target cells vs hl_trade_stop_target_*.csv
python3 ind10.py   # model median vs trailing-250 median (5.3)
python3 ind11.py   # first-hour placebo: my own Monte-Carlo of the two variance clocks (section 3, placebo row)
python3 ind12.py   # trade-by-trade comparison with results/hl_trade_trades.csv
```

Rows 22 and 23 and the regime check were run inline with the same data (the same formulas as `ind5.py` / `ind1.py`; see `ind5.py` for the EWMA series and the three tercile definitions). Clean re-run of the builder's pipeline:

```
cd /tmp/claude-0/-home-user-pred-18/01384b6e-cd11-5bbc-b7f5-2dd03125e5eb/scratchpad/vC/repo
export HL_TRADE_TMP=/tmp/claude-0/-home-user-pred-18/01384b6e-cd11-5bbc-b7f5-2dd03125e5eb/scratchpad/vC/tmp
python3 src/hl_trade_study.py all --hourly /tmp/claude-0/-home-user-pred-18/01384b6e-cd11-5bbc-b7f5-2dd03125e5eb/scratchpad/h60_BSE.NS.json --reps 2000 --procs 4
sha256sum results/hl_trade_* research/hl/C_tradeability.md      # compare with /home/user/pred_18/results/ and research/hl/
```
