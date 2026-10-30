# Independent verification: workstream "events" (research/v2/06_event_reactions_and_breaks.md)

Verifier scope: re-implement the key numbers from `data/processed/bse_daily.csv` and `index_daily.csv` without importing or copying the analyst's code, then read the code only to diagnose differences, check look-ahead, definition drift, multiple testing, effective n, validation labels, report-vs-JSON consistency and the break claims. My scripts are in `/tmp/claude-0/-home-user-pred-18/01384b6e-cd11-5bbc-b7f5-2dd03125e5eb/scratchpad/v/` (t1..t9.py). I edited none of the analyst's files and ran no git commands.

## 0. Cutoff exposure (read this first)

* Only rows dated <= 2026-10-13 were used. `bse_daily.csv` ends 2026-10-13 and `index_daily.csv` ends 2026-10-12; every script filters `index <= 2026-10-13` explicitly.
* I did not open `results/forecast_score_2026-10-14*.json`, `results/forecast_record_2026-10-14_v2.json`, `data/raw/udiff/20261014.zip`, `data/processed/intraday_union_15m.csv`, `data/raw/macro`, or any 14/15 Oct price, volume or headline. I ran no fetch scripts and used no web tools.
* I read only the `events` key of the scratchpad `done_results.json` (not the other workstreams).
* No exposure to post-cutoff content. Nothing in this verification was influenced by it.
* The analyst's code asserts all inputs are <= 2026-10-13 (events.py line 401 and 1017). The JSON follow-up block has no `error` key, so the assertion on the intraday union file passed. The latest intraday date in the output is 2026-09-18. `events.py` SHA-256 equals the hash stored in `events.json` (`41001d33...`), so the reported run is the code on disk. Note that the run timestamps (07:54-07:55 UTC on 14 Oct) fall inside the 14 Oct session on the sandbox clock; I found no evidence that this mattered, because the inputs are asserted and the output contains nothing dated after 13 Oct.

## 1. Re-implementation results (analyst value -> mine)

| # | Claim | Reported | Mine | Verdict |
|---|---|---|---|---|
| 1 | Per-event R0, G0, I0, z0 (z = R / RMS of prior 60 sessions), turnover multiple (day-0 / mean of prior 20), all 45 events | table 2.1 | max abs difference 0.005 (rounding) on every column; D5 also matches (e.g. E08 -14.63, T01 +11.66) | confirmed |
| 2 | Ordinary pool: n, mean abs z, RMS z, median, share >=1.5, geo turnover multiple | 1702; 0.7514; 1.070; 0.527; 12.6%; 0.835 | 1702; 0.7514; 1.0702; 0.5275; 12.57%; 0.8348 | confirmed |
| 3 | Mean abs z0: NE 1.775, NE_sched 1.266, NE_unsched 2.030, EARN7 1.304, EARN10 1.390, ANALYST 1.250 | as left | identical to 3 decimals | confirmed |
| 4 | Raw p vs pool: EARN7 0.0471, NE_sched 0.0386, EARN10 0.0151 | as left | 0.0458, 0.0385, 0.0141 (200k-300k draws; Monte Carlo noise) | confirmed |
| 5 | Volume multiple NE 1.78x (median 1.69x), EARN7 2.48x | as left | 1.785, 1.689, 2.479 | confirmed |
| 6 | Sign rule: 20 signed (13 neg, 7 pos), 14 hits, mean sign*R0 +4.157%, perm p 0.0015, boot CI [1.76, 6.55], hit-rate null mean 48.6% | as left | 14/20; +4.157%; one-sided perm p 0.0015; CI [1.89, 6.58]; null 48.55%; hit p 0.058 one-sided | confirmed |
| 7 | Timing split: 12/14 hits and mean sign*R0 +5.85% for dossier-dated vs 2/6 and +0.21% documented; Fisher p 0.0374 | as left | identical, Fisher 0.03741 | confirmed |
| 8 | Chronological halves of signed set +6.06% then +2.25% | as left | +6.06%, +2.25% | confirmed |
| 9 | Earnings: R0 positive 3/7, mean abs R0 3.88%, sign agreement 6/7 with exact p 0.1429, Spearman rev +0.179 (p 0.713), EPS +0.10 (n=5, p 0.95), QoQ 0.00 (p 1.0), YoY +0.162 (p 0.729); power n=7 0.16/0.34/0.51/0.74/0.87, n=5 0.04/0.08/0.14/0.23/0.38 | as left | exact permutations identical; power 0.163/0.333/0.504/0.729/0.877 and 0.040/0.085/0.127/0.230/0.369 | confirmed (inputs, the vendor surprises and PAT growth, are inherited from the dossier and research/v2/01, not re-sourced by me) |
| 10 | Follow-through: pool of large days n=214, mean F +0.80, 60% continuation; events n=18 F +0.16, 50%; 9 uncontaminated events F +0.70 | as left | 214; +0.799; 59.8%; 18; +0.159; 50%; 9; +0.699 | confirmed |
| 11 | Unscheduled regulatory abs z quartiles 1.27/2.02/2.96; 60-session RMS 2.153% | as left | 1.27/2.02/2.96; 2.1533% | confirmed |
| 12 | Segment descriptives (RMS, median G, share G>0, share G==0, geo turnover) for B1..B9 | table 5.1 | identical, e.g. B2 turnover 271 -> 1515 (ln ratio 1.723); B8L share G>0 0.664 -> 0.460, G==0 0.064 -> 0.160, median G 0.224 -> 0.000 | confirmed |
| 13 | Placebo-date rank p for B2_turnover, B8L_pos_gap, B8L_zero_gap, B7L_pos_gap, B6_turnover | 0.00225, 0.0491, 0.0188, 0.1995, 0.7124 | 0.002248 (n=2223), 0.04906, 0.01876, 0.1995, 0.7124 | confirmed exactly |
| 14 | Self-test (GARCH 0.08/0.90, 100/100 windows): block-permutation size 0.39, placebo 0.05; power vs x1.6 step 0.79 / 0.35 | as left | my own simulation (250 reps): size 0.42 / 0.06; power 0.79 / 0.34 | confirmed |
| 15 | Monthly gap table 2025-07..2026-10 (median G, share G>0, Nifty share, zero share, mean R); "BSE above Nifty in 11 of 12 months"; "median G >= 0.2% in 9 of 12" | section 5.5 | all months match; 11/12 and 9/12 confirmed | confirmed |
| 16 | Mixture multipliers m(p) = sqrt(1 + p(Zev^2/Zpool^2 - 1)) with Zev^2 = 5.324, Zpool^2 = 1.145 | 1.053 / 1.244 / 1.447 | arithmetic reproduces; Zev^2 = mean z0^2 of the 18 unscheduled events = 5.3239 | arithmetic confirmed; inputs problematic (section 3) |

The A4 first-run coding bug (sum rather than difference) is disclosed in the report; the final A4 value (+2.13 pp, p 0.058) is the pre-registered statistic.

## 2. Report vs stored JSON

* Parsed all Part A rows (20 matched by regex) and all 66 Part B rows of the report tables against `events.json` registry: n, estimate, raw p, p_block, p_placebo, claim p, Holm-22/54, BH-22/54, Holm-88. No mismatch beyond rounding.
* Recomputed Holm and BH myself for Family A (22), Family B primary (54) and the whole registry (88): maximum difference 1e-16 (Holm) and 5e-9 (BH).
* The counts "block alone flags 8 of 54, placebo 4, both 2" and the lists of registry-wide Holm/BH < 0.05 are right. The single Part B p-value that looks significant after borrowing from Part A (B2_turnover BH-88 0.033) is correctly labelled as borrowed strength.
* Presentation inconsistencies (minor): (a) prose quotes simple percentage moves for 5-6 Oct (+4.39%, +3.94%) while the tables are log returns (R15 +3.87); (b) "6/7 sign agreement, exact p 0.1429" pairs a count with the p-value of a different statistic (mean of sign*R0); the count-based one-sided exact p is 0.114; (c) the sign-rule hit-rate p 0.0590 is one-sided (two-sided 0.071), which the table does mark as "greater".

## 3. Look-ahead, definition drift, selection, tuning

**No look-ahead in any computed predictor.** sigma (prior 60 sessions, shifted), turnover base (prior 20, shifted) and the market-model window [i-260, i-11] all use only earlier data. The control pool excludes event windows using future event dates, which is benign (it only removes event days from the baseline).

**Outcome-informed day-0 assignment is the main design problem (partly disclosed, not carried through).** For 15 of the 27 gated non-earnings events and 14 of the 20 signed events, "day 0" is the session on which the dossier shows the price reaction (`dossier_reaction_date`), so the event date was chosen knowing where the price moved. The analyst applied the timing-evidence split only to the sign rule. Applied to magnitude, it changes the headline:

| subset (non-earnings) | n | mean abs z0 | raw p vs pool |
|---|---|---|---|
| dossier-dated day 0 | 15 | 2.32 | about 2e-6 |
| documented release time (press/timestamp) | 12 | 1.09 | 0.074 |
| documented and scheduled | 8 | 0.99 | 0.17 |
| documented non-earnings plus EARN7 | 19 | 1.17 | 0.018 |
| unscheduled regulatory, dossier-dated / documented | 10 / 4 | 2.47 / 1.30 | n/a |

Welch test dossier vs documented: p 0.0016. The turnover multiple shows the same split (geo 2.56x dossier-dated vs 1.14x documented, p 0.068 for the latter). The report's "selection-light" premium of about 1.3 (1.7x) uses scheduled events and earnings, but the scheduled group itself contains the one dossier-dated Budget day (z 3.46); without it the scheduled mean is 0.99. A defensible selection-light premium is about 1.1-1.3 (1.5-1.7x), significant only when the documented non-earnings events and earnings are pooled (p 0.018, single post-hoc comparison). The report's direction (events larger than ordinary) survives; the size of the Holm-0.0044 headline does not carry the weight the table gives it. The inclusion rule "a price move with cause not found is NOT an event" is itself conditioned on the outcome: 11 sessions with abs z >= 2 in 2024-26 (for example 2024-09-16 z 6.2, 2024-09-18 z 4.5) are unlisted.

**Section 7 widening multipliers inherit that selection.** Using the four unscheduled regulatory events with documented timing (R13, R14, R15, R16: abs z 1.59, 1.16, 1.83, 0.60, the most recent and most on-topic, all CAS/settlement), mean z^2 is 1.90 and the same formula gives m = 1.01 / 1.05 / 1.09 at p = 0.03 / 0.15 / 0.30, against the report's 1.053 / 1.244 / 1.447. n = 4 is far too small to prefer, but the spread shows the recommended x1.18 / x1.37 are not robust. The report calls Zev "selection-biased upward" and p "an assumption", but gives no selection-adjusted alternative. The "embedded base rate of 3%" claim is also an assumption: the 18 listed events cover 608 of the 2,388 sessions in v1's sample (0.75% of sessions if spread over the whole history).

**Definition drift (undisclosed).** The pre-registration docstring defines m(p) = sqrt(1 + p(Zev^2 - 1)) with p grid {0.035, 0.15, 0.30}; the code and report use sqrt(1 + p(Zev^2/Zpool^2 - 1)) with p_base = 18/608 = 0.0296. The post-first-run changelog does not list this change. Effect is small (1.053 vs 1.073 at base) and the new form is arguably more correct, but it is a pre-registration deviation. A1_W2_NE is a poorly specified variant (2-session sum scaled by sqrt 2 against a single-day pool); the note admits this.

**Thresholds and tuning.**
* The abs z >= 1.5 pool threshold and windows were fixed before outcomes; no evidence of tuning there.
* B7L/B8L windows were chosen after the first run (disclosed). Sensitivity of the B8 positive-gap placebo p to the pre-window length (post window fixed at 50 sessions): 40 -> 0.14, 60 -> 0.10, 100 -> 0.12, 120 -> 0.16, 200 -> 0.13, 250 -> 0.049, 300 -> 0.028, 400 -> 0.032, 500 -> 0.032. The effect size is stable (-15 to -24 pp), the p-value is not; 250 is neither the most nor the least favourable choice, so I see no sign of outcome tuning, but the report should have shown this table.
* The B8 and gap cells were fixed after the analyst had seen the v1 gap result (DEVIATIONS #16: share G>0 0.449 vs 0.707). The peeking log says so. These cells are therefore confirmations of an in-sample v1 observation, not independent tests.
* Sign column was typed after reading the reactions (stated). R13/R15/R16 mappings rest on the premise that a settlement-reform reversal helps BSE, but only R14 carries the judgement flag (J). R05 and R16 are coded 0 and so drop out of the signed set (R05 -1.18%, R16 +1.30%; net effect on the hit rate is nil), which is still a degree of freedom.

## 4. Multiple testing and effective n

* Family sizes (22 + 54 + 12 = 88) are counted correctly and the Holm/BH arithmetic is exact. The 88 do not include the group splits reported descriptively (by type, by timing, by set), 9 variant runs, or the choices of EARN7 vs EARN10 and the 5-day window; these are disclosed rather than corrected. The 12 B_sens cells and A2c-by-timing are post-hoc and labelled so.
* A1 events fall on distinct sessions within NE; co-dated pairs (R14/A04, X04/A05) put the same session into NE and ANALYST, so A1_ANALYST (n=5) has 3 independent sessions and is not independent of A1_NE.
* A5 windows overlap; the report flags this and gives the 9 uncontaminated events. The A5a comparison is not like-for-like (pool restricted to abs z >= 1.5, events not), which favours the pool; the conclusion (not found) is unaffected.
* Part B placebo ranks use about 2,100-2,200 heavily overlapping windows, so the effective number of independent placebo windows is of order 20-25; the B2 turnover p of 0.0022 reflects roughly five adjacent placebo dates (the 12-19 Sep 2024 cluster), not 5 independent ones. The p-values are valid relative frequencies but coarse.
* Stationary-bootstrap CIs (mean block 10) for highly persistent series (turnover, 23-50 session windows) are probably somewhat narrow; the report notes low power.

## 5. Validation labels

* No finding is labelled `validated_out_of_sample`, and none should be: no chronological walk-forward with fixed rules against a benchmark was run in this workstream (the chronological halves are a descriptive check, correctly described so). The code's status rule never assigns it. Confirmed.
* `descriptive_only` on A1_NE, A8_NE, A8_EARN7, A2a is acceptable under the brief (Holm < 0.05, in-sample), with the caveat in section 3 that A1_NE and A8_NE are largely driven by outcome-dated events.
* Two labels look generous: the Section 7 scenario finding is `descriptive_only` in the returned structure, but it is an arithmetic scenario with an assumed p and a selection-biased Zev; `untested` is the accurate label. "Historical relationships likely invalid on 14 Oct" is `descriptive_only` while the break cells beneath it are `not_found`; that is defensible only because the text hedges (and my own sup tests below are borderline).
* `not_found` for the Part B cells correctly means "not detectable with these windows" (35% power for a x1.6 volatility step), which the report states.

## 6. Independent tests of the break / regime claims

The report claims no break is established family-wise; it nevertheless says the gap premium and the Nifty relationship are "likely invalid on 14 Oct". I tested those two with a different method (unknown-date supremum statistics with block-bootstrap nulls drawn from pre-2026 history). Both were chosen after seeing the analyst's output, so they are confirmatory and carry limited weight; with a correction for these two post-hoc looks (x2) they sit around 0.03-0.08.

1. **Share of positive gaps.** Two-proportion test 166/250 vs 23/50: Fisher p 0.0097, z-test p 0.0064 (naive; ignores dependence and date choice). Sup-z over candidate break dates in 2026: best date 2026-07-13 (z 3.68), block-bootstrap p 0.004 (iid) / 0.015 (block 5) / 0.029 (block 10). BSE excess over the Nifty (paired indicator): 15.2 pp -> 0.0 pp, Welch p 0.097. Historical context: the rolling-50-session share is now 0.46, the lowest in the sample (previous minimum 0.42 occurs on 2026-09-21; 1st percentile 0.46; full-history share 0.70). So the drop is real in magnitude, nominally significant, but the data place the shift in mid-July, not at the 3 Aug auction date, which agrees with the analyst's "date not identified" conclusion. Verdict: report's `not_found` after correction is a conservative reading; "do not assume a positive median gap" is supported.
2. **Correlation / beta with Nifty 50.** Correlation 0.634 (H1 2026, n=120) vs 0.125 (since 1 Jul, n=72): Fisher z 4.10. 250 sessions pre vs since 3 Aug: 0.510 vs 0.205, Fisher p 0.027. Sup Fisher z over 2026 dates 4.55 at 2026-06-17, block-bootstrap p 0.035-0.0375. Context: the rolling-60 correlation is now 0.19 (18th percentile of history); its long-run median is 0.34 and it has been this low in 2017-19 and 2023-24. The H1 2026 level (0.63) was the unusual one, so "beta 1.4-1.6 / corr 0.5-0.65 no longer safe" is supported, partly as a return to the historical norm. This is a different framing from the report (which attributes part of it to the VWAP/auction measurement change).
3. **Turnover step (B2).** Reproduced (x5.6). But the largest 106/39 turnover step in the sample is at 12-19 Sep 2024 (+1.92 ln), two weeks before the 1 Oct candidate date, and 1 Oct itself ranks 11th of 2,244 windows by absolute effect. The report says the step cannot be attributed to the SEBI measures; it does not note that the maximum precedes the date.
4. **Volatility.** The analyst's claim of a gradual decline rather than a dated step is consistent with their own B4/B5/B7 cells; I did not run a separate test.

## 7. Items I could not verify

* Vendor consensus and EPS surprise figures (Investing.com, TradersUnion, TradingView 20.31), PAT growth rates and release times for the three "pattern" quarters in `data/results_dates.csv`: inherited from the dossiers and research/v2/01; no primary source reachable offline. Only signs and rank order are used by the report, which is the right choice. `unverifiable` stands.
* Event existence, dates and content for the regulatory items rest on dossiers (many single-source); the analyst states they did not open primary documents.

## 8. Overall

Numbers are accurate and reproduce independently; the report is candid about non-blind design, multiple testing and the sign-rule failure; no leakage; no false `validated_out_of_sample`. The material weakness is that the magnitude and volume headlines (and the Section 7 widening factors) are computed on a set whose day-0 was chosen with knowledge of where the price moved, and the analyst's own timing-evidence diagnostic, which collapses the sign result, was not applied to them. When the documented-timing events are separated, the event premium is about 1.1-1.3 abs z (about 1.5-1.7x an ordinary session) and the conditional widening is much smaller than the stated 1.18-1.37. Severity: minor (no wrong numbers; one substantive caveat that should be carried into any use of Section 7).
