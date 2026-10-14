"""v2 workstream "events": event reactions (Part A) and structural-change tests (Part B) for NSE:BSE (BSE Ltd).

Run:  cd /home/user/pred_18 && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 src/behaviour/events.py        (writes results/behaviour/events.json)
Self-test on SIMULATED data only (no BSE outcome is touched):  ... python3 src/behaviour/events.py --selftest
Reads repo data read-only and fetches NOTHING (information cutoff 2026-10-13 22:00 IST; the 14-Oct-2026 session is unseen; the code asserts
that every input row is dated <= 2026-10-13).  The markdown report research/v2/06_event_reactions_and_breaks.md is written by hand from
events.json.

=====================================================================================================================
PRE-REGISTRATION.  Written BEFORE any event return, abnormal return, volume multiple, break statistic or p-value of this workstream was
computed (file mtime precedes the first execution; the SHA-256 of the file as run is stored in events.json).
THE DESIGN IS NOT BLIND, and this is stated up front: the two dossiers (research/01, research/02) and research/v2/01 print the close-to-close
reaction of most candidate events (results days, the analogue table A1-A15, the news timeline) and I read them before writing this text.
What is fixed ex ante is (i) the event inclusion rule, (ii) the first-tradable-session rule, (iii) the sign rule text, (iv) every statistic,
window, threshold and null distribution below.  Residual contamination risks, stated rather than hidden: sign labels and first-session
assignments were typed by me after having seen those printed reactions, so a sign could have been (unconsciously) nudged toward the outcome;
the event list itself is probably biased toward large moves (the dossier author searched for a cause when the price moved).  Mitigations:
every event carries a `judgement` flag; the unscheduled set (most exposed to selection) is analysed separately from the scheduled set (date
known in advance: results, Budget day, effective dates, central-bank releases); the sign rule is a content rule that deliberately ignores
prior expectations, so it will be WRONG for "less bad than feared" events and that failure is reported, not repaired.

PEEKING LOG (what had been seen before this text was written)
 * docs/V2_BRIEF.md; research/01_company_dossier.md and research/02_regulatory_macro_catalysts.md in full (they contain the reaction of
   each results day P-9/R-3/A13, analogues A1-A15, the B4 timeline with every daily % move 13 Jul-13 Oct 2026, a 5-month price context).
 * data/results_dates.csv; data/corp_actions_verified.csv; docs/DEVIATIONS.md (incl. #16: share of positive gaps 0.449 since 2026-08-03 vs 0.707
   before, median gap 0.000%, 16% exact zeros; #21 caveats).
 * research/v2/01_fundamentals_verification.md sections 1-3 (NSE dissemination times of 10 results, vendor consensus table with the
   next-session R of 8 results, its own magnitude test T1-T5: p = 0.024 raw / 0.118 Holm for |z| of results days; 7 of 8 revenue-surprise
   signs agree with the sign of R) and research/v2/02_news_catalysts_update.md (timing correction: first coverage of the Reuters CAS story is
   5 Oct 20:32 IST, so 5 Oct +4.39% is NOT its reaction).  research/v2/05_intraday_structure.md first 50 lines.  I did NOT open
   results/behaviour/*.json nor research/v2/03; I read the design headers of src/behaviour/pattern_tests.py and linkages.py only.
 * Data-description queries before writing the Part B text: date coverage of every event session in bse_daily/index_daily, session counts of
   the candidate windows, F&O file coverage (first BSE-stock row 20241129), share of exact-zero gaps (117 of 2,338 sessions = 5.0% before
   2026-08-03; 8 of 50 after) and by year.  No volatility, beta or turnover break statistic had been computed.
 * No event return, abnormal return, 5-day return, volume multiple or recovery time had been computed from data before the first run.

---------------------------------------------------------------------------------------------------------------------
PART A  EVENT STUDY
---------------------------------------------------------------------------------------------------------------------
NOTATION  Sessions k = 0..N-1 of src/common.py load_bse() (2017-02-06 .. 2026-10-13, N = 2388).  G, I, R as in V2_BRIEF (R = G + I, prev =
 bonus-adjusted previous kept close).  rN_k = ln(Nifty50 close_k / close_{k-1}) on the same two BSE sessions (NaN if either index row is
 missing: 2026-10-13 has no index row, so the Nifty-based fields of that session are NaN).  GN_k = ln(Nifty open_k / Nifty close_{k-1}),
 IN_k = ln(Nifty close_k / Nifty open_k).  sig_k = sqrt(mean(R_{k-60..k-1}^2))  (zero-mean RMS of the 60 sessions BEFORE k; "trailing vol").
 turnover base T0_k = mean(turnover_cr_{k-20..k-1}) (rupee turnover is corporate-action free; share volume is not).
 CAUTION on the Nifty market model: before 2026-08-03 the BSE close is a 30-minute VWAP, the index close is the 15:30 value, so R and rN are
 non-synchronous before that date (beta biased down, residual noisier); reported as a caveat, not corrected.

EVENT INCLUSION RULE (fixed now).  An item is an event iff (a) it has a calendar date in research/01, research/02, research/v2/01-02
 or data/results_dates.csv, (b) it is about BSE Ltd, exchange/derivatives regulation or competition, the Union Budget, a scheduled central-bank
 release, or the Nifty-50 index, (c) a cause is documented (a price move with "cause not found" is NOT an event), (d) its first tradable
 session lies in the data.  Not invented: no date, time or event outside those documents.  Items with unknown release time are kept in the
 table but are NOT used in the gated tests (`gating = False`).
FIRST-TRADABLE-SESSION RULE.  Day 0 (S*) = the first session whose trading can reflect the item: the same session if it was released
 before/during market hours (09:15-15:30 IST, or a Sunday/Saturday special session), the next trading session if released after 15:30 or on a
 non-trading day.  For `intraday` events day 0 contains pre-event trading (the part before the release cannot be separated: R0 over-states
 nothing but is diluted by pre-event drift; G0 is NOT the news reaction).  For `post_close`/`weekend` events G0 + I0 is the reaction.
 timing_evidence in {timestamp (primary file/filing stamp), press (dated press item), dossier_reaction_date (S* inferred from the date the
 dossier shows the reaction; release time not verified), unknown}.  A fixed 2-session robustness variant W2 = R(S*) + R(S*+1) is
 computed for every event (used only as a robustness variant, see below).
SIGN RULE (written now; applies to non-earnings events; `sign_V`).  From the CONTENT of the item as described in the sources, ignoring
 prior expectations and ignoring the outcome:  +1 = raises expected BSE transaction-charge revenue / removes a threat to it (relief,
 removal or softening of a pending curb, restoration of status quo, forced passive demand [index inclusion announcement], lower
 risk-free/higher risk appetite);  -1 = lowers it or adds a threat (new tax/fee/curb, enforcement against a major derivatives participant,
 curbs mooted by the regulator, more competition/supply of exchange paper [NSE NOC, DRHP], risk-off tightening);  0 = content does not
 determine a direction (timing statement; swap of expiry days; implementation of a previously announced measure; anticipated flows
 already completed).  `judgement = True` marks signs that needed a mapping beyond the plain reading (competition events, index flows,
 "softening of a curb", CPI vs prior print).  Known weakness (accepted): a rule that ignores expectations mislabels "milder than feared"
 outcomes (R03 below is the example) and mixes aggregate-volume with BSE-share effects (R02).  Earnings events use no sign_V; they use
 sign(revenue surprise vs vendor consensus) where a consensus is shown, the signs of YoY and QoQ PAT growth, and the sign of the EPS surprise
 (see E-tests).  Consensus figures are secondary vendor data (Investing.com table, reproduced on the same vendor page 2026-10-14; the
 TradingView "21.40 vs 20.31" is NOT used: 21.40 = PAT 872.66 cr / 407.88 mn listed shares, a vendor share-count basis, company-reported EPS
 is 21.22; 20.31 is not reproduced by any other source: Investing 20.51, TradersUnion 20.45, PL Capital 20.7).  The surprise SIGN is
 vendor-robust (beat on EPS in 5/5 comparable quarters), magnitudes are vendor-dependent.

EVENT SETS (the table EVENTS below is the pre-registration; ids are stable).
 EARN7  = the 7 rows of data/results_dates.csv (primary earnings set, n = 7).   EARN10 = EARN7 + Q4 FY24, Q1 FY25, Q3 FY25 (release times
          from NSE dissemination per research/v2/01 s3.1; EXTENDED set, robustness only).
 NE     = gated non-earnings events (regulatory/enforcement, tax-budget, market structure, macro, scheduled implementation days).
          NE_sched = date known in advance; NE_unsched = the rest (selection-exposed).  NE_signed = NE with sign_V != 0.
 ANALYST (5 rating actions, extra; sign = direction of the rating action), GOV_UNK (3 management events with unknown/primary-stamp issues,
          not gated; n too small for any claim).
 Overlap flags: `co_dated` (another listed event shares S*), `contaminated_5d` (another event's S* within S*+1..S*+5).

PER-EVENT METRICS (computed for every event; positions i = index of S*)
 R0, G0, I0 (log).   z0 = R0/sig_i.   Market model on rN with intercept, estimation window positions [i-260, i-11] (250 sessions that END 10
 sessions before day 0), >= 120 valid pairs, else NaN:  AR0 = R0 - (a + b*rN_i);  ARG0, ARI0 analogously (G on GN, I on IN, own fits).
 Next day:  R1 = R_{i+1};  z1 = |R1|/sig_i  (trailing vol FIXED at its pre-event value).   5-day follow-through D5 = sum_{j=1..5} R_{i+j};
 beta-adjusted AD5 = sum of the same-window residuals;  T5 = R0 + D5.   Volume multiple V0 = turnover_i/T0_i, V1 = turnover_{i+1}/T0_i.
 Recovery: cum_j = sum_{m=0..j} R_{i+m}.  If R0 < 0: rec = first j in 1..20 with cum_j >= 0 (full retracement of the day-0 loss to the pre-event
 close);  if R0 > 0: first j with cum_j <= 0.  Censored at >20 (reported as 21 with `rec_censored`).  Half-retracement: first j with
 sign(R0)*cum_j <= 0.5*|R0|.   Forward fields are NaN when the window runs past 2026-10-13.

TEST FAMILY A (every test below is registered; Monte Carlo B = 20,000; seed 20261014; p = (1 + #{null >= obs})/(B+1) unless stated).
 Control pool P = non-event sessions with date >= 2019-01-01, k >= 60, outside [S*-1, S*+5] of EVERY listed event, plus k+5 <= N-1 for
 forward fields.  P is the unconditional baseline in all pool comparisons (same trailing-vol standardisation as the events).
 A1_mag   mean |z0| of a group vs mean of n draws (with replacement) from P:  groups EARN7, NE, NE_sched, NE_unsched, ANALYST.  One-sided
          (greater).  [5 tests]
 A2_sign  sign-rule informativeness on NE_signed (null = shuffle R0 across events, signs fixed):  A2a mean(sign_V*R0);  A2b mean(sign_V*AR0);
          A2c hit rate P(sign(R0) = sign_V).  One-sided (greater).  [3 tests]
 A3_asym  magnitude asymmetry: mean|z0| of sign_V = -1 minus mean|z0| of sign_V = +1 within NE_signed (null = permute the labels), two-sided.
          [1 test]   (raw |R0| and |AR0| versions are robustness variants of the SAME hypothesis, not extra tests.)
 A4_dir   directional asymmetry: mean(sign_V*R0 | sign_V=+1) - mean(sign_V*R0 | sign_V=-1) (null: shuffle R0 across events), two-sided.  [1]
 A5_follow follow-through (+) vs reversal (-): F = sign(R0)*D5/sig_i.  A5a mean F of NE_signed (forward-complete) vs draws from P restricted to
          |z0| >= 1.5 (matched on a large day-0 move; threshold fixed now), two-sided.  A5b mean F of sign_V=+1 minus sign_V=-1 (permute
          labels), two-sided.  [2 tests]
 A6_form  separate verbal/reported news from formal documents.  Unscheduled `regulatory` events only; formal = {formal_order, formal_circular,
          consultation_paper}, informal = {verbal, media_report}.  Difference of mean|z0| (formal - informal), label permutation, two-sided.  [1]
 A7_sched selection diagnostic: mean|z0| NE_unsched minus NE_sched, label permutation, two-sided.  [1]
 A8_vol   mean ln V0 of a group vs draws from P:  groups NE, EARN7.  One-sided greater.  [2]
 A9_recov among NE_signed events with R0 < 0 and a complete 5-day window: share fully retraced within 5 sessions vs the same share among
          P days with z0 <= -1.5 (bootstrap of n draws), two-sided.  [1]
 E-tests (EARN7, exact permutation over all n! pairings, two-sided): E1 mean(sign(rev_surprise)*R0) [n=7]; E2 Spearman(rev_surprise, R0)
          [7]; E3 Spearman(EPS surprise vendor basis, R0) [5, all surprises positive so sign tests are impossible]; E4 Spearman(PAT QoQ %,
          R0) [7]; E5 Spearman(PAT YoY %, R0) [7].  Dossier numbers: research/01 Appendix A and research/v2/01 s3.2.  [5 tests]
 => Family A has 22 hypothesis tests.  Variants (not additional tests, but COUNTED as runs): A1/A2/A3 with W2 instead of day 0, with
    EARN10 instead of EARN7, raw/AR versions, and the "uncontaminated" subsets for A5/A9.
 CIs: 95% percentile bootstrap over events (iid, B = 5,000).  Effective n = number of events (events are sparse; overlaps are flagged).
 Adjustment: Holm (FWER) and Benjamini-Hochberg (FDR) within Family A and across the whole registry (Parts A + B).
 STATUS RULE.  These are in-sample associations.  `validated_out_of_sample` is NOT assigned (no walk-forward event test is run).  A pattern
 is `descriptive_only` if Holm-adjusted p < 0.05, else `not_found`; E-tests and tests with n < 8 per cell are `descriptive_only`/`not_found`
 with an explicit power statement (minimum detectable Spearman rho at 80% power is simulated for n = 5 and 7).

---------------------------------------------------------------------------------------------------------------------
PART B  STRUCTURAL CHANGE AT PRE-SPECIFIED DATES
---------------------------------------------------------------------------------------------------------------------
CANDIDATE DATES (fixed in the task before any test): B1 2024-04-29 (SEBI fee order); B2 2024-10-01 (SEBI F&O measures); B3 first date with a
 BSE-stock F&O row in data/raw/fo_bse (computed: 2024-11-29; the 8 earlier files, 2024-11-18..2024-11-28, are header-only); B4 2025-05-23
 (2:1 bonus ex-date); B5 2025-09-01 (expiry-day swap); B6 2026-02-01 (Budget STT, Sunday session); B7 2026-07-01 (RBI curbs); B8 2026-08-03
 (closing-auction regime); B9 2026-09-30 (first session as a Nifty-50 member).  The break session t is the first session >= the date.
WINDOWS ("clean segments").  pre = sessions [max(t_prev, t-120), t-1], post = sessions [t, min(t_next-1, t+119)] where t_prev/t_next are the
 neighbouring CANDIDATE dates (first date: t-120; last date: to the end of data).  So each test compares two adjacent segments that do not
 contain another candidate break.  Interpretability rule: a test with n_pre < 20 or n_post < 20 is flagged `underpowered` (computed, kept in
 the family, never interpreted): B7/B8/B9 are the affected dates (post = 23, 41/23, 9..10 sessions).
METRICS (6 per date => 54 tests):  M1 vol: ln(RMS(R)_post / RMS(R)_pre).  M2 beta: slope(R on rN)_post - slope_pre (both with intercept; sessions with
 NaN rN excluded).  M3a median(G)_post - median(G)_pre in % points.  M3b share(G>0) post - pre in percentage points.  M3c share(G == 0) post -
 pre in pp (exact zero: |G| < 1e-9, i.e. open == bonus-adjusted previous close).  M4 turnover: mean ln(turnover_cr) post - pre.
INFERENCE (two independent two-sided permutation-type tests per cell, then an intersection-union rule fixed now):
 (1) BLOCK PERMUTATION: pool the pre and post sessions, cut them into blocks of 5 consecutive sessions (counted outward from the break), reassign
     blocks at random to "post" keeping the number of post blocks, recompute the effect; B = 20,000.
 (2) PLACEBO-DATE RANK: the same effect computed with the same pre/post window LENGTHS at every other session t' of 2017-2026 (|t'-t| > 10,
     windows inside the data); p = (1 + #{|e'| >= |e|})/(1 + M).  This respects volatility clustering and level drift (the null contains the real
     breaks of the sample, so it is conservative).
 CLAIM p = max(p_block, p_placebo) (reject only if both reject => size <= alpha).  Holm and BH across the 54 claim-p values; also reported by
 metric (9 each) and for each test separately.  Block-permutation alone is anti-conservative for persistent series (vol, turnover): the
 self-test measures its size under a persistent GARCH null.
EFFECT SIZES + CIs: effect as defined above with 95% stationary-bootstrap CIs (mean block 10, B = 2,000; pre and post resampled separately;
 Nifty pairs resampled jointly).  Every segment's own level is reported.
 STATUS RULE: Holm-claim p < 0.05 => `descriptive_only` (in-sample break; NOT out-of-sample validated); else `not_found`; underpowered cells
 are `not_found (underpowered)` regardless.
FOLLOW-UPS (descriptive, no p-values): (a) exact-zero gaps: first-bar open of the intraday union vs the official open on zero-gap sessions;
 (b) calendar-quarter beta/vol/turnover vs the dossier FPI share (n = 4 quarters: association table only);
 (c) scenario: widening of the 14-Oct distribution if a regulatory event lands (mixture sigma multiplier m(p) = sqrt(1 + p*(Zev^2 - 1)),
     Zev^2 = mean z0^2 of NE_unsched vs the pool's mean z0^2, p in {0.035 [= listed unscheduled NE events per session since 2024-04-29],
     0.15, 0.30}); p for 14 Oct itself is NOT estimable from history.

---------------------------------------------------------------------------------------------------------------------
POST-FIRST-RUN CHANGELOG (disclosed; written AFTER the first execution had shown the outcomes below; everything above this line is the
original pre-registration and was not edited except the one-line test-count remark that follows)
 First-run facts that motivated the changes: Part A: A1_NE raw p 5e-5; A2a mean(sign*R0) +4.16% raw p 0.0015 (Holm-A 0.028), but the variant
 "A2a_timestamped_only" (6 events whose release time is documented independently of the price) gave +0.2%; A4 printed an estimate (0.0895)
 OUTSIDE its own bootstrap CI.  Part B: no cell survived (smallest claim p 0.0022: B2 turnover, Holm-54 0.12; B8 clean pre-window = 23 sessions).
 1. BUG FIX A4: the pre-registered statistic is mean(s*R0|s=+1) - mean(s*R0|s=-1); the first run coded the SUM of the two means (0.0895, raw p
    0.0030, Holm 0.051).  Recoded to the pre-registered difference.  The first-run number was a wrong statistic and is not reported as a finding.
 2. POST-HOC (not pre-registered): long-window sensitivity cells B7L (120 sessions before 2026-07-01 vs 2026-07-01..2026-10-13) and B8L (250
    sessions before 2026-08-03 vs 2026-08-03..2026-10-13) because the clean windows of B7/B8 contain only 23 sessions on one side.  12 extra
    tests (family "B_sens"); Holm/BH are reported within the primary 54, within the 12, and across the whole registry (88 tests).
    B7L's post window contains B8 and B9 (not clean) - stated, not corrected.
 3. POST-HOC diagnostic A2c_by_timing_evidence (Fisher exact, hit rate of sign_V for events whose first session was inferred from the dossier's
    reaction date vs events with documented release time); counted among the variant runs, not in the family.
 4. POST-HOC descriptive additions (no p-values): Nifty gap columns in every segment, monthly BSE/Nifty gap table 2025-07..2026-10, and the
    zero-gap vs first-bar comparison.  Added because the zero-gap/positive-gap shares looked non-monotone around 2026-08-03 in the segment table.
=====================================================================================================================
"""
from __future__ import annotations

import hashlib
import itertools
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

from common import load_bse, load_index, targets

SEED = 20261014
CUTOFF = pd.Timestamp("2026-10-13")
OUT = Path("results/behaviour/events.json")
B_MC = 20000          # Monte Carlo draws for event tests
B_CI = 5000           # bootstrap draws for event-level CIs
B_PERM = 20000        # block permutations (Part B)
B_BOOT = 2000         # stationary-bootstrap draws (Part B effect CIs)
BLOCK = 5             # permutation block (sessions)
SBLOCK = 10           # stationary bootstrap mean block
WIN = 120             # max sessions per segment side
MINW = 20             # interpretability threshold
EXCL = 10             # placebo exclusion radius (sessions)
POOL_START = pd.Timestamp("2019-01-01")

# ---------------------------------------------------------------------------------------------------------------------
# EVENT TABLE (the pre-registration).  fields: id, label, set, type, form, scheduled, info_date, timing, first_session, tev, sign, judge, gating, ref
# set: EARN | NE | ANALYST | GOV
# type: earnings | regulatory | tax_budget | market_structure | macro | governance | analyst
# form: results | formal_order | formal_circular | consultation_paper | verbal | media_report | scheduled_impl | budget | macro_release |
#       corporate_filing | rating_action | index_review
# ---------------------------------------------------------------------------------------------------------------------
def _e(id, label, set_, type_, form, sched, info, timing, first, tev, sign, judge, gating, ref):
    return dict(id=id, label=label, set=set_, type=type_, form=form, scheduled=sched, info_date=info, timing=timing,
                first_session=first, timing_evidence=tev, sign_V=sign, judgement=judge, gating=gating, ref=ref)


EVENTS = [
    # ---- earnings (all released after 15:30; NSE dissemination times from research/v2/01 s3.1; two re-checked by HEAD on nsearchives)
    _e("E01", "Q4 FY24 results", "EARN", "earnings", "results", True, "2024-05-08", "post_close", "2024-05-09", "press", None, False, True, "research/v2/01 s3.1 (20:45 IST); extended set"),
    _e("E02", "Q1 FY25 results", "EARN", "earnings", "results", True, "2024-08-07", "post_close", "2024-08-08", "press", None, False, True, "research/v2/01 s3.1 (17:19 IST); extended set"),
    _e("E03", "Q2 FY25 results", "EARN", "earnings", "results", True, "2024-11-12", "post_close", "2024-11-13", "timestamp", None, False, True, "results_dates.csv; research/v2/01 (19:05 IST)"),
    _e("E04", "Q3 FY25 results", "EARN", "earnings", "results", True, "2025-02-06", "post_close", "2025-02-07", "press", None, False, True, "research/v2/01 s3.1 (18:13 IST); extended set"),
    _e("E05", "Q4 FY25 results", "EARN", "earnings", "results", True, "2025-05-06", "post_close", "2025-05-07", "timestamp", None, False, True, "results_dates.csv; filing Last-Modified 13:33 GMT = 19:03 IST (HEAD 2026-10-14)"),
    _e("E06", "Q1 FY26 results", "EARN", "earnings", "results", True, "2025-08-07", "post_close", "2025-08-08", "press", None, False, True, "results_dates.csv; research/v2/01 (18:18 IST)"),
    _e("E07", "Q2 FY26 results", "EARN", "earnings", "results", True, "2025-11-11", "post_close", "2025-11-12", "press", None, False, True, "results_dates.csv; research/v2/01 (18:02 IST)"),
    _e("E08", "Q3 FY26 results", "EARN", "earnings", "results", True, "2026-02-09", "post_close", "2026-02-10", "press", None, False, True, "results_dates.csv; research/v2/01 (18:40 IST)"),
    _e("E09", "Q4 FY26 results", "EARN", "earnings", "results", True, "2026-05-07", "post_close", "2026-05-08", "press", None, False, True, "results_dates.csv; research/v2/01 (17:36 IST)"),
    _e("E10", "Q1 FY27 results", "EARN", "earnings", "results", True, "2026-08-04", "post_close", "2026-08-05", "timestamp", None, False, True, "results_dates.csv; filing Last-Modified 13:16 GMT = 18:46 IST (HEAD 2026-10-14)"),
    # ---- regulatory / enforcement (unscheduled)
    _e("R01", "SEBI order on regulatory fee base for options (turnover charges)", "NE", "regulatory", "formal_order", False, "2024-04-29", "intraday", "2024-04-29", "dossier_reaction_date", -1, False, True, "research/02 A1 (BS headline dated 29 Apr; time not verified)"),
    _e("R02", "SEBI F&O consultation paper (weekly expiry, lot size, upfront premium)", "NE", "regulatory", "consultation_paper", False, "2024-07-30", "post_close", "2024-07-31", "dossier_reaction_date", -1, False, True, "research/02 A2"),
    _e("R03", "SEBI six-measure F&O circular", "NE", "regulatory", "formal_circular", False, "2024-10-01", "post_close", "2024-10-03", "dossier_reaction_date", -1, False, True, "research/02 A3 (2 Oct holiday); 'milder than feared' => rule mislabels"),
    _e("R04", "Report: SEBI works out expiry-day solution (Tue/Thu)", "NE", "regulatory", "media_report", False, "2025-03-28", "intraday", "2025-03-28", "dossier_reaction_date", 1, False, True, "research/02 A4"),
    _e("R05", "SEBI clears NSE Tuesday / BSE Thursday expiry swap", "NE", "regulatory", "media_report", False, "2025-06-18", "intraday", "2025-06-18", "dossier_reaction_date", 0, False, True, "research/02 A5 (swap: no aggregate-volume direction)"),
    _e("R06", "SEBI interim order vs Jane Street (3 Jul)", "NE", "regulatory", "formal_order", False, "2025-07-03", "post_close", "2025-07-04", "dossier_reaction_date", -1, False, True, "research/02 A6"),
    _e("R07", "SEBI chair on longer-tenor derivatives (verbal)", "NE", "regulatory", "verbal", False, "2025-08-21", "intraday", "2025-08-21", "dossier_reaction_date", -1, False, True, "research/02 A7"),
    _e("R08", "Report: SEBI weighing end of weekly F&O", "NE", "regulatory", "media_report", False, "2025-09-11", "intraday", "2025-09-11", "dossier_reaction_date", -1, False, True, "research/02 A8"),
    _e("R09", "Report: no change in weekly options expiry", "NE", "regulatory", "media_report", False, "2025-11-07", "intraday", "2025-11-07", "dossier_reaction_date", 1, False, True, "research/02 A9 (vendor/press conflict on size; NSE bhavcopy used)"),
    _e("R10", "SEBI NOC to NSE IPO", "NE", "market_structure", "corporate_filing", False, "2026-01-30", "intraday", "2026-01-30", "dossier_reaction_date", -1, True, True, "research/02 B4 older item; competition rule"),
    _e("R11", "RBI circular on bank credit to capital-market intermediaries (13 Feb)", "NE", "regulatory", "formal_circular", False, "2026-02-13", "post_close", "2026-02-16", "dossier_reaction_date", -1, False, True, "research/02 A12; research/v2/01 row 9 (RBI press release)"),
    _e("R12", "NSE files DRHP", "NE", "market_structure", "corporate_filing", False, "2026-06-17", "intraday", "2026-06-17", "dossier_reaction_date", -1, True, True, "research/02 A14; competition rule"),
    _e("R13", "SEBI says it will review expiry-settlement method (reported 3-4 Sep)", "NE", "regulatory", "verbal", False, "2026-09-04", "pre_open", "2026-09-04", "press", 1, False, True, "research/02 R4 (FPJ 4 Sep morning); 3 Sep +move unexplained"),
    _e("R14", "SEBI consultation paper on CAS / settlement (Sat 12 Sep; 14 Sep holiday)", "NE", "regulatory", "consultation_paper", False, "2026-09-12", "nontrading", "2026-09-15", "timestamp", 1, True, True, "SEBI paper 'Issued on September 12, 2026' (research/v2/01 row 11)"),
    _e("R15", "Reuters-sourced report: SEBI to revert derivatives settlement to 30-min VWAP", "NE", "regulatory", "media_report", False, "2026-10-05", "post_close", "2026-10-06", "timestamp", 1, False, True, "first coverage 5 Oct 20:32 IST (research/v2/01 row 12); 5 Oct is NOT the reaction"),
    _e("R16", "SEBI chair: CAS guidelines 'in about a week' (Sat 10 Oct 18:20 IST)", "NE", "regulatory", "verbal", False, "2026-10-10", "nontrading", "2026-10-12", "timestamp", 0, False, True, "SEBI speech PDF Last-Modified 18:20 IST (research/v2/02 M1); timing statement only"),
    _e("R17", "NSE Indices announces BSE to replace Wipro in Nifty 50", "NE", "market_structure", "index_review", False, "2026-08-07", "post_close", "2026-08-10", "dossier_reaction_date", 1, True, True, "research/02 C5 (announcement date inferred, SINGLE-SOURCE)"),
    # ---- scheduled implementation days (sign 0: no new information by rule)
    _e("X01", "Expiry-day swap effective (NSE Tue / BSE Thu)", "NE", "regulatory", "scheduled_impl", True, "2025-09-01", "intraday", "2025-09-01", "timestamp", 0, False, True, "research/02 R11"),
    _e("X02", "RBI prop-funding curbs effective", "NE", "regulatory", "scheduled_impl", True, "2026-07-01", "intraday", "2026-07-01", "timestamp", 0, False, True, "research/02 R10; research/v2/01 row 9"),
    _e("X03", "CAS goes live", "NE", "regulatory", "scheduled_impl", True, "2026-08-03", "intraday", "2026-08-03", "timestamp", 0, False, True, "SEBI circular 16 Jan 2026 (research/v2/01 row 10)"),
    _e("X04", "NSE lists (Rs 1,800)", "NE", "market_structure", "scheduled_impl", True, "2026-09-24", "intraday", "2026-09-24", "timestamp", 0, False, True, "research/02 C1"),
    _e("X05", "Nifty-50 inclusion effective after close (passive buying at close)", "NE", "market_structure", "scheduled_impl", True, "2026-09-29", "intraday", "2026-09-29", "timestamp", 0, True, True, "research/02 C5/G-5; flows complete at the close"),
    # ---- tax / budget
    _e("T01", "Union Budget (Sunday session): F&O STT hike", "NE", "tax_budget", "budget", True, "2026-02-01", "intraday", "2026-02-01", "dossier_reaction_date", -1, False, True, "research/02 R9/A11"),
    # ---- macro (named dates only)
    _e("M01", "US-India trade deal announced (2 Feb, US hours)", "NE", "macro", "macro_release", False, "2026-02-02", "post_close", "2026-02-03", "dossier_reaction_date", 1, False, True, "research/02 M2"),
    _e("M02", "Fed 25bp hike (16 Sep, ~23:30 IST)", "NE", "macro", "macro_release", True, "2026-09-16", "post_close", "2026-09-17", "press", -1, False, True, "research/02 M7"),
    _e("M03", "RBI MPC hikes repo to 5.50%", "NE", "macro", "macro_release", True, "2026-10-07", "intraday", "2026-10-07", "press", -1, False, True, "research/02 M7"),
    _e("M04", "India Sept CPI 5.54% (12 Oct ~16:00)", "NE", "macro", "macro_release", True, "2026-10-12", "post_close", "2026-10-13", "press", -1, True, True, "research/02 M8 (Aug 4.83%); no forward window, no Nifty row for 13 Oct"),
    # ---- analyst actions (extra group)
    _e("A01", "Jefferies Hold -> Underperform", "ANALYST", "analyst", "rating_action", False, "2026-08-17", "intraday", "2026-08-17", "press", -1, False, True, "research/v2/01 row 15"),
    _e("A02", "Nuvama Buy -> Hold", "ANALYST", "analyst", "rating_action", False, "2026-08-18", "intraday", "2026-08-18", "press", -1, False, True, "research/v2/01 row 16"),
    _e("A03", "Bernstein initiates Underperform", "ANALYST", "analyst", "rating_action", False, "2026-09-09", "intraday", "2026-09-09", "press", -1, False, True, "research/v2/01 row 17"),
    _e("A04", "JPMorgan upgrade to Overweight (date approx.)", "ANALYST", "analyst", "rating_action", False, "2026-09-15", "intraday", "2026-09-15", "press", 1, False, True, "research/v2/01 row 19 (single minor aggregator); co-dated with R14"),
    _e("A05", "Macquarie initiates Outperform", "ANALYST", "analyst", "rating_action", False, "2026-09-24", "intraday", "2026-09-24", "press", 1, False, True, "research/v2/01 row 18; co-dated with X04"),
    # ---- management / governance (release time unknown for two; not gated)
    _e("G01", "MD&CEO Chauhan resignation", "GOV", "governance", "corporate_filing", False, "2022-07-25", "unknown", "2022-07-25", "unknown", -1, False, False, "research/v2/01 row 21 (date only)"),
    _e("G02", "SEBI approval letter for new MD&CEO (28 Nov)", "GOV", "governance", "corporate_filing", False, "2022-11-28", "unknown", "2022-11-28", "unknown", 1, False, False, "research/v2/01 row 21 (letter date; dissemination time unknown)"),
    _e("G03", "Board appoints Ramamurthy MD&CEO (filing 13:29 IST)", "GOV", "governance", "corporate_filing", False, "2022-12-08", "intraday", "2022-12-08", "timestamp", 1, False, False, "NSE filing Last-Modified 07:59 GMT (HEAD 2026-10-14); largely pre-announced by the SEBI approval => not gated"),
]

# Earnings fact table (dossier numbers; vendor surprises = Investing.com table reproduced 2026-10-14; None = not computable on a consistent basis)
EARN_FACTS = {
    "E03": dict(pat=345.77, qoq=30.8, yoy=188.0, rev_s=1.50, eps_s=None),
    "E05": dict(pat=493.67, qoq=125.8, yoy=362.0, rev_s=0.83, eps_s=None),
    "E06": dict(pat=538.17, qoq=9.0, yoy=103.6, rev_s=-0.93, eps_s=14.22),
    "E07": dict(pat=557.02, qoq=3.5, yoy=61.1, rev_s=1.71, eps_s=9.36),
    "E08": dict(pat=596.59, qoq=7.1, yoy=172.9, rev_s=0.48, eps_s=9.14),
    "E09": dict(pat=795.47, qoq=33.3, yoy=61.1, rev_s=-2.55, eps_s=19.05),
    "E10": dict(pat=872.66, qoq=9.7, yoy=62.2, rev_s=-1.94, eps_s=4.34),
    "E04": dict(pat=218.59, qoq=-36.8, yoy=100.0, rev_s=6.03, eps_s=None),
    "E02": dict(pat=264.29, qoq=147.2, yoy=None, rev_s=-0.16, eps_s=None),
    "E01": dict(pat=106.89, qoq=None, yoy=None, rev_s=None, eps_s=None),
}
EARN7_IDS = ["E03", "E05", "E06", "E07", "E08", "E09", "E10"]

CAND_DATES = [("B1", "2024-04-29", "SEBI fee order"), ("B2", "2024-10-01", "SEBI F&O measures"), ("B3", None, "first BSE-stock F&O row in data/raw/fo_bse"),
              ("B4", "2025-05-23", "2:1 bonus ex-date"), ("B5", "2025-09-01", "expiry-day swap"), ("B6", "2026-02-01", "Budget STT (Sunday session)"),
              ("B7", "2026-07-01", "RBI prop-funding curbs"), ("B8", "2026-08-03", "closing-auction regime"), ("B9", "2026-09-30", "first session as Nifty-50 member")]
METRICS = ["vol", "beta", "med_gap", "pos_gap", "zero_gap", "turnover"]
METRIC_LABEL = {"vol": "ln(RMS R post / pre)", "beta": "beta to Nifty50 (post - pre)", "med_gap": "median G (pp, post - pre)",
                "pos_gap": "share G>0 (pp, post - pre)", "zero_gap": "share G==0 (pp, post - pre)", "turnover": "mean ln turnover_cr (post - pre)"}


# ---------------------------------------------------------------------------------------------------------------------
# generic helpers
# ---------------------------------------------------------------------------------------------------------------------
def holm(p):
    p = np.asarray(p, float)
    m = len(p)
    o = np.argsort(p)
    adj = np.empty(m)
    run = 0.0
    for r, i in enumerate(o):
        run = max(run, (m - r) * p[i])
        adj[i] = min(1.0, run)
    return adj


def bh(p):
    p = np.asarray(p, float)
    m = len(p)
    o = np.argsort(p)[::-1]
    adj = np.empty(m)
    run = 1.0
    for r, i in enumerate(o):
        k = m - r
        run = min(run, p[i] * m / k)
        adj[i] = run
    return adj


def pv(null, obs, alt="greater"):
    """Monte-Carlo p with the +1 correction.  alt 'two' = |null| >= |obs| (null centred at 0 by construction)."""
    null = np.asarray(null, float)
    null = null[np.isfinite(null)]
    B = len(null)
    if alt == "greater":
        c = np.sum(null >= obs - 1e-12)
    elif alt == "less":
        c = np.sum(null <= obs + 1e-12)
    else:
        c = np.sum(np.abs(null) >= abs(obs) - 1e-12)
    return float((1 + c) / (B + 1))


def pv2_centered(null, obs):
    """two-sided p for a statistic whose null is centred at the null mean (pool comparisons)"""
    null = np.asarray(null, float)
    null = null[np.isfinite(null)]
    mu = null.mean()
    c = np.sum(np.abs(null - mu) >= abs(obs - mu) - 1e-12)
    return float((1 + c) / (len(null) + 1))


def pct_ci(x, lo=2.5, hi=97.5):
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    if len(x) < 2:
        return [None, None]
    return [float(np.percentile(x, lo)), float(np.percentile(x, hi))]


def f(x, nd=6):
    if x is None:
        return None
    try:
        if not np.isfinite(x):
            return None
    except TypeError:
        return x
    return float(np.round(float(x), nd))


def sb_indices(n, B, mean_block, rng):
    p = 1.0 / mean_block
    idx = np.empty((B, n), dtype=np.int64)
    idx[:, 0] = rng.integers(0, n, B)
    new = rng.random((B, n)) < p
    starts = rng.integers(0, n, (B, n))
    for t in range(1, n):
        idx[:, t] = np.where(new[:, t], starts[:, t], (idx[:, t - 1] + 1) % n)
    return idx


def fit_mm(y, x, lo, hi):
    """OLS y = a + b x on positions lo..hi inclusive, valid pairs only.  returns (a, b, n) or (nan, nan, n)"""
    if lo < 0:
        return np.nan, np.nan, 0
    yy, xx = y[lo:hi + 1], x[lo:hi + 1]
    m = np.isfinite(yy) & np.isfinite(xx)
    n = int(m.sum())
    if n < 120:
        return np.nan, np.nan, n
    yy, xx = yy[m], xx[m]
    vx = xx.var()
    if vx <= 0:
        return np.nan, np.nan, n
    b = np.cov(xx, yy, bias=True)[0, 1] / vx
    return float(yy.mean() - b * xx.mean()), float(b), n


# ---------------------------------------------------------------------------------------------------------------------
# data context
# ---------------------------------------------------------------------------------------------------------------------
class Ctx:
    pass


def load_ctx():
    d = load_bse()
    t = targets(d)
    ix = load_index()
    assert d.index.max() <= CUTOFF and ix.index.max() <= CUTOFF, "input dated after the cutoff"
    c = Ctx()
    c.d, c.t, c.idx, c.N = d, t, d.index, len(d)
    c.R, c.G, c.I = t["R"].values.astype(float), t["G"].values.astype(float), t["I"].values.astype(float)
    nc = ix["nifty50_close"].reindex(d.index)
    no = ix["nifty50_open"].reindex(d.index)
    c.rN = np.log(nc / nc.shift(1)).values.astype(float)
    c.GN = np.log(no / nc.shift(1)).values.astype(float)
    c.IN = np.log(nc / no).values.astype(float)
    c.tov = d["turnover_cr"].values.astype(float)
    R2 = pd.Series(c.R ** 2)
    c.sig = np.sqrt(R2.rolling(60).mean().shift(1).values)
    c.T0 = pd.Series(c.tov).rolling(20).mean().shift(1).values
    c.dates = c.idx.values
    return c


# ---------------------------------------------------------------------------------------------------------------------
# PART A
# ---------------------------------------------------------------------------------------------------------------------
def event_row(c, e):
    fs = pd.Timestamp(e["first_session"])
    if fs not in c.idx:
        raise ValueError(f"{e['id']}: {fs.date()} not a session")
    i = c.idx.get_loc(fs)
    N = c.N
    R, G, I = c.R, c.G, c.I
    sig = c.sig[i]
    r = dict(id=e["id"], label=e["label"], set=e["set"], type=e["type"], form=e["form"], scheduled=e["scheduled"], info_date=e["info_date"],
             timing=e["timing"], first_session=e["first_session"], timing_evidence=e["timing_evidence"], sign_V=e["sign_V"],
             judgement=e["judgement"], gating=e["gating"], ref=e["ref"], pos=int(i))
    r["sig60"] = f(sig, 6)
    r["R0"], r["G0"], r["I0"] = R[i], G[i], I[i]
    r["z0"] = R[i] / sig
    r["zG0"], r["zI0"] = G[i] / sig, I[i] / sig
    r["R_m1"] = R[i - 1]
    r["R1"] = R[i + 1] if i + 1 < N else np.nan
    r["z1abs"] = abs(R[i + 1]) / sig if i + 1 < N else np.nan
    r["W2"] = R[i] + R[i + 1] if i + 1 < N else np.nan
    r["zW2"] = r["W2"] / (sig * np.sqrt(2)) if i + 1 < N else np.nan
    a, b, n_est = fit_mm(R, c.rN, i - 260, i - 11)
    aG, bG, _ = fit_mm(G, c.GN, i - 260, i - 11)
    aI, bI, _ = fit_mm(I, c.IN, i - 260, i - 11)
    r["alpha"], r["beta"], r["beta_n"] = a, b, n_est
    r["nifty_R0"] = c.rN[i]
    r["AR0"] = R[i] - (a + b * c.rN[i]) if np.isfinite(a) and np.isfinite(c.rN[i]) else np.nan
    r["ARG0"] = G[i] - (aG + bG * c.GN[i]) if np.isfinite(aG) and np.isfinite(c.GN[i]) else np.nan
    r["ARI0"] = I[i] - (aI + bI * c.IN[i]) if np.isfinite(aI) and np.isfinite(c.IN[i]) else np.nan
    fwd = i + 5 < N
    r["fwd5_complete"] = bool(fwd)
    r["D5"] = float(R[i + 1:i + 6].sum()) if fwd else np.nan
    r["T5"] = r["R0"] + r["D5"] if fwd else np.nan
    if fwd and np.isfinite(a):
        res = R[i + 1:i + 6] - (a + b * c.rN[i + 1:i + 6])
        r["AD5"] = float(res.sum()) if np.all(np.isfinite(res)) else np.nan
    else:
        r["AD5"] = np.nan
    r["V0"] = c.tov[i] / c.T0[i]
    r["V1"] = c.tov[i + 1] / c.T0[i] if i + 1 < N else np.nan
    # recovery
    rec, cens, half = None, None, None
    if abs(R[i]) > 0 and i + 20 < N + 0:
        cum = np.cumsum(R[i:i + 21])
        s = np.sign(R[i])
        hit = np.where(s * cum[1:] <= 0)[0]
        rec = int(hit[0] + 1) if len(hit) else 21
        cens = rec == 21
        hh = np.where(s * cum[1:] <= 0.5 * abs(R[i]))[0]
        half = int(hh[0] + 1) if len(hh) else 21
    elif abs(R[i]) > 0:
        m = min(20, N - 1 - i)
        if m >= 1:
            cum = np.cumsum(R[i:i + m + 1])
            s = np.sign(R[i])
            hit = np.where(s * cum[1:] <= 0)[0]
            if len(hit):
                rec, cens = int(hit[0] + 1), False
            hh = np.where(s * cum[1:] <= 0.5 * abs(R[i]))[0]
            if len(hh):
                half = int(hh[0] + 1)
    r["rec_sessions"], r["rec_censored"], r["half_rec_sessions"] = rec, cens, half
    r["rec5"] = bool(rec is not None and rec <= 5) if fwd else None
    return r


def flag_overlaps(rows):
    pos = {r["id"]: r["pos"] for r in rows}
    for r in rows:
        r["co_dated"] = [o["id"] for o in rows if o["id"] != r["id"] and o["pos"] == r["pos"]]
        r["contaminated_5d"] = [o["id"] for o in rows if o["id"] != r["id"] and r["pos"] + 1 <= o["pos"] <= r["pos"] + 5]


def build_pool(c, rows):
    N = c.N
    excl = np.zeros(N, bool)
    for r in rows:
        excl[max(0, r["pos"] - 1):min(N, r["pos"] + 6)] = True
    dates = pd.DatetimeIndex(c.idx)
    ok = (~excl) & (dates >= POOL_START) & (np.arange(N) >= 60) & np.isfinite(c.sig)
    k = np.where(ok)[0]
    p = dict(k=k)
    p["z0"] = c.R[k] / c.sig[k]
    p["lnV0"] = np.log(c.tov[k] / c.T0[k])
    fw = k + 5 < N
    D5 = np.full(len(k), np.nan)
    D5[fw] = np.array([c.R[j + 1:j + 6].sum() for j in k[fw]])
    p["F"] = np.sign(c.R[k]) * D5 / c.sig[k]
    rec5 = np.full(len(k), np.nan)
    for q, j in enumerate(k):
        if j + 5 < N and c.R[j] < 0:
            cum = np.cumsum(c.R[j:j + 6])
            rec5[q] = float(np.any(cum[1:] >= 0))
    p["rec5"] = rec5
    return p


def draw_means(vals, n, B, rng):
    vals = vals[np.isfinite(vals)]
    idx = rng.integers(0, len(vals), (B, n))
    return vals[idx].mean(1)


def spearman_exact(x, y):
    from scipy.stats import rankdata
    rx, ry = rankdata(x), rankdata(y)
    n = len(x)

    def rho(a, b):
        a = a - a.mean()
        b = b - b.mean()
        return float((a * b).sum() / np.sqrt((a * a).sum() * (b * b).sum()))
    obs = rho(rx, ry)
    cnt = 0
    tot = 0
    for perm in itertools.permutations(range(n)):
        tot += 1
        if abs(rho(rx, ry[list(perm)])) >= abs(obs) - 1e-12:
            cnt += 1
    return obs, cnt / tot, tot


def power_spearman(n, rho_grid, nsim, rng):
    """fraction of simulated bivariate-normal samples with exact two-sided Spearman p < 0.05"""
    from scipy.stats import rankdata
    perms = np.array(list(itertools.permutations(range(n))))
    base = np.arange(1, n + 1, dtype=float)
    base = base - base.mean()
    sd = np.sqrt((base ** 2).sum())
    rho_p = (base[perms] * base).sum(1) / (sd * sd)
    out = {}
    for rho in rho_grid:
        rej = 0
        for _ in range(nsim):
            x = rng.standard_normal(n)
            y = rho * x + np.sqrt(1 - rho ** 2) * rng.standard_normal(n)
            rx, ry = rankdata(x), rankdata(y)
            a, b = rx - rx.mean(), ry - ry.mean()
            ro = (a * b).sum() / np.sqrt((a * a).sum() * (b * b).sum())
            p = np.mean(np.abs(rho_p) >= abs(ro) - 1e-12)
            rej += p < 0.05
        out[str(rho)] = rej / nsim
    return out


def part_a(c, rng):
    rows = [event_row(c, e) for e in EVENTS]
    flag_overlaps(rows)
    df = pd.DataFrame(rows)
    pool = build_pool(c, rows)
    reg = []

    def add(id_, family, hyp, n, est, ci, p, alt, extra=None):
        reg.append(dict(id=id_, part="A", family=family, hypothesis=hyp, n=int(n), estimate=f(est), ci95=[f(x) for x in ci] if ci else None,
                        p_raw=f(p, 8), alt=alt, **(extra or {})))

    def grp(mask):
        return df[mask].copy()

    G_E7 = df[df.id.isin(EARN7_IDS)]
    G_E10 = df[df["set"] == "EARN"]
    G_NE = df[(df["set"] == "NE") & df.gating]
    G_S = G_NE[G_NE.scheduled]
    G_U = G_NE[~G_NE.scheduled]
    G_AN = df[df["set"] == "ANALYST"]
    G_SIG = G_NE[G_NE.sign_V.fillna(0) != 0]
    out = dict(sets={k: v.id.tolist() for k, v in dict(EARN7=G_E7, EARN10=G_E10, NE=G_NE, NE_sched=G_S, NE_unsched=G_U, NE_signed=G_SIG, ANALYST=G_AN).items()})
    pz = pool["z0"]
    out["pool"] = dict(n=int(len(pool["k"])), mean_abs_z0=f(np.mean(np.abs(pz))), rms_z0=f(np.sqrt(np.mean(pz ** 2))), median_abs_z0=f(np.median(np.abs(pz))),
                       share_abs_z_ge_1p5=f(np.mean(np.abs(pz) >= 1.5)), mean_lnV0=f(np.mean(pool["lnV0"])),
                       period=[str(pd.Timestamp(c.idx[pool["k"][0]]).date()), str(pd.Timestamp(c.idx[pool["k"][-1]]).date())])

    def boot_mean(v):
        v = np.asarray(v, float)
        v = v[np.isfinite(v)]
        if len(v) < 2:
            return [None, None]
        return pct_ci(v[rng.integers(0, len(v), (B_CI, len(v)))].mean(1))

    # ---- A1 magnitude vs pool
    for name, g in [("EARN7", G_E7), ("NE", G_NE), ("NE_sched", G_S), ("NE_unsched", G_U), ("ANALYST", G_AN)]:
        v = np.abs(g.z0.values)
        null = draw_means(np.abs(pz), len(v), B_MC, rng)
        add(f"A1_{name}", "A1_mag", f"mean |z0| of {name} exceeds the pool of ordinary sessions", len(v), v.mean(), boot_mean(v), pv(null, v.mean(), "greater"), "greater",
            dict(pool_mean=f(np.abs(pz).mean()), null_p95=f(np.percentile(null, 95)), mean_abs_R0_pct=f(100 * np.abs(g.R0.values).mean(), 3), median_abs_z0=f(np.median(v))))
    # ---- A2 sign informativeness
    s = G_SIG.sign_V.values.astype(float)
    for tag, col in [("a", "R0"), ("b", "AR0")]:
        x = G_SIG[col].values.astype(float)
        m = np.isfinite(x)
        xs, ss = x[m], s[m]
        obs = np.mean(ss * xs)
        null = np.array([np.mean(ss * rng.permutation(xs)) for _ in range(B_MC)])
        add(f"A2{tag}", "A2_sign", f"mean(sign_V*{col}) > 0 on NE_signed", m.sum(), obs, boot_mean(ss * xs), pv(null, obs, "greater"), "greater")
    x = G_SIG.R0.values.astype(float)
    hit = np.mean(np.sign(x) == s)
    nullh = np.array([np.mean(np.sign(rng.permutation(x)) == s) for _ in range(B_MC)])
    add("A2c", "A2_sign", "hit rate P(sign(R0)=sign_V) > chance", len(s), hit, boot_mean((np.sign(x) == s).astype(float)), pv(nullh, hit, "greater"), "greater",
        dict(null_mean=f(nullh.mean()), hits=int((np.sign(x) == s).sum())))
    # ---- A3 magnitude asymmetry
    zs = np.abs(G_SIG.z0.values)
    neg, pos = s == -1, s == 1
    obs = zs[neg].mean() - zs[pos].mean()
    null = np.empty(B_MC)
    for b in range(B_MC):
        pm = rng.permutation(neg)
        null[b] = zs[pm].mean() - zs[~pm].mean()
    ci = pct_ci([rng.choice(zs[neg], neg.sum()).mean() - rng.choice(zs[pos], pos.sum()).mean() for _ in range(B_CI)])
    add("A3", "A3_asym", "mean|z0|(negative) - mean|z0|(positive) != 0", len(s), obs, ci, pv(null, obs, "two"), "two",
        dict(n_neg=int(neg.sum()), n_pos=int(pos.sum()), mean_neg=f(zs[neg].mean()), mean_pos=f(zs[pos].mean()),
             mean_abs_R0_neg_pct=f(100 * np.abs(G_SIG.R0.values[neg]).mean(), 3), mean_abs_R0_pos_pct=f(100 * np.abs(G_SIG.R0.values[pos]).mean(), 3)))
    # ---- A4 directional asymmetry
    xr = G_SIG.R0.values.astype(float)

    def a4(xv):
        sx = s * xv
        return sx[pos].mean() - sx[neg].mean()
    obs = a4(xr)
    null = np.array([a4(rng.permutation(xr)) for _ in range(B_MC)])
    # note: statistic is mean(s*R|+) - mean(s*R|-) = mean(R|+) + mean(R|-)
    ci = pct_ci([rng.choice((s * xr)[pos], pos.sum()).mean() - rng.choice((s * xr)[neg], neg.sum()).mean() for _ in range(B_CI)])
    add("A4", "A4_dir", "mean(s*R0|+) - mean(s*R0|-) != 0 (direction-adjusted reaction differs by sign)", len(s), obs, ci, pv(null, obs, "two"), "two",
        dict(mean_R0_pos_pct=f(100 * xr[pos].mean(), 3), mean_R0_neg_pct=f(100 * xr[neg].mean(), 3)))
    # ---- A5 follow-through
    Fv = np.sign(G_SIG.R0.values) * G_SIG.D5.values / G_SIG.sig60.values
    mfw = np.isfinite(Fv)
    pF = pool["F"][np.abs(pz) >= 1.5]
    pF = pF[np.isfinite(pF)]
    obs = Fv[mfw].mean()
    null = draw_means(pF, int(mfw.sum()), B_MC, rng)
    add("A5a", "A5_follow", "mean F=sign(R0)*D5/sig of NE_signed differs from large-move ordinary days (|z0|>=1.5)", mfw.sum(), obs, boot_mean(Fv[mfw]), pv2_centered(null, obs), "two",
        dict(pool_mean=f(pF.mean()), pool_n=int(len(pF)), continuation_share=f(np.mean(Fv[mfw] > 0)), pool_continuation_share=f(np.mean(pF > 0))))
    sm = s[mfw]
    Fm = Fv[mfw]
    pm_, nm_ = sm == 1, sm == -1
    obs = Fm[pm_].mean() - Fm[nm_].mean()
    null = np.empty(B_MC)
    for b in range(B_MC):
        q = rng.permutation(nm_)
        null[b] = Fm[~q].mean() - Fm[q].mean()
    ci = pct_ci([rng.choice(Fm[pm_], pm_.sum()).mean() - rng.choice(Fm[nm_], nm_.sum()).mean() for _ in range(B_CI)])
    add("A5b", "A5_follow", "F(positive events) - F(negative events) != 0", mfw.sum(), obs, ci, pv(null, obs, "two"), "two",
        dict(n_pos=int(pm_.sum()), n_neg=int(nm_.sum()), F_pos=f(Fm[pm_].mean()), F_neg=f(Fm[nm_].mean())))
    # ---- A6 formal vs informal regulatory (unscheduled)
    reg_u = G_U[G_U.type == "regulatory"]
    fm = reg_u.form.isin(["formal_order", "formal_circular", "consultation_paper"]).values
    im = reg_u.form.isin(["verbal", "media_report"]).values
    zz = np.abs(reg_u.z0.values)
    use = fm | im
    zz, fmu = zz[use], fm[use]
    obs = zz[fmu].mean() - zz[~fmu].mean()
    null = np.empty(B_MC)
    for b in range(B_MC):
        q = rng.permutation(fmu)
        null[b] = zz[q].mean() - zz[~q].mean()
    ci = pct_ci([rng.choice(zz[fmu], fmu.sum()).mean() - rng.choice(zz[~fmu], (~fmu).sum()).mean() for _ in range(B_CI)])
    add("A6", "A6_form", "mean|z0| formal documents - verbal/reported news != 0 (unscheduled regulatory)", len(zz), obs, ci, pv(null, obs, "two"), "two",
        dict(n_formal=int(fmu.sum()), n_informal=int((~fmu).sum()), mean_formal=f(zz[fmu].mean()), mean_informal=f(zz[~fmu].mean()),
             mean_abs_R0_formal_pct=f(100 * np.abs(reg_u.R0.values[use][fmu]).mean(), 3), mean_abs_R0_informal_pct=f(100 * np.abs(reg_u.R0.values[use][~fmu]).mean(), 3)))
    # ---- A7 scheduled vs unscheduled
    zU, zS = np.abs(G_U.z0.values), np.abs(G_S.z0.values)
    obs = zU.mean() - zS.mean()
    allz = np.concatenate([zU, zS])
    lab = np.concatenate([np.ones(len(zU), bool), np.zeros(len(zS), bool)])
    null = np.empty(B_MC)
    for b in range(B_MC):
        q = rng.permutation(lab)
        null[b] = allz[q].mean() - allz[~q].mean()
    ci = pct_ci([rng.choice(zU, len(zU)).mean() - rng.choice(zS, len(zS)).mean() for _ in range(B_CI)])
    add("A7", "A7_sched", "mean|z0| unscheduled - scheduled != 0 (selection diagnostic)", len(allz), obs, ci, pv(null, obs, "two"), "two",
        dict(n_unsched=len(zU), n_sched=len(zS), mean_unsched=f(zU.mean()), mean_sched=f(zS.mean())))
    # ---- A8 volume multiple
    for name, g in [("NE", G_NE), ("EARN7", G_E7)]:
        v = np.log(g.V0.values)
        null = draw_means(pool["lnV0"], len(v), B_MC, rng)
        add(f"A8_{name}", "A8_vol", f"mean ln V0 of {name} exceeds ordinary sessions", len(v), v.mean(), boot_mean(v), pv(null, v.mean(), "greater"), "greater",
            dict(geo_mean_multiple=f(np.exp(v.mean()), 3), pool_geo_mean=f(np.exp(pool["lnV0"].mean()), 3), median_multiple=f(np.median(g.V0.values), 3)))
    # ---- A9 recovery
    neg_ev = G_SIG[(G_SIG.R0 < 0) & G_SIG.fwd5_complete]
    ev_rec = neg_ev.rec5.astype(float).values
    prec = pool["rec5"][(pz <= -1.5)]
    prec = prec[np.isfinite(prec)]
    obs = np.nanmean(ev_rec)
    null = draw_means(prec, len(ev_rec), B_MC, rng)
    add("A9", "A9_recov", "share of negative signed events fully retracing the day-0 loss within 5 sessions differs from ordinary large-loss days", len(ev_rec), obs, boot_mean(ev_rec),
        pv2_centered(null, obs), "two", dict(pool_share=f(prec.mean()), pool_n=int(len(prec)), median_recovery_sessions=f(np.median(neg_ev.rec_sessions.dropna().values) if neg_ev.rec_sessions.notna().any() else np.nan, 2)))
    # ---- E-tests (EARN7)
    e7 = G_E7.set_index("id")
    facts = pd.DataFrame(EARN_FACTS).T
    R0 = e7.R0.astype(float)
    rs = facts.loc[R0.index, "rev_s"].astype(float)
    obs = float(np.mean(np.sign(rs.values) * R0.values))
    n7 = len(R0)
    nullv = [np.mean(np.sign(rs.values) * R0.values[list(pm)]) for pm in itertools.permutations(range(n7))]
    add("E1", "E_earn", "mean(sign(revenue surprise)*R0) > 0 (EARN7, exact permutation, two-sided)", n7, obs, None,
        float((1 + np.sum(np.abs(nullv) >= abs(obs) - 1e-12) - 1) / len(nullv)), "two", dict(signs_agree=int(np.sum(np.sign(rs.values) == np.sign(R0.values))), of=n7))
    for tid, col, desc in [("E2", "rev_s", "revenue surprise %"), ("E3", "eps_s", "EPS surprise % (vendor basis)"), ("E4", "qoq", "PAT QoQ %"), ("E5", "yoy", "PAT YoY %")]:
        xs = facts.loc[R0.index, col]
        m = xs.notna().values
        xv, yv = xs.values[m].astype(float), R0.values[m]
        rho, p, tot = spearman_exact(xv, yv)
        add(tid, "E_earn", f"Spearman({desc}, R0), EARN7 exact permutation, two-sided", int(m.sum()), rho, None, p, "two", dict(perms=tot))
    out["earnings_power"] = {"n7": power_spearman(7, [0.5, 0.7, 0.8, 0.9, 0.95], 1500, rng), "n5": power_spearman(5, [0.5, 0.7, 0.8, 0.9, 0.95], 1500, rng)}
    # sign-direction table for earnings (descriptive)
    out["earnings_table"] = []
    for iid in G_E10.id:
        r = df[df.id == iid].iloc[0]
        fa = EARN_FACTS[iid]
        out["earnings_table"].append(dict(id=iid, label=r.label, session=r.first_session, R0=f(r.R0), G0=f(r.G0), I0=f(r.I0), z0=f(r.z0, 3), AR0=f(r.AR0), z1abs=f(r.z1abs, 3),
                                          D5=f(r.D5), V0=f(r.V0, 3), rec=r.rec_sessions, qoq=fa["qoq"], yoy=fa["yoy"], rev_s=fa["rev_s"], eps_s=fa["eps_s"], in_EARN7=iid in EARN7_IDS))
    # ---- robustness variants (counted runs, not family members)
    var = {}
    nvar = 0

    def run_var(name, fn):
        nonlocal nvar
        nvar += 1
        var[name] = fn()
    zW = lambda g: np.abs(g.zW2.dropna().values)  # noqa: E731
    run_var("A1_W2_NE", lambda: dict(n=int(len(zW(G_NE))), mean=f(zW(G_NE).mean()), p=f(pv(draw_means(np.abs(pz) * 1.0, len(zW(G_NE)), B_MC, rng), zW(G_NE).mean(), "greater"), 6),
                                      note="pool is the day-0 |z0| pool (not 2-session); W2 scaled by sqrt2 so null mean is comparable only approximately"))
    run_var("A1_EARN10", lambda: dict(n=int(len(G_E10)), mean=f(np.abs(G_E10.z0.values).mean()), p=f(pv(draw_means(np.abs(pz), len(G_E10), B_MC, rng), np.abs(G_E10.z0.values).mean(), "greater"), 6)))
    run_var("A8_EARN10", lambda: dict(n=int(len(G_E10)), geo=f(np.exp(np.log(G_E10.V0.values).mean()), 3), p=f(pv(draw_means(pool["lnV0"], len(G_E10), B_MC, rng), np.log(G_E10.V0.values).mean(), "greater"), 6)))
    sabs = np.abs(G_SIG.R0.values)
    obs = sabs[neg].mean() - sabs[pos].mean()

    def _perm_raw():
        nul = []
        for _ in range(2000):
            q = rng.permutation(neg)
            nul.append(sabs[q].mean() - sabs[~q].mean())
        return np.array(nul)
    run_var("A3_rawR0", lambda: dict(diff=f(obs), p=f(pv(_perm_raw(), obs, "two"), 6)))
    ar = np.abs(G_SIG.AR0.values)
    mm = np.isfinite(ar)
    obs2 = ar[mm & neg].mean() - ar[mm & pos].mean()
    def _perm_ar():
        nul = []
        for _ in range(2000):
            q = rng.permutation(neg)
            nul.append(ar[mm & q].mean() - ar[mm & ~q].mean())
        return nul
    run_var("A3_AR0", lambda: dict(diff=f(obs2), p=f(pv(np.array(_perm_ar()), obs2, "two"), 6)))
    unc = G_SIG[G_SIG.contaminated_5d.apply(len) == 0]
    run_var("A5a_uncontaminated", lambda: dict(n=int(unc.D5.notna().sum()), mean_F=f((np.sign(unc.R0) * unc.D5 / unc.sig60).mean())))
    run_var("A2a_timestamped_only", lambda: dict(n=int(((G_SIG.timing_evidence.isin(["timestamp", "press"]))).sum()),
                                                  mean=f((G_SIG[G_SIG.timing_evidence.isin(["timestamp", "press"])].sign_V * G_SIG[G_SIG.timing_evidence.isin(["timestamp", "press"])].R0).mean())))
    # chronological halves of the signed set (descriptive consistency check; NOT a validation)
    gs = G_SIG.sort_values("first_session")
    half = len(gs) // 2
    run_var("A2a_chrono_halves", lambda: dict(first_half_n=half, first_half_mean=f((gs.sign_V * gs.R0).iloc[:half].mean()), second_half_n=len(gs) - half,
                                              second_half_mean=f((gs.sign_V * gs.R0).iloc[half:].mean())))
    # POST-HOC diagnostic (added after the first run showed A2a_timestamped_only ~ 0): hit rate by how the first session was identified
    from scipy.stats import fisher_exact
    doc = G_SIG.timing_evidence.isin(["timestamp", "press"]).values
    hits = (np.sign(G_SIG.R0.values) == G_SIG.sign_V.values.astype(float))

    def _fisher():
        tab = [[int(hits[~doc].sum()), int((~hits[~doc]).sum())], [int(hits[doc].sum()), int((~hits[doc]).sum())]]
        return dict(table_rows_dossier_inferred_vs_documented=tab, odds_ratio=f(fisher_exact(tab)[0], 3), p_two_sided=f(fisher_exact(tab)[1], 5),
                    mean_sR0_dossier_inferred=f((G_SIG.sign_V.values.astype(float) * G_SIG.R0.values)[~doc].mean()), n_dossier_inferred=int((~doc).sum()),
                    mean_sR0_documented=f((G_SIG.sign_V.values.astype(float) * G_SIG.R0.values)[doc].mean()), n_documented=int(doc.sum()))
    run_var("A2c_by_timing_evidence_POSTHOC", _fisher)
    out["variants"], out["n_variant_runs"] = var, nvar
    # ---- per-group descriptive table
    def desc(g):
        return dict(n=len(g), mean_R0_pct=f(100 * g.R0.mean(), 3), mean_abs_R0_pct=f(100 * g.R0.abs().mean(), 3), mean_abs_z0=f(g.z0.abs().mean(), 3), median_abs_z0=f(g.z0.abs().median(), 3),
                    max_abs_z0=f(g.z0.abs().max(), 3), mean_abs_AR0_pct=f(100 * g.AR0.abs().mean(), 3), mean_abs_zG0=f(g.zG0.abs().mean(), 3), mean_abs_zI0=f(g.zI0.abs().mean(), 3),
                    mean_z1abs=f(g.z1abs.mean(), 3), mean_D5_pct=f(100 * g.D5.mean(), 3), geo_V0=f(np.exp(np.log(g.V0).mean()), 3), n_down=int((g.R0 < 0).sum()))
    out["group_descriptives"] = {k: desc(v) for k, v in dict(EARN7=G_E7, EARN10=G_E10, NE=G_NE, NE_sched=G_S, NE_unsched=G_U, NE_pos=G_SIG[G_SIG.sign_V == 1], NE_neg=G_SIG[G_SIG.sign_V == -1], ANALYST=G_AN).items()}
    out["by_type"] = {t_: desc(g) for t_, g in G_NE.groupby("type")}
    out["by_timing"] = {t_: desc(g) for t_, g in G_NE.groupby("timing")}
    # 14-Oct scenario: sigma multiplier
    nsess = int((pd.DatetimeIndex(c.idx) >= pd.Timestamp("2024-04-29")).sum())
    p_base = len(G_U) / nsess
    zev2 = float(np.mean(G_U.z0.values ** 2))
    zp2 = float(np.mean(pz ** 2))
    scen = {}
    for p in [p_base, 0.15, 0.30]:
        scen[f"p={p:.3f}"] = dict(p=f(p, 4), sigma_multiplier=f(np.sqrt(1 + p * (zev2 / zp2 - 1)), 4))
    out["scenario_14oct"] = dict(listed_unscheduled_events=len(G_U), sessions_since_2024_04_29=nsess, p_base=f(p_base, 4), Zev2=f(zev2, 4), Zpool2=f(zp2, 4),
                                 Zev_rms=f(np.sqrt(zev2), 3), note="Zev is selection-biased upward (events were found because prices moved); p for 14 Oct is not estimable", mixture=scen)
    return df, out, reg


# ---------------------------------------------------------------------------------------------------------------------
# PART B
# ---------------------------------------------------------------------------------------------------------------------
def stat_rows(w, R, x, vx, G, lnT):
    """stats of the sessions with weight w (B x n or n,) ; arrays R,x,vx,G,lnT broadcast (n,) or gathered (B,n).  returns dict of arrays (B,)"""
    w = np.atleast_2d(w).astype(float)
    n = w.sum(1)
    R2 = R * R
    out = {}
    out["vol"] = np.sqrt((w * R2).sum(1) / n)
    v = w * vx
    nx = v.sum(1)
    with np.errstate(invalid="ignore", divide="ignore"):
        mx = (v * x).sum(1) / nx
        my = (v * R).sum(1) / nx
        cov = (v * x * R).sum(1) / nx - mx * my
        vr = (v * x * x).sum(1) / nx - mx * mx
        out["beta"] = cov / vr
    out["pos_gap"] = (w * (G > 0)).sum(1) / n
    out["zero_gap"] = (w * (np.abs(G) < 1e-9)).sum(1) / n
    out["turnover"] = (w * lnT).sum(1) / n
    Gb = np.broadcast_to(G, w.shape)
    out["med_gap"] = np.nanmedian(np.where(w > 0, Gb, np.nan), axis=1)
    return out


def effect(post, pre):
    return dict(vol=np.log(post["vol"] / pre["vol"]), beta=post["beta"] - pre["beta"], med_gap=100 * (post["med_gap"] - pre["med_gap"]),
                pos_gap=100 * (post["pos_gap"] - pre["pos_gap"]), zero_gap=100 * (post["zero_gap"] - pre["zero_gap"]), turnover=post["turnover"] - pre["turnover"])


def first_fo_date():
    fl = sorted(Path("data/raw/fo_bse").glob("*.csv"))
    for p in fl:
        with open(p) as fh:
            n = sum(1 for _ in fh) - 1
        if n > 0:
            d = p.stem
            return pd.Timestamp(f"{d[:4]}-{d[4:6]}-{d[6:]}"), len(fl)
    return None, len(fl)


def placebo_effects(R, x, vx, G, lnT, n_pre, n_post):
    """effects for all t' in [n_pre, N-n_post]; returns (tprime array, dict of effect arrays)"""
    N = len(R)
    tp = np.arange(n_pre, N - n_post + 1)
    cs = lambda a: np.concatenate([[0.0], np.cumsum(a)])  # noqa: E731
    C_R2, C_vx = cs(R * R), cs(vx)
    xz = np.where(vx > 0, x, 0.0)
    Rz = np.where(vx > 0, R, 0.0)
    C_x, C_y, C_xy, C_xx = cs(xz), cs(Rz), cs(xz * Rz), cs(xz * xz)
    C_pos, C_zero, C_T = cs((G > 0).astype(float)), cs((np.abs(G) < 1e-9).astype(float)), cs(lnT)

    def seg(C, a, b):
        return C[b] - C[a]

    def group(a, b):
        n = b - a
        o = {}
        o["vol"] = np.sqrt(seg(C_R2, a, b) / n)
        nx = seg(C_vx, a, b)
        with np.errstate(invalid="ignore", divide="ignore"):
            mx = seg(C_x, a, b) / nx
            my = seg(C_y, a, b) / nx
            cov = seg(C_xy, a, b) / nx - mx * my
            vr = seg(C_xx, a, b) / nx - mx * mx
            o["beta"] = cov / vr
        o["pos_gap"] = seg(C_pos, a, b) / n
        o["zero_gap"] = seg(C_zero, a, b) / n
        o["turnover"] = seg(C_T, a, b) / n
        return o
    from numpy.lib.stride_tricks import sliding_window_view as swv
    pre = group(tp - n_pre, tp)
    post = group(tp, tp + n_post)
    pre["med_gap"] = np.median(swv(G, n_pre), axis=1)[tp - n_pre]
    post["med_gap"] = np.median(swv(G, n_post), axis=1)[tp]
    return tp, effect(post, pre)


def segment_stats(c, a, b):
    """descriptive statistics of sessions a..b inclusive"""
    sl = slice(a, b + 1)
    R, x = c.R[sl], c.rN[sl]
    m = np.isfinite(x)
    out = dict(start=str(pd.Timestamp(c.idx[a]).date()), end=str(pd.Timestamp(c.idx[b]).date()), n=int(b - a + 1), rms_R_pct=f(100 * np.sqrt(np.mean(R ** 2)), 4),
               sd_R_pct=f(100 * R.std(ddof=1), 4), mean_R_pct=f(100 * R.mean(), 4), median_G_pct=f(100 * np.median(c.G[sl]), 4), share_pos_gap=f(np.mean(c.G[sl] > 0), 4),
               share_zero_gap=f(np.mean(np.abs(c.G[sl]) < 1e-9), 4), mean_ln_turnover=f(np.mean(np.log(c.tov[sl])), 4), geo_turnover_cr=f(np.exp(np.mean(np.log(c.tov[sl]))), 2),
               sd_G_pct=f(100 * c.G[sl].std(ddof=1), 4), sd_I_pct=f(100 * c.I[sl].std(ddof=1), 4))
    gn = c.GN[sl]
    gm = np.isfinite(gn)
    if gm.sum() >= 5:
        out["nifty_share_pos_gap"] = f(np.mean(gn[gm] > 0), 4)
        out["nifty_median_gap_pct"] = f(100 * np.median(gn[gm]), 4)
        out["bse_minus_nifty_share_pos_gap"] = f(np.mean(c.G[sl][gm] > 0) - np.mean(gn[gm] > 0), 4)
    if m.sum() >= 5:
        b_ = np.cov(x[m], R[m], bias=True)[0, 1] / x[m].var()
        out["beta"] = f(b_, 4)
        out["corr_Nifty"] = f(np.corrcoef(x[m], R[m])[0, 1], 4)
        out["n_beta"] = int(m.sum())
    return out


def break_cells(c, rng, rngl, cid, date_str, label, t, ws, we, group):
    """six tests for one pre/post pair: pre = sessions ws..t-1, post = t..we.  Returns (cells, info)."""
    R, x, G = c.R, c.rN, c.G
    vx = np.isfinite(x).astype(float)
    x0 = np.where(np.isfinite(x), x, 0.0)
    lnT = np.log(c.tov)
    n_pre, n_post = t - ws, we - t + 1
    sl = slice(ws, we + 1)
    Rw, xw, vw, Gw, Tw = R[sl], x0[sl], vx[sl], G[sl], lnT[sl]
    m_post = np.concatenate([np.zeros(n_pre), np.ones(n_post)])
    obs_post = stat_rows(m_post, Rw, xw, vw, Gw, Tw)
    obs_pre = stat_rows(1 - m_post, Rw, xw, vw, Gw, Tw)
    eff_obs = {kk: float(v[0]) for kk, v in effect(obs_post, obs_pre).items()}
    # block permutation
    nb_pre = int(np.ceil(n_pre / BLOCK))
    bid = np.concatenate([(n_pre - 1 - np.arange(n_pre)) // BLOCK, nb_pre + np.arange(n_post) // BLOCK])
    nb = int(bid.max() + 1)
    nb_post = nb - nb_pre
    chosen = np.argsort(rngl.random((B_PERM, nb)), axis=1)[:, :nb_post]
    bm = np.zeros((B_PERM, nb), bool)
    bm[np.arange(B_PERM)[:, None], chosen] = True
    mask = bm[:, bid].astype(float)
    eff_perm = effect(stat_rows(mask, Rw, xw, vw, Gw, Tw), stat_rows(1 - mask, Rw, xw, vw, Gw, Tw))
    # placebo dates
    tp, eff_pl = placebo_effects(R, x0, vx, G, lnT, n_pre, n_post)
    keep = np.abs(tp - t) > EXCL
    j = np.where(tp == t)[0]
    if len(j):
        for kk in METRICS:
            if np.isfinite(eff_obs[kk]) and np.isfinite(eff_pl[kk][j[0]]):
                assert abs(eff_pl[kk][j[0]] - eff_obs[kk]) < 1e-8, (cid, kk, eff_pl[kk][j[0]], eff_obs[kk])
    # bootstrap CI (pre and post resampled separately)
    ip = sb_indices(n_pre, B_BOOT, SBLOCK, rng)
    iq = sb_indices(n_post, B_BOOT, SBLOCK, rng)
    a_ = np.arange(n_pre) + ws
    b_ = np.arange(n_post) + t

    def gathered(base, idxm):
        sel = base[idxm]
        return stat_rows(np.ones(idxm.shape), R[sel], x0[sel], vx[sel], G[sel], lnT[sel])
    eb = effect(gathered(b_, iq), gathered(a_, ip))
    cells = []
    for kk in METRICS:
        eo = eff_obs[kk]
        ep = eff_perm[kk][np.isfinite(eff_perm[kk])]
        pb = float((1 + np.sum(np.abs(ep) >= abs(eo) - 1e-12)) / (1 + len(ep))) if np.isfinite(eo) else np.nan
        pl = eff_pl[kk][keep]
        pl = pl[np.isfinite(pl)]
        pp = float((1 + np.sum(np.abs(pl) >= abs(eo) - 1e-12)) / (1 + len(pl))) if np.isfinite(eo) else np.nan
        under = (n_pre < MINW) or (n_post < MINW)
        cells.append(dict(id=f"{cid}_{kk}", part="B", group=group, family=f"B_{group}", hypothesis=f"{cid} {date_str} ({label}): change in {METRIC_LABEL[kk]}", date_id=cid,
                          break_session=str(pd.Timestamp(c.idx[t]).date()), metric=kk, n=int(n_pre + n_post), n_pre=int(n_pre), n_post=int(n_post), underpowered=bool(under),
                          estimate=f(eo, 6), ci95=[f(v_) for v_ in pct_ci(eb[kk])], p_block=f(pb, 6), p_placebo=f(pp, 6), p_raw=f(max(pb, pp), 8), alt="two", n_placebo=int(len(pl))))
    info = dict(id=cid, date=date_str, label=label, break_session=str(pd.Timestamp(c.idx[t]).date()), n_pre=int(n_pre), n_post=int(n_post),
                pre_window=[str(pd.Timestamp(c.idx[ws]).date()), str(pd.Timestamp(c.idx[t - 1]).date())], post_window=[str(pd.Timestamp(c.idx[t]).date()), str(pd.Timestamp(c.idx[we]).date())],
                pre=segment_stats(c, ws, t - 1), post=segment_stats(c, t, we), group=group)
    return cells, info


def part_b(c, rng):
    fo_date, nfiles = first_fo_date()
    pos_of = lambda d_: int(c.idx.searchsorted(pd.Timestamp(d_)))  # noqa: E731
    cands = []
    for cid, dstr, lab in CAND_DATES:
        dt = fo_date if cid == "B3" else pd.Timestamp(dstr)
        cands.append(dict(id=cid, date=dt, label=lab, pos=pos_of(dt)))
    cands = sorted(cands, key=lambda z: z["pos"])
    N = c.N
    rngl = np.random.default_rng(SEED + 7)
    cells, infos = [], []
    for k, cd in enumerate(cands):
        t = cd["pos"]
        t_prev = cands[k - 1]["pos"] if k > 0 else t - WIN
        t_next = cands[k + 1]["pos"] if k + 1 < len(cands) else N
        ws = max(t_prev, t - WIN)
        we = min(t_next - 1, t + WIN - 1)
        cc, inf = break_cells(c, rng, rngl, cd["id"], str(cd["date"].date()), cd["label"], t, ws, we, "primary")
        cells += cc
        infos.append(inf)
    # POST-HOC long-window sensitivity (added after the first run; see POST-FIRST-RUN CHANGELOG): the clean windows of B7/B8 have only 23 sessions on one side.
    sens = []
    byid = {z["id"]: z for z in cands}
    t7, t8 = byid["B7"]["pos"], byid["B8"]["pos"]
    for cid, lab, t, ws in [("B7L", "RBI curbs, long windows: 120 sessions before vs 07-01..end", t7, t7 - WIN), ("B8L", "closing-auction regime, long windows: 250 sessions before vs 08-03..end", t8, t8 - 250)]:
        cc, inf = break_cells(c, rng, rngl, cid, str(c.idx[t].date()), lab, t, ws, N - 1, "sens")
        sens += cc
        infos.append(inf)
    cells_all = cells + sens
    # adjustments: claim p = max(p_block, p_placebo); Holm/BH within the primary 54, within the 12 sensitivity cells, and (in main) across the registry
    for grp, cl in [("primary", cells), ("sens", sens)]:
        pcl = np.array([z["p_raw"] for z in cl])
        pb_ = np.array([z["p_block"] for z in cl])
        pp_ = np.array([z["p_placebo"] for z in cl])
        for arr_name, arr in [("holm", holm(pcl)), ("bh", bh(pcl)), ("holm_block_only", holm(pb_)), ("holm_placebo_only", holm(pp_))]:
            for z, v_ in zip(cl, arr):
                z[f"p_{arr_name}_B"] = f(v_, 8)
    for kk in METRICS:
        ii = [i for i, z in enumerate(cells) if z["metric"] == kk]
        h = holm(np.array([cells[i]["p_raw"] for i in ii]))
        for i_, v_ in zip(ii, h):
            cells[i_]["p_holm_metric"] = f(v_, 8)
    info = dict(candidates=infos, fo_first_row_date=str(fo_date.date()) if fo_date is not None else None, fo_files=nfiles)
    return cells_all, info


def part_b_followups(c, rng):
    out = {}
    # (a) exact-zero gaps vs intraday first bar
    try:
        u = pd.read_csv("data/processed/intraday_union_15m.csv", parse_dates=["date"])
        assert u.date.max() <= CUTOFF
        first = u.sort_values(["date", "time"]).groupby("date").first()
        rows = []
        for dt in c.idx[(np.abs(c.G) < 1e-9) & (c.idx >= pd.Timestamp("2026-08-03"))]:
            if dt in first.index:
                i = c.idx.get_loc(dt)
                rows.append(dict(date=str(dt.date()), official_open=float(c.d.loc[dt, "open"]), prev=float(c.d.loc[dt, "prev"]), first_bar_open=float(first.loc[dt, "open"]),
                                 first_bar_open_minus_official=f(float(first.loc[dt, "open"] - c.d.loc[dt, "open"]), 3), source=str(first.loc[dt, "source"])))
        allz = [str(dt.date()) for dt in c.idx[(np.abs(c.G) < 1e-9) & (c.idx >= pd.Timestamp("2026-08-03"))]]
        out["zero_gap_followup"] = dict(zero_gap_sessions_since_2026_08_03=allz, intraday_available=rows,
                                        note="first-bar open is the first continuous trade; official open is the pre-open auction price (docs/DEVIATIONS 17); equality of official open with prev close is not itself evidence of a data fault")
        # zero-gap share by year and tick
        yr = pd.Series(np.abs(c.G) < 1e-9, index=c.idx).groupby(c.idx.year).agg(["sum", "count"])
        out["zero_gap_by_year"] = {str(k): dict(zero=int(v["sum"]), n=int(v["count"]), share=f(v["sum"] / v["count"], 4)) for k, v in yr.iterrows()}
    except Exception as ex:  # noqa: BLE001
        out["zero_gap_followup"] = dict(error=str(ex))
    # (b) calendar quarters vs FPI share (dossier G-1)
    fpi = {"2025Q3": 16.3, "2025Q4": 17.5, "2026Q1": 19.42, "2026Q2": 21.32}
    qs = {"2025Q3": ("2025-07-01", "2025-09-30"), "2025Q4": ("2025-10-01", "2025-12-31"), "2026Q1": ("2026-01-01", "2026-03-31"), "2026Q2": ("2026-04-01", "2026-06-30"),
          "2026Q3_to_cutoff": ("2026-07-01", "2026-10-13")}
    rows = {}
    for q, (a, b) in qs.items():
        sel = np.where((c.idx >= pd.Timestamp(a)) & (c.idx <= pd.Timestamp(b)))[0]
        s_ = segment_stats(c, sel[0], sel[-1])
        s_["fpi_share_pct_quarter_end"] = fpi.get(q)
        rows[q] = s_
    ql = list(fpi)
    corr = {}
    for kname in ["rms_R_pct", "beta", "geo_turnover_cr", "corr_Nifty"]:
        v = [rows[q][kname] for q in ql]
        corr[kname] = f(np.corrcoef(list(fpi.values()), v)[0, 1], 3)
    # (c) POST-HOC descriptive: monthly gap statistics 2025-07..2026-10 for BSE and for the Nifty (is the gap shift specific to 2026-08-03?)
    mon = {}
    for per in pd.period_range("2025-07", "2026-10", freq="M"):
        sel = np.where(pd.PeriodIndex(c.idx, freq="M") == per)[0]
        if len(sel) == 0:
            continue
        gn = c.GN[sel]
        gm = np.isfinite(gn)
        mon[str(per)] = dict(n=int(len(sel)), bse_median_gap_pct=f(100 * np.median(c.G[sel]), 3), bse_share_pos=f(np.mean(c.G[sel] > 0), 3), bse_share_zero=f(np.mean(np.abs(c.G[sel]) < 1e-9), 3),
                             nifty_share_pos=f(np.mean(gn[gm] > 0), 3) if gm.any() else None, nifty_median_gap_pct=f(100 * np.median(gn[gm]), 3) if gm.any() else None,
                             mean_R_pct=f(100 * c.R[sel].mean(), 3))
    out["monthly_gap_table_POSTHOC"] = mon
    out["quarterly_fpi"] = dict(rows=rows, pearson_with_fpi_share_n4=corr, note="n = 4 quarters; association table only, no inference; FPI share from research/01 G-1 (Trendlyne/IIFL, SINGLE-SOURCE)")
    return out


# ---------------------------------------------------------------------------------------------------------------------
# SELF-TEST (simulated data only)
# ---------------------------------------------------------------------------------------------------------------------
def selftest():
    rng = np.random.default_rng(1)
    t0 = time.time()

    def garch(n, omega=2e-6, a=0.08, b=0.90, shift_at=None, mult=1.0):
        r = np.empty(n)
        h = omega / (1 - a - b)
        for i in range(n):
            if shift_at is not None and i >= shift_at:
                s = np.sqrt(h) * mult
            else:
                s = np.sqrt(h)
            r[i] = s * rng.standard_normal()
            h = omega + a * (r[i] / (mult if (shift_at is not None and i >= shift_at) else 1.0)) ** 2 + b * h
        return r
    N, brk, nrep, Bp = 1500, 900, 120, 400
    res = {"null": {"block": 0, "placebo": 0, "max": 0}, "shift1.6": {"block": 0, "placebo": 0, "max": 0}}
    for scen, kw in [("null", {}), ("shift1.6", dict(shift_at=brk, mult=1.6))]:
        for _ in range(nrep):
            r = garch(N, **kw)
            Gs = r * 0.4
            xN = r * 0.8 + 0.002 * rng.standard_normal(N)
            lnT = np.zeros(N)
            vx = np.ones(N)
            n_pre = n_post = 100
            sl = slice(brk - n_pre, brk + n_post)
            m_post = np.concatenate([np.zeros(n_pre), np.ones(n_post)])
            ob = stat_rows(m_post, r[sl], xN[sl], vx[sl], Gs[sl], lnT[sl])
            op = stat_rows(1 - m_post, r[sl], xN[sl], vx[sl], Gs[sl], lnT[sl])
            e_obs = effect(ob, op)["vol"][0]
            bid = np.concatenate([(n_pre - 1 - np.arange(n_pre)) // BLOCK, (n_pre // BLOCK) + np.arange(n_post) // BLOCK])
            nb = bid.max() + 1
            nbp = nb - n_pre // BLOCK
            chosen = np.argsort(rng.random((Bp, nb)), axis=1)[:, :nbp]
            bm = np.zeros((Bp, nb), bool)
            bm[np.arange(Bp)[:, None], chosen] = True
            mk = bm[:, bid].astype(float)
            ep = effect(stat_rows(mk, r[sl], xN[sl], vx[sl], Gs[sl], lnT[sl]), stat_rows(1 - mk, r[sl], xN[sl], vx[sl], Gs[sl], lnT[sl]))["vol"]
            pbk = (1 + np.sum(np.abs(ep) >= abs(e_obs))) / (Bp + 1)
            tp, epl = placebo_effects(r, xN, vx, Gs, lnT, n_pre, n_post)
            keep = np.abs(tp - brk) > EXCL
            ppl = (1 + np.sum(np.abs(epl["vol"][keep]) >= abs(e_obs))) / (1 + keep.sum())
            res[scen]["block"] += pbk < 0.05
            res[scen]["placebo"] += ppl < 0.05
            res[scen]["max"] += max(pbk, ppl) < 0.05
    out = {k: {kk: vv / nrep for kk, vv in v.items()} for k, v in res.items()}
    # Holm/BH sanity
    p = np.array([0.001, 0.01, 0.02, 0.04, 0.5])
    out["holm"], out["bh"] = holm(p).tolist(), bh(p).tolist()
    # exact spearman sanity
    rho, pval, tot = spearman_exact([1, 2, 3, 4, 5, 6, 7], [1, 2, 3, 4, 5, 6, 7])
    out["spearman_perfect_n7"] = [rho, pval, tot]
    out["seconds"] = round(time.time() - t0, 1)
    out["config"] = dict(N=N, break_at=brk, reps=nrep, B_perm=Bp, garch=dict(a=0.08, b=0.90), window=100)
    print(json.dumps(out, indent=1))
    return out


# ---------------------------------------------------------------------------------------------------------------------
def sanitize(o):
    if isinstance(o, dict):
        return {str(k): sanitize(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [sanitize(v) for v in o]
    if isinstance(o, (np.bool_,)):
        return bool(o)
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (float, np.floating)):
        return float(o) if np.isfinite(o) else None
    if isinstance(o, (pd.Timestamp,)):
        return str(o)
    return o


def main():
    if "--selftest" in sys.argv:
        selftest()
        return
    t0 = time.time()
    rng = np.random.default_rng(SEED)
    c = load_ctx()
    df, outA, regA = part_a(c, rng)
    cellsB, infoB = part_b(c, np.random.default_rng(SEED + 1))
    fol = part_b_followups(c, np.random.default_rng(SEED + 2))
    # ---- adjustments
    pA = np.array([r["p_raw"] for r in regA])
    for r, h, b in zip(regA, holm(pA), bh(pA)):
        r["p_holm_A"], r["p_bh_A"] = f(h, 8), f(b, 8)
    allr = regA + cellsB
    for r in cellsB:
        r.setdefault("p_holm_B", None)
    pall = np.array([r["p_raw"] for r in allr])
    for r, h, b in zip(allr, holm(pall), bh(pall)):
        r["p_holm_all"], r["p_bh_all"] = f(h, 8), f(b, 8)
    for r in allr:
        if r["part"] == "A":
            r["status"] = "descriptive_only" if r["p_holm_A"] is not None and r["p_holm_A"] < 0.05 else "not_found"
            if r["id"].startswith("E"):
                r["status"] = "descriptive_only" if r["status"] == "descriptive_only" else "not_found (n<=7: ~no power)"
        else:
            r["status"] = "not_found (underpowered)" if r["underpowered"] else ("descriptive_only" if (r["p_holm_B"] is not None and r["p_holm_B"] < 0.05) else "not_found")
    ev_records = []
    for _, r in df.iterrows():
        d_ = {k: (None if (isinstance(v, float) and not np.isfinite(v)) else v) for k, v in r.to_dict().items()}
        for k in ["R0", "G0", "I0", "R_m1", "R1", "W2", "nifty_R0", "AR0", "ARG0", "ARI0", "D5", "T5", "AD5", "alpha"]:
            d_[k] = f(d_.get(k), 6)
        for k in ["z0", "zG0", "zI0", "z1abs", "zW2", "V0", "V1", "beta"]:
            d_[k] = f(d_.get(k), 4)
        for k in ["rec_sessions", "half_rec_sessions"]:
            if d_.get(k) is not None:
                d_[k] = int(d_[k])
        d_["rec_censored"] = None if d_.get("rec_censored") is None else bool(d_["rec_censored"])
        d_["rec5"] = None if d_.get("rec5") is None else bool(d_["rec5"])
        d_["sign_V"] = None if d_["sign_V"] is None or (isinstance(d_["sign_V"], float) and not np.isfinite(d_["sign_V"])) else int(d_["sign_V"])
        ev_records.append(d_)
    src = Path(__file__).read_bytes()
    meta = dict(script="src/behaviour/events.py", sha256=hashlib.sha256(src).hexdigest(), mtime_utc=pd.Timestamp(Path(__file__).stat().st_mtime, unit="s").isoformat(),
                run_utc=pd.Timestamp.now(tz="UTC").isoformat(), seed=SEED, B_MC=B_MC, B_CI=B_CI, B_PERM=B_PERM, B_BOOT=B_BOOT, block=BLOCK, n_events=len(EVENTS),
                n_tests_A=len(regA), n_tests_B_primary=sum(1 for r in cellsB if r["group"] == "primary"), n_tests_B_sens=sum(1 for r in cellsB if r["group"] == "sens"), n_tests_total=len(allr), n_variant_runs_A=outA["n_variant_runs"],
                max_date_in_inputs=str(pd.Timestamp(c.idx.max()).date()), data_sessions=int(c.N), runtime_s=round(time.time() - t0, 1),
                cutoff_note="inputs asserted <= 2026-10-13; no network access in this script")
    obj = dict(meta=meta, events=ev_records, partA=outA, partB=dict(info=infoB, followups=fol), registry=allr)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(sanitize(obj), indent=1))
    print(f"wrote {OUT}  tests A={len(regA)} B={len(cellsB)}  runtime {meta['runtime_s']}s")


if __name__ == "__main__":
    main()
