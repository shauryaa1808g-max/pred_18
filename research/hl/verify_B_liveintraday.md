# Independent verification of Specialist B (live running high / low tool)

Verifier: independent, did not trust the builder's summary (it was lost); judged `research/hl/B_liveintraday.md`, `src/live_highlow.py` and `results/live_hl_*` on their own.
Clock rule: nothing dated after Thu 15 Oct 2026 22:00 IST was requested or used. The CLI tests ran with the network pointed at a dead local proxy (the machine's real clock is already Fri 16 Oct morning), so no Yahoo call could return anything. Data used: `data/processed/bse_daily.csv` + `bse_daily_extra.csv` (14-15 Oct are in the extra file), the two 15-minute files, the builder's cached 1-minute bars (7-15 Oct), and the scratchpad hourly file (last bar 15 Oct 15:15 IST).

## 0. Bottom line

**Verdict: pass with fixes needed. Severity: minor** (nothing that was quoted as a headline number is wrong; several sentences overreach and a few printed phrases are not backed).

* Every headline number I re-computed from the raw files with my own code (not the builder's functions) came out the same: offsets, rupee misses, pinball losses, Diebold-Mariano p-values, calibrated multipliers, coverage per checkpoint, the chronological check, the hourly walk-forward, the "high is already in" reliability, the 15 Oct replay. Largest difference in any pinball loss: 0.005 Rs (rounding). Per-checkpoint hit counts: identical. The builder's `--backtest` re-run in an isolated copy gave **15 of 15 CSV files byte-identical** (only timestamps differ).
* I found **no look-ahead** beyond what the builder already admits (leave-one-out uses later sessions for the profile, the multiplier and the offsets; the strictly chronological run, n = 19, gives the same picture and I reproduced it).
* Things that must change before the lead repeats them: (a) the "time-of-day profile earns its keep in the hourly sample (+1.6%, p < 0.001)" claim is an artefact of a badly built benchmark (section 3.1); (b) the "+-8 / +-5 points" uncertainty is one standard error, not a 95% range; (c) the hourly Yahoo-vs-NSE table mixes rupee units; (d) two phrases the tool prints to the user ("if it extends, another Rs X-Y is typical" and "chance of at least Rs 5 / 10 / 20 / 40") are not validated and in my test run too optimistic / too narrow (section 3.4); (e) the tool never uses the official opening price, which on gap-open days is the day's high or low and can sit Rs 30-55 outside Yahoo's bars (section 3.5).
* This tool does **not** forecast tomorrow's high and low. Nothing from it should be presented as the Fri 16 Oct forecast. It is for use during the session, and the numbers are not validated before about 09:45.

## 1. What I checked and how

| # | Check | Result |
|---|---|---|
| 1 | Read `src/live_highlow.py` (1,324 lines), `live_nowcast.py`, `metrics.py`, `common.py` line by line for look-ahead, off-by-one, units, sign | no look-ahead found; details in section 2 |
| 2 | Re-implemented the whole 15-minute study from the raw files (profile, closed-form distribution of the future maximum, nested leave-one-out multiplier, offset convolution, B1, B2, coverage, Kupiec, Diebold-Mariano, cluster bootstrap) | matches, section 4 |
| 3 | Re-implemented the hourly walk-forward (479 sessions, 429 scored) including M0, M1, B1-B4, M3a, M6 | matches to 3 decimals, section 4 |
| 4 | Compared every number in report tables T3a, T3b, T4a-T4e, T9 (about 320 cells) against the CSV files | 0 mismatches |
| 5 | Stronger leak test than the builder's: replaced **all bars after 12:30** of one session with junk and re-ran the builder's engine | forecasts at checkpoints up to 12:30 unchanged (max change 0.0 for 15 variants); the 15:00 forecast moved by 8.5 (control), so the test can detect a leak |
| 6 | Independent Monte-Carlo and an algebraic re-derivation of the closed form F(b) = Phi(b/s_c) + Phi(b/sigma_W) - 1 | correct (derivation in 2.2); the builder's `--selftest` passes (max difference to simulation 0.0023) |
| 7 | Ran the CLI as a user in every failure case listed in the task, plus a faked Yahoo feed and faked 429s | section 5 |
| 8 | Looked for hidden causes of the Yahoo-vs-NSE gap, unit problems, benchmark construction, calibration of the printed phrases | section 3 |
| 9 | Re-ran `--backtest --hourly ...` and `--selftest` in an isolated copy of `src/` + needed data | byte-identical outputs (backtest 77 s) |

## 2. Code audit

### 2.1 Timing of every feature (relative to the forecast time T)

* Checkpoint m = m completed 15-minute (or hourly) slots. Price = close of slot m-1; running high / low = max / min of the highs / lows of slots 0..m-1 (`Sample.__init__`, lines 287-300). Nothing from slot m onward enters the state. Verified by the junk-bar test above.
* 15-minute checkpoint labels are right: 09:45 = m 2, 10:30 = m 5, ... 15:00 = m 23. Hourly 10:15 = m 1 ... 15:15 = m 6.
* Live tool and replay: Yahoo 1-minute bars are stamped by their start; `--asof HH:MM` keeps bars with start < HH:MM; `state_from_bars` uses `end = last_start + 1 - 555`. Consistent with the backtest slots (my replay of 15 Oct reproduces the builder's table T10 to every printed digit: for example 12:30 gives price 3,344.0, P(high in) 0.64, 50% value 3,380.3, 90% value 3,407.6, low 90% value 3,281.4).
* Profile, multiplier c, offsets: other sessions only. 15-minute: **all** other sessions (including later ones), disclosed. Hourly: strictly earlier sessions, first 50 fit-only (I re-implemented that and got identical c paths: min / median / max 0.700 / 0.875 / 0.975).
* "Day-ahead sigma" stand-in (M4): EWMA uses official daily bars of sessions strictly before the date (`ewma_pre_session` sets the value before updating with day t). Fine.
* Truth: official NSE high / low (published about 16:34 IST) or the Yahoo bars' final extreme. The scored session's own final extreme never enters its forecast.

### 2.2 Arithmetic

* Future maximum of (continuous Brownian path to about 15:15) + (one symmetric auction jump): P(max <= b) = P(end <= b) - P(path touched b, end <= b). After the first touch the remaining increments and the jump are independent and symmetric, so P(end <= b | touched b) = 1/2, giving P(end <= b) - (1 - Phi(b/s_c)) = Phi(b/sigma_W) + Phi(b/s_c) - 1. Correct. The low is the mirror image with the same F. The pinball loss summed over the symmetric 9-level grid is the same for the mirrored low.
* `quantile_forecast` takes max(running extreme, c * base quantile); scaling c multiplies s_c and s_J together, so the base quantiles scale linearly (I used that). Monotone across levels.
* Offset convolution (`conv_quantiles`): official high = Yahoo final high + delta (delta >= 0 drawn from the other sessions), and the CDF is averaged over deltas with the correct log conversions for high and low. Same as mine.
* Rupee misses: the report's "Rs" miss is `price_now * |log difference|`, not the simple rupee difference. They differ by at most Rs 0.35 in the means (for example 09:45 high 19.69 vs 20.04, low 22.21 vs 21.89) and by nothing in the medians. Immaterial, but the table is "log difference x price now".
* **Pinball "in rupees" is not rupees**: `RS = 3400` converts a log loss at a fixed price of Rs 3,400 (line 50), for every window. In the hourly Validation window the stock actually traded around Rs 1,900 (bonus-adjusted) and in Final around Rs 3,000. Relative differences (the percentages and the Diebold-Mariano tests) are unaffected; the absolute "Rs" level of the pinball tables should be called "log loss x 3,400". The report never says so.
* Bonus-adjusted vs raw: `bse_daily.csv` OHLC are **as traded** (2025-05-23: open 2,358 after 7,305 the day before; only `prev` is adjusted), so the builder is right that the task note "prices are bonus-adjusted in the processed history" is true for `prev` only. The model uses within-day log ratios only, so this is harmless; the hourly Yahoo bars are divided by 3 before 23 May 2025 and the builder rescales with a factor `kf` only for the offset tables.
* Short side: sign handling correct in `estimate`, `conv_quantiles`, `extension_probs`, `words`.
* Holm implementation correct (step-down with running maximum). Diebold-Mariano (Harvey-Leybourne-Newbold, Bartlett weights) equals my own implementation (M1c vs M1: p = 0.00008 mine, 0.0001 reported).

## 3. Findings that change what can be said

### 3.1 "The time-of-day profile earns its keep only in the hourly sample (+1.6%, p < 0.001)" is an artefact

The "constant variance rate" benchmark B3 gives **every bar the same variance**. In the hourly file six bars are 60 minutes long but the seventh (15:15-15:30, the closing print) is 15 minutes, so B3 gives the closing jump one seventh of the day's variance instead of about 4%. That is not a constant variance rate, it is a mis-specified model, and it loses mostly because of the last bar. With a proper constant rate I get (hourly walk-forward, same multiplier calibration, same targets):

| hourly window | M1 (profile) | B3 as built | constant per clock minute | flat over the six hourly bars, jump variance kept |
|---|---|---|---|---|
| Validation, n = 123 | 2.691 | 2.720 (+1.1%) | 2.672 (**-0.7%**, profile worse, p that profile is better 0.75) | 2.697 (+0.2%, p 0.40) |
| Final, n = 306 | 2.304 | 2.341 (+1.6%, p 0.0001) | 2.309 (**+0.2%, p 0.18**) | 2.316 (+0.5%, p 0.019, Holm 0.03 in the B1,B2,B4,flat family) |
| post-auction, n = 43 | 2.762 | 2.828 (+2.4%) | 2.753 (-0.3%) | 2.747 (-0.5%) |

(values = log loss x 3,400 averaged over sessions; percentages = benchmark minus M1.) So the profile is worth at most 0.5% of pinball loss (about 0.01 of 2.3), and 0.2% / not significant against a proper constant-rate model. The honest sentence is: **"the time-of-day profile has not been shown to matter in either sample."** The 15-minute result (constant rate nominally better, -1.1%) and the post-hoc B3c result (0.7% better than M1c) point the same way. Report section 1 item 4 and section 5 item 4 must be rewritten; the numbers-to-quote section did not use it (good).

Also: the verdict "B1 (price stays) is far worse everywhere, so the model adds real information" rests on a zero-width forecast that nobody would use. The meaningful comparison is B2 (unconditional empirical quantiles): M1 beats it clearly only in the hourly sample (+18% Final, p < 0.001), and **not** in the 15-minute sample (official target +4.4%, raw p 0.19, Holm 0.58; Yahoo target +10.3%, raw p 0.041 = my 0.0414, Holm 0.12).

### 3.2 Uncertainty is stated at one standard error

"+-8 points (50% band) / +-5 points (90% band) from sampling alone" are about 1 standard error of a binomial with n = 39 (0.080 and 0.048). A 95% half-width is about +-16 and +-9 points per checkpoint cell. The pooled figures have a session-cluster-bootstrap 95% interval of [41, 65] and [46, 68] (50% level) and [80, 95] and [80, 94] (90% level) (mine: 42-65, 45-68, 79-95, 80-94). The sentence the tool prints with every call ("...held 54% / 57% ... 88% / 88% (effective sample about 39 sessions, so +-8 points on the first and +-5 on the second...)") therefore makes the pooled numbers look more certain than the report's own bootstrap does. Replace by the bootstrap intervals.

### 3.3 Hourly Yahoo-vs-NSE table (T2, rows "hourly bars, 479 sessions" and the tail statements)

The 146 sessions before the 23 May 2025 bonus are multiplied by 3 ("Rs as traded"), so the pooled hourly row is not in today's rupees and looks fatter than the 39-session row. In today's rupees (my recomputation, n = 479): NSE high minus Yahoo high mean 0.92, median 0.2, p90 2.0, p95 3.1; Yahoo low minus NSE low mean 1.23, median 0.43, p90 3.1, p95 5.3; maximum unchanged (46.4 on 4 Jul 2025, 54.7 on 18 Jun 2025). Post-bonus sessions only (n = 333): high p95 4.2, p99 15.2; low p95 5.4, p99 10.6. NSE high more than Rs 5 above Yahoo's in 14 of 333 sessions (4.2%), low in 19 of 333 (5.7%). Yahoo's extreme was beyond the NSE one in 3 sessions of 479 (up to Rs 12.8). Hence:
* "up to about Rs 4 in INPUT_AUDIT.md" vs 5.3 / 4.5 in 39 sessions: it is a larger sample (a maximum grows with n), not a real contradiction; the 95th percentiles (4.0 / 3.9 in 39 sessions; 4.2 / 5.4 in 333) are consistent. The "strongly contradicts for the hourly tail" wording is too strong.
* But the tail beyond the 95th percentile is **fatter than the 39 sessions show**, including inside the post-auction regime: 17 Aug 2026 (+Rs 30.4) and 12 Aug 2026 (+Rs 10.9) fall just before the 15-minute sample starts on 18 Aug. The "19 times in 20" value is fine; anything more extreme than that is not covered.
* "The Yahoo running high is a floor / It can not end below Rs X" (printed by the tool) holds in 39 of 39 sessions but failed in 3 of 479 hourly sessions. Say "has not ended below it in 39 sessions".

### 3.4 Two printed phrases are not validated and do not hold up in my test

Both are on the Yahoo basis, 15-minute sample, leave-one-out, same states as the builder (8 checkpoints x 39 sessions):

| printed phrase | what I measured |
|---|---|
| "Chance the high / low is pushed at least Rs 5 / 10 / 20 / 40" | high: predicted 29.7 / 25.0 / 17.4 / 7.9%, observed 23.7 / 18.6 / 12.8 / 9.9%. Low: predicted 40.3 / 33.9 / 23.4 / 10.4%, observed 34.6 / 25.3 / 15.7 / 9.3%. The tool is 4-9 points too high at Rs 5-20 (cluster 95% intervals of the difference mostly include 0 but lean the same way: for example low, Rs 10: -8.6 points, interval -16.8 to +0.3). The report lists these as "not separately validated"; they are also biased upward. |
| "If it extends, another Rs 7-30 up is typical" (conditional middle half of the extension) | The actual extension fell inside this range in **36% of 80** extension states (high) and **33% of 141** (low), against 50% intended. States are strongly dependent (suggestive, not conclusive), but the direction is the wrong one for a range called typical. Not listed in the report's limits. |

### 3.5 The official opening price is not used and is sometimes the day's extreme

NSE sets the open in the pre-open auction; Yahoo's first bar does not carry it. On gap days the official open can be the day's high or low and lie far outside every Yahoo bar. Example in the data (not in the 39-session sample): 17 Aug 2026 official open 3,390.0, official high 3,390.4, Yahoo hourly high 3,360.0 (gap Rs 30.4); 12 Aug 2026 official open 3,605.0, high 3,605.9, Yahoo high 3,595.0. In the 333 post-bonus hourly sessions the official extreme is within Rs 1 of the official open in 6 of the 14 high gaps above Rs 5 and 4 of the 19 low gaps; the remaining large gaps have other causes I did not trace. In the 39-session sample the official open lay above Yahoo's high in only 3 sessions and below Yahoo's low in only 3, and the official high equals the official open in only 2 of the 25 sessions with a positive high offset (the official low equals it in 2 of 31). The project already reads the official open from the pre-open auction (`src/preopen.py`, final from 09:08) but this tool ignores it, so on a gap-open day every NSE-basis band can be too low (high) or too high (low) by tens of rupees all day. This is not in the report's limits. It does not break the "nine times in ten" figures on average: when I swapped the offset source for 300 strictly earlier post-bonus hourly sessions (current rupees, includes these gap days) the pooled 90% coverage was 86.9% / 88.5% (high / low) instead of 87.8% / 87.5%, and the 50% level 54.5% / 50.6% instead of 53.5% / 57.1%. So the headline coverage is not sensitive to the offset source (the report listed this as untested; it is now tested).

### 3.6 "Read a stated 'is in' probability for the high as a floor"

Verified for stated 30-90%: 15-minute, 167 states, stated 62.5% -> observed 80.8% (my cluster-bootstrap interval for the gap: +7 to +28 points); hourly Final, 918 states, 60.8% -> 72.0% (+6 to +16). Low: 61.4 -> 63.8% (15-minute, 138 states, interval -9 to +14) and 60.7 -> 66.3% (hourly, 830 states). But the "floor" statement fails in the top bin of the 15-minute sample: stated 97.5% -> observed 91.3% (92 states, driven by two sessions, 11 and 29 Sep). The categorical phrase the tool prints ("the high is in (over 99%)") held in all 39 of 39 high states and 33 of 33 low states with stated >= 99.5%, from 19 and 16 sessions. So: floor for 30-90%, not for the 90-100% bin.

### 3.7 Smaller points

* The tool prints numbers at any time of day, including 09:16-09:30, where no calibration exists (calibration and scoring start at the 09:30 boundary, first scored checkpoint 09:45). Nothing warns the user. The 1-minute descriptive check (n = 7 sessions, which I reproduced: high 90% value hit 80.2% against 91.4% model-implied, low 99.6%) is the only evidence for mid-slot times.
* "Typical miss ... (39 past sessions, out of sample ...)" is printed also for replays of sessions that are among the 39; for a replay it is in-sample. For a future live session it is fine. The stored miss table is also smoothed over three neighbouring slot boundaries, so the live line differs by a few tenths of a rupee from the report's unsmoothed table.
* "Fitted c is not stable" (1.0 vs 0.875): true; effect is small (M0 vs M1 -0.1% in the 15-minute sample).
* The pre-fixed section's claim of being written before any result cannot be verified from git (one checkpoint commit, 15 Oct 17:13 UTC). The builder's own leak test (wipe the scored session's final extremes) cannot fail by construction because that session is excluded from its own calibration; my truncation test is the meaningful one.
* M1c is post-hoc (added after the plain Yahoo bands failed at 15:00). It is flagged as such everywhere. It is one fix, tried alongside M1+off (worse); I do not count it as a hidden search.

## 4. Independent recomputation: report value vs mine

| claim | builder | mine | difference |
|---|---|---|---|
| sessions 39; with 15:15 bar 31; without 8 | 39 / 31 / 8 | 39 / 31 / 8 | 0 |
| NSE high minus Yahoo high (n 39): mean / median / p90 / p95 / max | 0.89 / 0.20 / 2.62 / 4.00 / 5.3 | 0.887 / 0.20 / 2.62 / 4.00 / 5.30 | 0 |
| Yahoo low minus NSE low (n 39) | 1.05 / 0.70 / 2.70 / 3.93 / 4.5 | 1.051 / 0.70 / 2.70 / 3.93 / 4.50 | 0 |
| never reversed beyond float noise (39) | yes | yes (min -0.00005) | 0 |
| 1-minute offsets (7 sessions) high mean / max, low mean / max | 0.66 / 2.3, 0.37 / 1.5 | 0.66 / 2.3, 0.37 / 1.5 | 0 |
| 15 Oct: Yahoo 1-minute high / low vs NSE | 3,445.0 / 3,315.2, diff 0.0 | same | 0 |
| "stays" mean miss, 09:45 high / low (log x price) | 19.7 / 22.2 | 19.69 / 22.21 | 0.01 |
| "stays" mean miss, 12:30 | 9.4 / 14.9 | 9.45 / 14.92 | 0.01 |
| "stays" median miss, 12:30 | 1.4 / 4.1 | 1.39 / 4.12 | 0.01 |
| "stays" mean miss, 14:00 / 15:00 (high, low) | 6.7, 5.3 / 2.7, 2.4 | 6.72, 5.26 / 2.70, 2.42 | <= 0.04 |
| pinball B1, official target (n 39) | 5.79 | 5.786 | 0.004 |
| pinball B2 / M1 / M1c, official | 3.29 / 3.15 / 3.05 | 3.294 / 3.154 / 3.049 | <= 0.005 |
| M1c vs M1 | -3.4%, DM p 0.0001 | -3.4%, p 0.00008 | 0 |
| M1 vs B2, Yahoo target | +10.3%, raw p 0.041 | +10.3%, p 0.0414 | 0 |
| fitted c, 15-minute LOO, Yahoo fit min / median / max | 1.000 / 1.025 / 1.075 | 1.000 / 1.025 / 1.075 | 0 |
| fitted c, official fit | 1.050 / 1.075 / 1.125 | 1.050 / 1.075 / 1.125 | 0 |
| M1c hits at 09:45...15:00, all 32 cells (T4a) | e.g. 23/39, 19/39, 34/39, 36/39 at 09:45 | identical in all 32 | 0 |
| Kupiec cells failing: low 50% 14:00 27/39; low 90% 12:30 31/39 | p 0.015; p 0.051 | 0.0150; 0.0514 | 0 |
| M1c pooled coverage, 50% level high / low | 54% / 57% | 53.5% / 57.1% | 0.5 pt |
| M1c pooled coverage, 90% level high / low | 88% / 88% | 87.8% / 87.5% | 0.2 pt (87.5 rounds up) |
| bootstrap 95% interval, 90% level | [80, 95] / [80, 94] | [79, 95] / [80, 94] | 1 pt (different seed) |
| plain Yahoo bands (c fitted on NSE) at 90% level | 71% / 75%; 46% / 56% at 15:00 | 71.2% / 74.7%; 18/39 and 22/39 | 0 |
| strictly chronological, n = 19, M1c, 50% / 90% level | 54 / 56, 85 / 88 | 53.9 / 55.9, 84.9 / 87.5 | 0.1 pt |
| "high is in" 30-90%, 15-minute | 167 states, 62% -> 81% | 167, 62.5% -> 80.8% | 0 |
| Brier model vs base rate, 15-minute high / low | 0.157 vs 0.183, 0.129 vs 0.225 | same | 0 |
| hourly sessions 479, scored 429 = 123 + 306 (43 post-auction inside Final) | same | same | 0 |
| hourly Final pinball B1 / B2 / B3 / B4 / M0 / M1 | 4.63 / 2.72 / 2.34 / 2.36 / 2.37 / 2.30 | 4.628 / 2.720 / 2.341 / 2.360 / 2.370 / 2.304 | <= 0.005 |
| hourly Final DM p (M1 better): B3 / B4 | 0.000 / 0.014 | 0.0001 / 0.0145 | 0 |
| hourly M6 vs M1: Final -0.6% raw p 0.013; post-auction -1.2% p 0.020 | same | -0.6% p 0.013; -1.2% p 0.020 | 0 |
| hourly M3a: Final -0.8% raw p 0.214 | same | -0.8% p 0.214 | 0 |
| hourly Final coverage cells (e.g. 10:15 high 50%: 204/306) | 204, 218, 224, 239, 253, 281 | same | 0 |
| hourly "high is in" 30-90%, Final | 918 states, 61% -> 72% | 918, 60.8% -> 72.0% | 0 |
| Holm for M6, hourly Final | 0.121 | 0.121 | 0 |
| 15 Oct replay table T10 (8 checkpoints, P(in), 50% / 90% values) | e.g. 09:45: 0.13, 3,390.9, 3,441.7 | same to the decimal in all 8 | 0 |
| 1-minute check: high 90% hit 0.80, nominal 0.91; low 1.00 / 0.92 | same | 0.802 / 0.914; 0.996 / 0.916 | 0 |
| jump on 15 Oct starts at 13:33-13:34 (+3.1% to 3,445.0 at 14:04), low 3,315.2 at 09:16 | same | same | 0 |
| 1-minute vs 15-minute bars (173 bars) | max difference 0.00 | 0.0001 | 0 |
| `--backtest` re-run in an isolated copy | n/a | 15 of 15 CSVs byte-identical, JSON identical except timestamps | 0 |

## 5. CLI run as a user (all with `--nosave` so no repo file changed; checksums of the log, bar cache and params file before and after are equal)

| case | command (clock override where needed) | result |
|---|---|---|
| Saturday | `--now "2026-10-17 10:00"` | clear message ("weekend ... use --replay"). But it first tries Yahoo, so with Yahoo unreachable the user sees "Could not fetch Yahoo..." and waits 13 s before the weekend message. |
| before 09:15 | `--now "2026-10-16 08:30"` | clear message, same 13 s delay |
| weekday, no bars yet / holiday | `--now "2026-10-16 10:00"` | "No Yahoo bars for today ... holiday, or the feed has not started yet. Last session in the data: 2026-10-15" |
| after the close | `--now "2026-10-15 16:00"` and `22:00` | "Session complete ... NSE figure expected at 3,445.2 (9 times in 10 between 3,445.0 and 3,448.1)"; warns that cached bars are used if Yahoo is down. Correct and readable. |
| API 429, plain-text body and JSON error body (fake curl) | Yahoo mocked | both fall back to the cache with "Yahoo could not be reached ... not live" after 13 s of back-off; no crash |
| flaky feed (two 429s, then a valid Yahoo-format JSON on query1) | mocked | succeeds on retry in 1.7 s, same numbers as the replay within rounding (63% vs 64% high in; 3,409.1 vs 3,407.6) |
| mid-session at 12:30 with a valid feed | mocked from the builder's own bars | prints the full plain-words estimate |
| `--asof` 09:16, 09:20, 12:30, 15:10, 15:20, 15:29, 15:31 | replay | all run; 15:20 reports "in (over 99%)"; 15:29 and later report "session complete". 09:16 and 09:20 print confident numbers (for example "86% chance of a new high ... another Rs 17-65") with no warning that nothing was validated that early. |
| `--replay`, `--date 2026-10-09 --asof 11:00` | replay | run |

Readability: mostly plain words, but every call repeats a 90-word Yahoo-vs-NSE paragraph and ends with a 70-word calibration note full of jargon ("volatility multiplier c", "leave-one-session-out", "effective sample", "8 checkpoints each, strongly dependent"). A trader needs: price now, running high / low, chance the high is in, the 50% / 90% values on the NSE basis, typical miss in rupees, one caution line. Not verified by me: the real Yahoo response (I did not call it); the parse of Yahoo's format is the project's existing `rows_1m`, exercised here only through a mock built from the builder's cached bars.

Other behaviours worth knowing. Tested with a mocked feed that ends at 15:14 (closing print not delivered): at 15:31 the tool says "At 15:15 IST ... 15 min to the close" (the session ended at 15:30, the data is 16 minutes old, no stale-data warning because the fetch itself worked); at 15:36 it says "Session complete. Last price (the closing print) Rs 3,425.7" although that is the 15:14 price, not the print (official close 3,428.0), with the explanation only in the last paragraph ("the closing-auction print is not in the Yahoo feed yet"). From reading the code (not run): if Yahoo is down mid-session the cache is used with a warning, but "minutes to close" and "At HH:MM" are those of the last cached bar, not of the clock.

## 6. Claim audit (sentences with a number, "beats", "better", "improvement")

* Section 1 item 1 (offsets): verified. Item 2 (plain Yahoo bands 71% / 75%; M1c 88% / 88%, intervals, one failing cell): verified. Item 3 (no variant beats M1 after Holm): verified for the 9-variant family in each sample (best Holm 0.12, M6 hourly Final). Note the Holm family is per sample and window; across 5 columns M6 has three raw p below 0.05 (0.046, 0.013, 0.020): consistent with "not established", and I agree it should not be adopted.
* Item 4 (profile earns its keep in the hourly sample): **not supported** (3.1).
* Item 5 ("high is in" conservative): verified for 30-90% (3.6).
* Item 6 (typical miss in rupees): verified; it is the model-free "stays" column. These are the user-useful numbers.
* Item 7 (15 Oct replay: high above the 90% value at 4 of 8 checkpoints; low inside at 8 of 8): verified; one session, illustration only, as the report says.
* Section 4.2 verdict "B1 ... the model adds real information": overreach (3.1). "M1c ... DM p = 0.0001": numerically right; it is a correction of the measurement basis chosen after seeing the failure, not a validated model improvement; the report says post-hoc.
* Section 7 "+-8 / +-5 points": understated (3.2). Section 7 omits the gap-open case (3.5), the unvalidated phrases (3.4) and the pre-09:45 use (3.7).
* Contradictions with earlier project statements: the report lists four. I agree with the direction on all, with these changes: the INPUT_AUDIT "up to about Rs 4" is a small-sample maximum, not a refutation (3.3); the sentence that `live_nowcast.py` / `FORECAST_REPORT_V2.md` "treat the Yahoo high/low as the day's range" is fair for the live nowcast, which prints "day range so far" from Yahoo without the NSE note, and not for V2, which states the Rs 4.0 / 4.2 gaps. I found no further contradiction with `FORECAST_REPORT_V2.md` (its first-hour-variance finding is the same shape as the profile used here).
* Sample sizes sit next to the claims everywhere I looked. Windows: no Development window (hourly file starts 16 Oct 2024); Validation n = 123, Final n = 306, post-auction n = 43 (hourly) and 39 (15-minute): all correct.

## 7. What the lead may quote, must correct, must not quote

**May quote as they stand** (independently reproduced; always with the n):
1. Yahoo vs NSE gap, 39 sessions 18 Aug-15 Oct 2026: NSE high above Yahoo's by Rs 0.2 median / 0.89 mean / 2.62 (90th percentile) / 4.0 (95th) / 5.3 max; NSE low below Yahoo's by Rs 0.7 / 1.05 / 2.7 / 3.93 / 4.5; never reversed in these 39. 1-minute bars, 7 sessions: up to Rs 2.3 / 1.5. 15 Oct: Rs 0.0 / 0.0. (Add the tail caveat in 3.3.)
2. Typical gap between the final NSE extreme and the running one (39 sessions, mean / median, high | low): 09:45 Rs 19.7 / 4.0 | 22.2 / 7.2; 10:30 15.8 / 2.5 | 18.7 / 5.5; 11:30 13.3 / 1.4 | 17.0 / 4.3; 12:30 9.4 / 1.4 | 14.9 / 4.1; 13:15 8.7 / 0.8 | 12.1 / 2.6; 14:00 6.7 / 0.7 | 5.3 / 1.8; 14:30 4.2 / 0.4 | 4.3 / 1.5; 15:00 2.7 / 0.3 | 2.4 / 0.8. Say that these are averages over 39 sessions and dominated by a few big days.
3. Plain Yahoo extremes used as the NSE figure fail: the "nine times in ten" value held 71% (high) and 75% (low) of the time, and 46% / 56% at 15:00 (39 sessions x 8 times).
4. With the measured gap added (M1c, leave-one-out, post-hoc fix): "half the time" held 54% / 57% (95% interval 41-65 / 46-68), "nine times in ten" held 88% / 88% (80-95 / 80-94); strictly chronological, 19 sessions: 85% / 88%. One of 32 cells fails a Kupiec test (low side, "half the time", 14:00: 27 of 39).
5. "The high is probably in" probabilities for the **high** are conservative when the tool says 30-90% (stated 62% -> in 81%, 167 states from 38 sessions; hourly stated 61% -> 72%, 918 states, 306 sessions). The low is about right.
6. Nothing tried (realised volatility so far, range so far, day-ahead EWMA, per-level multiplier, time-bucket multiplier) improved on the base model after Holm; best Holm 0.12.
7. 15 Oct replay facts and the Rs 30-plus jump from 13:33.

**Must be corrected (corrected value):**
* "Profile beats constant variance by 1.6% (p < 0.001)" -> **0.2% (p 0.18) against a constant rate per clock minute; 0.5% (raw p 0.019, Holm 0.03) if the jump variance is kept; not significant or economically relevant. In the 39-session sample the constant-rate model is nominally better.**
* "+-8 / +-5 points from sampling alone" -> use the bootstrap 95% intervals above (+-12 / +-7 pooled; about +-16 / +-9 per checkpoint cell).
* Hourly offsets "Rs as traded" row -> today's rupees: high mean 0.92 / p95 3.1; low mean 1.23 / p95 5.3 (n 479); post-bonus n 333: p99 15.2 / 10.6; 4.2% / 5.7% of sessions above Rs 5; max 46.4 / 54.7.
* "It can not end below the running high" -> "has not in 39 sessions" (3 of 479 hourly sessions had Yahoo beyond NSE, up to Rs 12.8).
* "Chance of at least Rs 5 / 10 / 20 / 40": observed was 4-9 points below the stated figure at Rs 5-20 (3.4); do not present as calibrated.
* "Pinball loss in rupees" -> "log loss x 3,400".
* "Typical miss ... out of sample" -> true only for a session that is not one of the 39.

**Must not be quoted:**
* The "if it extends, another Rs X-Y is typical" ranges (they contained the real extension in 33-36% of cases, intended 50%).
* Anything the tool prints before about 09:45, and mid-slot figures as validated (n = 7 sessions).
* The hourly-sample "profile matters" claim; "B1 shows the model adds information".
* Any profit or trading claim (none was tested) and any use of this tool as the Fri 16 Oct high / low forecast: it does not produce one before the open.
* NSE-basis bands on a gap-open day without checking the official open against the first bars (3.5).

## 8. Suggested fixes for the builder (cheap)

1. Rebuild B3 as variance proportional to clock time and re-report; delete the hourly "profile earns its keep" sentence.
2. Print bootstrap intervals, not +-8 / +-5; shorten the call output.
3. Add the official open (`src/preopen.py`, or the daily file after the fact) to the running high / low and re-run the offset table; state the gap-open tail.
4. Drop or caveat the "typical" extension range and the "chance of at least Rs d" lines until calibrated (the empirical conditional distribution of the extension, from the same leave-one-out states, would be the simple replacement).
5. Refuse or warn before 09:45; check the clock before fetching (weekend / before open) so no 13-second Yahoo retry is needed; fix the "out of sample" and "can not" wording; label the pinball scale.

## 9. Commands to reproduce each number (scratch scripts are in the scratchpad; all read only repo data files and write only to the scratchpad)

Directory `S=/tmp/claude-0/-home-user-pred-18/01384b6e-cd11-5bbc-b7f5-2dd03125e5eb/scratchpad/vB`; run each from `$S`.

```
python3 r1.py     # sections 4: 39 sessions, Yahoo-vs-NSE offsets, "stays" misses (mean/median, log x price and direct Rs)
python3 r2.py     # nested leave-one-out profile and multiplier c (Yahoo and official target) -> loo.pkl   (c table)
python3 r3.py     # M1, M1c quantiles (offset convolution)                                                   -> Q15.pkl
python3 r4.py     # B1, B2, M1, M1c pinball, DM, per-checkpoint hits, Kupiec, pooled coverage, bootstrap, plain-Yahoo coverage
python3 r5.py     # strictly chronological 15-minute check (n = 19)
python3 r6.py     # "high/low already in" reliability (15-minute) with cluster bootstrap
python3 r7.py     # hourly walk-forward: M0, M1, B1-B4, plus my constant-rate benchmarks (per clock minute, flat-six)   -> hourly.pkl
python3 r8.py     # hourly Final per-checkpoint hits and collapsed-band shares
python3 r9.py     # hourly "already in" reliability
python3 r10.py    # hourly Yahoo-vs-NSE offsets in today's rupees, outliers, hourly vs 15-minute extremes
python3 r11.py    # hourly M6 and M3a
python3 r12.py    # calibration of "chance of at least Rs d" and of the "typical extension" range (3.4)
python3 r13.py    # 1-minute descriptive check (7 sessions, 5-minute marks)
python3 r14.py    # sensitivity of M1c coverage to the offset source (300 earlier hourly sessions)
```
Gap-open analysis (3.5) and top-bin reliability (3.6) were short inline Python on the same helpers (`mine.py`); the gap-open script is reproduced by the `official()` / `loadhourly()` loaders in `mine.py` (compare official open vs Yahoo hourly high / low on the 333 sessions from 2025-05-23).

Report-vs-file comparisons (T3a, T3b, T4a-e, T9, T2, T5): short inline Python parsing the markdown tables of `research/hl/B_liveintraday.md` and comparing to `results/live_hl_backtest_variants.csv`, `live_hl_backtest_coverage_checkpoints.csv`, `live_hl_miss_by_slot_15min.csv`, `live_hl_offsets_summary.json`, `live_hl_backtest_coverage_pooled.csv`.

Builder reproducibility and leak test (isolated copy, repo untouched):
```
mkdir -p $S/repocopy/{data/processed,results,docs}; cp -r /home/user/pred_18/src $S/repocopy/src
cp /home/user/pred_18/data/processed/{bse_daily,bse_daily_extra,intraday_union_15m,intraday_extra_15m}.csv $S/repocopy/data/processed/
cp /home/user/pred_18/results/live_hl_bars_1m.csv $S/repocopy/results/
cd $S/repocopy && python3 src/live_highlow.py --backtest --hourly /tmp/claude-0/-home-user-pred-18/01384b6e-cd11-5bbc-b7f5-2dd03125e5eb/scratchpad/h60_BSE.NS.json     # 77 s; then cmp each results/live_hl_*.csv with /home/user/pred_18/results/
cd $S/repocopy && python3 src/live_highlow.py --selftest        # closed form vs Monte-Carlo, state check, no-leak
cd $S/repocopy && python3 leak_test.py                           # my stronger truncation leak test
```
CLI cases (no network: dead proxy; `--nosave` everywhere):
```
cd /home/user/pred_18 && export HTTPS_PROXY=http://127.0.0.1:9 https_proxy=http://127.0.0.1:9 HTTP_PROXY=http://127.0.0.1:9 http_proxy=http://127.0.0.1:9 ALL_PROXY=http://127.0.0.1:9
python3 src/live_highlow.py --nosave --now "2026-10-17 10:00"    # weekend
python3 src/live_highlow.py --nosave --now "2026-10-16 08:30"    # before open
python3 src/live_highlow.py --nosave --now "2026-10-16 10:00"    # no bars today
python3 src/live_highlow.py --nosave --now "2026-10-15 16:00"    # after close
python3 src/live_highlow.py --nosave --asof 09:16 | 09:20 | 12:30 | 15:10 | 15:20 | 15:29 | 15:31
python3 src/live_highlow.py --replay --nosave ; python3 src/live_highlow.py --nosave --date 2026-10-09 --asof 11:00
# Yahoo mocks: fake curl in $S/fakebin/curl (MODE=429text | 429json | flaky | ok, feed = $S/fake_1230.json built from results/live_hl_bars_1m.csv)
V=$S; echo 0 > $V/fake_counter; PATH=$V/fakebin:$PATH MODE=flaky python3 src/live_highlow.py --nosave --now "2026-10-15 12:30"
```
