# Independent verification: src/live_nowcast.py (live "indicative close" nowcast)

Reviewer: independent agent, read-only on the repo. Scratch code: /tmp/review_scratch/ (indep.py rebuilds everything without importing the author's functions; a1..a14.py are the checks). Network worked (Yahoo fetch succeeded), so the replay was run. Run date 2026-10-15; Yahoo already holds the full 15 Oct session.

Overall severity: **major** (for claims and printed text; the core arithmetic reproduces exactly and the backtest has no self-leak at w=0). Nothing critical.

## 1. Confirmed (re-implemented from the two CSVs, no author imports)

| Item | Author | Mine |
|---|---|---|
| Sessions loaded | 39 (31 with 15:15 bar, 8 without) | 39 / 8 |
| Checkpoints (m=2..23, 22 per session) | 858 | 858 |
| Gaussian cover 50 / 90 / 95 % (w=0) | 63.2 / 90.0 / 94.5 | 63.17 / 89.98 / 94.52 |
| mean abs z | 0.7351 | 0.7351 |
| z quantiles 2.5/5/25/50/75/95/97.5 | -1.613 -1.438 -0.395 0.040 0.546 1.883 3.203 | identical to 4 d.p. |
| w=0.5 / 1.0 cover90 (docstring line 26) | 88.9 / 86.0 | confirmed from author's --backtest output |
| Tightening schedule at 09:20 (Rs 79/73/65/58/42/33/29) | as printed | 1.645*sqrt(sum ev[k:])*3323 reproduces all 7 |
| `--replay` table | results/nowcast_replay_latest.csv | re-run through run_live(False, hhmm): max abs diff 5e-13 |
| Closes | c[24] equals official daily close for all 38 sessions that have one (0 mismatches > Rs 0.06) | 15 Oct has no official row yet (see 3) |

## 2. Look-ahead / leakage

* Evaluated session does NOT leak into its own profile (profile(S[:j]+S[j+1:]), live.py:91-92). With w=0 sigma uses no information from the evaluated session at all. Checkpoint m uses only c[m-1] (bar closing at 09:15+15m) and v_sofar r[:m] (completed bars): correct, no look-ahead.
* LOSO is not chronological: a session's profile includes LATER sessions (and 11 Sep, 29 Sep). A pure walk-forward (expanding window, first 12 sessions as burn-in, 27 sessions / 594 points) gives Gaussian cover 56.6 / 87.4 / 93.3 %, mean|z| 0.895. Label it "leave-one-out, not out-of-time".
* The quoted bands use IN-SAMPLE empirical z-quantiles (line 126-127: `bt = backtest(); zq = bt["z_quantiles"]`). Honest nested check (quantiles recomputed without the held-out session, and those z's built from profiles without it): printed 50% band covers **49.3%**, 90% band **89.0%**, 95% band 94.4%. So the aggregate in-sample leak is small (about -1 pp). BUT:
  * line 133 `calibration_note` reports the coverage of the GAUSSIAN bands (63/90), while lines 127-128 print the EMPIRICAL bands. The note does not describe the printed bands.
  * the 2.5/97.5% quantiles (the `close_95` field) are effectively one session (see 6).
* **Bug (replay look-ahead, up to 1 minute), live_nowcast.py:115.** `df1.t.dt.strftime('%H:%M') <= asof` keeps the 1-minute bar stamped asof; Yahoo stamps are bar START, so that bar closes at asof+1min. `price_then` for "13:15" is the price at ~13:16:00. Difference vs last COMPLETE bar (price at asof:00): 09:45 +2.9, 10:30 0.0, 11:30 -1.3, 12:30 -3.0, 13:15 -2.9, **13:45 +13.2, 14:04 +13.9**, 14:30 +3.3, 15:00 +1.0 Rs (a 15 Oct news spike at 13:34 made 1-minute moves 0.13% sd). The dashboard table (`price_then`, `error_rs`, `inside_90`) inherits this. Fix: `< asof` (or `t <= asof - 1min`). Corrected rows: 90% inside 7/9 (unchanged), 50% inside 2/9 (14:04 flips to inside).
* Minor replay leak (line 126): `backtest()` is called inside run_live and, for a replay of 15 Oct, its z-quantiles include 15 Oct itself (it is in intraday_extra_15m.csv). Effect: q75 0.546 vs 0.513 and q05 -1.438 vs -1.461 without it, i.e. 1-2 Rs. Fix: pass `exclude=today` into backtest.
* Minor (line 108): `prev_official_close()` takes the last row of daily+extra; once 15 Oct is added to bse_daily_extra.csv (build_dashboard_data.py:129-132 expects this) "yesterday's close" becomes today's close and the printed change vs prev close is 0.00%. Fix: last row with index < today.

## 3. Sessions without the 15:15 bar, partial slots, post-close

* The 8 sessions (18 Aug, 24 Aug, 3 Sep, 17 Sep, 22 Sep, 29 Sep, 8 Oct, 9 Oct) have the auction print inside the 15:00 bar (e.g. 29 Sep: 15:00 bar volume 22.5 M, close 3200 = official). `ffill` (line 67) makes r[24] exactly 0 for them and loads the whole 15:00-to-close move into r[23]. Consequences:
  * ev[23] = 2.55e-5 mixes 31 pure 15-minute sessions (2.38e-5) with 8 30-minute ones (3.20e-5); ev[24] = 2.60e-6 is diluted by 8 zeros (undiluted 3.27e-6): sigma of the auction jump understated by 11% (0.161% vs 0.181%).
  * The sum ev[23]+ev[24] (all that matters for m<=23) is only 4% off (2.81e-5 vs 2.71e-5), so **the backtest is essentially unaffected**; the damage is to live bands after 15:00. Fix: estimate ev[24] from the 31 sessions that have the bar and ev[23] likewise, or merge slots 23+24 into one 30-minute block and interpolate.
* Partial slots (`frac`, lines 82, 118): bands are only ever tested at frac=0. Slot variance is not uniform in time. Worst case is the auction window: the print is a single jump at about 15:28, but `(1-frac)*ev[24]` shrinks sigma by a factor of 0.82 at 15:20 and 0.26 at 15:29 (I ran --asof 15:16 / 15:29 --nosave: "typical miss Rs 4", then "Rs 2", 90% band 3,425-3,432). Real 15:15 jump sd is 0.18% = Rs 6.2 (mean abs 0.139%, max 0.46% = Rs 16), 90% band about +/-Rs 10 until the print. At m=24 (15:15, frac 0, 31 sessions) my check gives Gaussian cover90 87%, cover50 48%, mean|z| 0.88, i.e. roughly fine at frac=0 but never tested by the code. Fix: for m>=24 set frac=0 until a bar with the auction volume appears, then collapse.
* m=25 (post-close) is **dead code**: rows_1m keeps slot<25 (<=15:29) so mins<375 always and m<=24; the `m<NB` guard (line 83) never takes the else branch. After the print the script keeps showing "2 min to the close, typical miss Rs 2" instead of "closed at X (unofficial)". m=0,1 (09:15-09:45) and m=24 are also outside the backtest (range(2,24)) yet are printed without caveat (at 09:20 the 90% band is +/-3%).
* **Bug, live_nowcast.py:160 (`refresh`)**: `g.slot.nunique() < 24` admits a half-finished session when run between 15:00 and 15:14 (slots 0-23 exist). It is saved as complete, treated as having no 15:15 bar, and never replaced (`have` is by date) - a permanently wrong close. Fix: require slot 24 present (auction print) and bars after 15:28, or skip `date == today` before 15:31.
* Data note: 15 Oct (the 39th session) is in the calibration sample with close 3428.0 = Yahoo 15:28 print; bse_daily_extra.csv has no 15 Oct row yet, so that close is unofficial (14 Oct, also Yahoo-built, matches the official 3338.0). Three sessions (17 Aug, 2 Sep, 10 Sep) were dropped by the garble test; verify_intraday.md already says 10 Sep's jump was genuine.

## 4. "typical miss = 0.8 sigma price" and tightening schedule

* 0.8 is sqrt(2/pi), the mean-abs of a Gaussian. Empirically mean|z| = 0.735 pooled but varies with time: 0.82 (m2-7), 0.76 (m8-15), 0.66 (m16-21), 0.61 (m22-23; 0.61 at exactly 15:00). So 0.8 overstates the MEAN miss by 9% pooled and 31% at 15:00. For the MEDIAN miss (what "typical" suggests to a reader) median|z| is 0.47 pooled and 0.33-0.38 late, so the label is 1.7x too big pooled and about 2.1x at 15:00. Today: 15:00 row says Rs 14.7, realised miss Rs 10 (one day).
* Schedule arithmetic is correct (reproduced). Caveats: it uses 1.645 symmetric while the printed 90% band is asymmetric [-1.438, +1.883] sigma (mean half-width 1.66, fine); and sigma itself is uncertain: session-bootstrap 95% CI for sigma_remaining is [1.33, 1.78]% at 09:45, [0.87, 1.43]% at 13:15, **[0.29, 0.77]% at 15:00** (point 0.53%), i.e. the Rs 29 half-width at 15:00 could be 16-42.

## 5. Replay (network OK)

Reproduced exactly (5e-13). Issues: the 1-minute look-ahead above; single day (all 9 rows share one outcome, 3428.0); 15 Oct is also inside the calibration sample; 50% band contains the close in 1 of 9 rows as published (2/9 corrected), 90% in 7/9 (misses 12:30, 13:15 before the 13:34 spike: +0.9% in one minute, volume 94k vs 2-4k). Docs/LIVE_TOOLS.md describes this fairly ("a late news spike breaks it") but nine dependent rows are one observation.

## 6. Is the 50% band honest, and where does the skew come from?

* Gaussian +/-0.674 sigma: pooled coverage 63.2% (session-bootstrap 95% CI 52-74%), so too wide on average; by time: 48.7% (m2-7), 61.5% (m8-15), 74.8% (m16-21), 78.2% (m22-23). Too wide late, about right early.
* The PRINTED 50% band is the empirical [q25,q75] = [-0.395, +0.546] sigma, 50% only by construction (nested 49.3%). By time of day it covers **35.9% (m2-7)**, 47.4% (m8-15), 63.2% (m16-21), 61.5% (m22-23). So "half the time" is wrong in both directions through the day; the 90% band covers 88.5 / 88.5 / 91.5 / 96.2%. The calibration note and docs ("50% band wider than needed (63% coverage)") speak of the Gaussian band, not the one printed.
* Skew: the upper 5% tail has 43 points; **22 are 11 Sep** (all 22 of that session's checkpoints have z>=3.59: about +4.5% from 14:30 to the close, genuine, matches the daily bar), 6 are 29 Sep, 6 are 15 Oct, 3 each 7 Oct and 13 Oct, 2 on 21 Sep, 1 on 31 Aug. The 97.5% quantile (3.20) is **entirely 11 Sep**: 22/858 = 2.56% is just above 2.5%; drop that session and it falls to 2.15, drop any other single session and it rises to 3.56-3.83. q95: 1.88 -> 1.80 without 11 Sep; 1.57 without 11 Sep, 29 Sep and 15 Oct, where q95/|q05| = 0.98 (symmetric) and [q25,q75] = [-0.52,+0.49]. The lower 5% tail is spread over 6 sessions. Session-bootstrap 95% CI of the asymmetry q95+q05 is [-0.31, +3.06] (P(<=0)=10%): not distinguishable from symmetric.
* 11 Sep also drives the profile: it is 54% of the sum of squares of the 15:00 slot and 24% of 14:45; without it sigma_remaining at 15:00 is 0.38% instead of 0.53% (-28%), at 14:15 -18%, at 13:15 -8%. One session widens every late-day band by up to ~39% while its own z-excess is then read as upward skew. That is why late-day coverage (96% at 15:00) is high and the right tail heavy.
* "No drift claimed" (docstring): 15:00-to-close mean is +0.18% (t=2.5; +0.13%, t=2.4 without 11 Sep; median +0.04%); the auction print is positive in 20 of 31 sessions (mean +0.05%, t=1.6). Multiple looks, small sample, so not established, but centre=price is not shown to be unbiased.

## 7. Unsupported or false text (from live_nowcast.py output)

1. **Constant "Today has been 1.0x as wild as a typical day"** (lines 85, 131, 151): with W_SCALE=0, scale2 is 1, so the statement prints 1.0x on every run (checked at six times). Real ratios for 15 Oct (sqrt(v_sofar/cum)) were 0.70 (m6), 0.76 (m13), 1.14 (m20), 1.12 (m23). Fix: compute `sqrt(v_sofar/cum[m])` independent of w.
2. "Gaussian 50/90% bands cover 63%/90%" is accurate for Gaussian but misattributed to the printed (empirical) bands (above).
3. "did not improve the test" (line 26/151): coverage is a weak criterion; on mean log-likelihood per checkpoint, w=0.5 is +0.09 nats vs w=0 (session-level SE 0.12), w=1 +0.07 (SE 0.18): inconclusive, not evidence of no gain.
4. "Half the time ..." / "nine times in ten" are time-of-day dependent (above) and rest on 39 sessions.

## 8. How far 39 sessions limits any calibration claim

* The sample is 39 sessions (38 with a confirmed official close) from one 8-week window; the 858 points are 22 overlapping checkpoints per session with mean cross-checkpoint z correlation 0.80, so the effective sample is about the session count (design effect about 18).
* Session-bootstrap 95% CIs: cover50 52-74%, cover90 83-96%, cover95 88-99%; q95 [1.13, 4.27], q97.5 [1.62, 5.00], mean|z| [0.53, 1.02]. Anything between "90% is about right" and "90% is 83%" is compatible with the data. Tail edges (5%, 2.5%) are set by 2 and 1 sessions.
* The z sd is 1.14 (heavy tails, scale mixture): the Gaussian shape is wrong, the pooled 90% hit rate is a coincidence of peakedness offsetting too-small tails. Sigma at 15:00 carries a +/-45% uncertainty from the profile alone.
* Not tested at all: 09:15-09:45, 15:15-15:30, any frac>0 time, chronological out-of-sample use, volatile-regime changes, news days other than those present (11 Sep, 29 Sep index day, 15 Oct).
* Reasonable wording: "descriptive: pooled bands hit about 49%/89% in leave-one-out, with time-of-day swings of 36-63% for the 50% band and heavy single-session influence; a handful more weeks are needed before any number here is more than a rough guide."

## 9. Suggested fixes (one line each)

* live_nowcast.py:115 use `< asof`; :126 exclude today from backtest; :85/:131/:151 compute the true volatility ratio; :132 replace 0.8 by empirical mean|z| per time bucket (0.82 -> 0.61) or call it "average miss" and report median; :133 report nested-LOSO coverage of the printed bands, by time of day; :67/:82 handle slot 24 as a jump with frac=0, estimate ev[23]/ev[24] on the 31 sessions that have the bar; :160 guard refresh; :108 prev close = last row before today; document that close_95 is one session.

Files touched: only this file (and /tmp/review_scratch/). The author's CLI was run only with --backtest, or with --asof ... --nosave; run_live was called with save=False. No log or json written.
