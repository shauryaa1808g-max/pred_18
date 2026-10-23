# v2 verification of workstream "news" (research/v2/02_news_catalysts_update.md)

Verifier: independent re-check. Stock BSE Ltd (NSE: BSE), target session Wed 2026-10-14, P0 = Rs 3,375.40. Information cutoff 2026-10-13 22:00 IST. Written to this single file only. The analyst's files were not edited. No git commands were run. Scratch code and downloads are in the session scratchpad under `vn/` (`vn/*.py`, `vn/dl/`); every Python run used `python3 -I` from outside the data directories.

## 0. Bottom line

1. **The "BSE Ltd made 0 filings on 13 Oct / no Q2 board-meeting intimation" claim is REFUTED. The fundamentals workstream is right.** BSE Ltd filed a Prior Intimation of Board Meeting on 13 Oct: meeting Wed 4 Nov 2026 (Q2 and H1 results), digitally signed 15:52:17 IST, NSE board-meetings feed stamps 16:02:54 ("Financial Results" row) and 16:03:59 ("Board Meeting Intimation" row), PDF server stamp 16:02:57 IST. All of that is before the 22:00 cutoff and before the frozen v1 cutoff of 16:55. I re-downloaded the PDF and the sha256 is identical to the fundamentals workstream's copy.
2. **Why the announcements API lacked it.** The `corporate-announcements` feed has no "Board Meeting Intimation" category at all (61 categories in BSE's 1,312 rows, 44 on 13 Oct market-wide). Prior intimations are published only in the separate `corporate-board-meetings` feed. The five previous BSE intimations (Jul 2025, Oct 2025, Jan 2026, Apr 2026, Jul 2026) also have zero rows in the announcements feed on their dates. The analyst's second check queried the board-meetings feed by **meeting date** (13-24 Oct, 478 pre-cutoff rows, which I reproduced exactly), so a 4 Nov meeting could not appear. The analyst's own ledger line "18:44 and 19:41 ABSL AMC board intimation" shows the feed contained 13 Oct intimations; the same query by symbol would have returned BSE's two rows.
3. **Everything else I could re-test reproduces**: the 14:15 spike statistics (8.87x, rank 3 of 495, 27.2% of bar volume, 53.7% window share), the 12 and 13 Oct residuals (to the second decimal), the peer and index returns, the official 13 Oct index closes, the SEBI Chairman quote, the SEBI "no CAS circular" negative, the F&O positioning, the ECB rates, and the calendar rows (Groww 14 Oct, Angel One 15 Oct, 20 Oct Dussehra, Muhurat 8 Nov).
4. **Forecast impact of the errors found: none.** 4 Nov is 21 days after the target session, the intimation was filed after the 14:15 spike, and no number used for the v1 distribution depends on it. The error is one of evidence quality: a false statement labelled `verified_source`, repeated in sections 1, 2, 3.2, 6, 8 (U12), 10, 11 and 12, built on an endpoint whose completeness was never tested with a positive control.
5. **Overall severity: major** (evidence-quality / labelling, not forecast-relevant). The remaining issues are minor: the spike's "3 of 495" is threshold-sensitive; "5 Oct = story day" is an assumption contradicted by the earliest coverage stamps I found; several stamps cannot be reproduced and two sit at or after 22:00; "57 board meetings" is a row count (25 companies); one primary-source fact (Angel One call time) was under-labelled SOFT.

## 1. Exposure and cutoff statement (read first)

* Wall clock at start: Thu 15 Oct 2026 13:13 IST. Judgement is as of 13 Oct 22:00 IST.
* **Not opened:** `results/forecast_score_2026-10-14*.json`, `results/forecast_record_2026-10-14_v2.json`, `data/raw/udiff/20261014.zip`, any 14/15 Oct market data, `research/v2/04-06*.md`. I ran no repository fetch script and did not touch `data/raw/macro`.
* **Local data read with an explicit date filter (<= 2026-10-13):** `bse_daily.csv`, `xlsx_15m_clean.csv`, `data/raw/intraday/20261007_20261013.csv`, `peers_daily.csv`, `index_daily.csv` (ends 12 Oct), `bse_iv_daily.csv`, FRED CSVs in `data/raw/macro`. (`bse_daily.csv` has a 13 Oct row sourced from the 13 Oct UDiFF file; it contains no 14 Oct data.)
* **Live endpoints return current state.** For every NSE API response I filtered by the timestamp field before printing. Rows after the cutoff were counted, not read: market-wide announcements 13 post-cutoff rows dated 13 Oct; board-meetings 59 (13-24 Oct window) and 150 (13 Oct-6 Nov window) rows; BSE symbol feeds 0; Groww symbol announcements 10 post-cutoff rows (counted, not printed, not read); Angel One and the two board-meeting symbol feeds 0. SEBI listings: circulars 0 items dated after 13 Oct; press releases 3 and reports 1 dated after 13 Oct (counted; titles not read).
* **Exposures to disclose (none used in any verdict):**
  1. A WebFetch of the Investing.com article cited at 21:47 IST showed "Updated: Oct 13, 2026, 04:16 PM" (zone not stated, presumably ET = 01:46 IST 14 Oct) with US closing levels (S&P 7,806.26 "virtually unchanged", Nasdaq 27,204.38 -0.2%, Dow 51,670.99 -0.4%) and live quote widgets (S&P 7,718.94 -1.11%, Nasdaq 26,692.87 -1.88%, Dow 51,621.48 -0.09%) at an unstated, post-cutoff time. I saw these numbers. I did not use them; the US-snapshot claim is therefore marked unverifiable below.
  2. I saw the size/ETag/Last-Modified response headers of NSE `block.csv` and `bulk.csv` (Last-Modified Wed 14 Oct 13:07:03 GMT, i.e. files now holding 14 Oct data; sizes 111 and 16,831 bytes). I did not read the bodies and make no inference from the sizes.
  3. Searches for the KOSPI and CAS stories returned some pages dated 14 Oct (for example a technology.org page about 13 Oct events). I used them only for 13 Oct facts.
  4. Before starting my own checks I read `research/v2/01_fundamentals_verification.md` (as instructed) and also `research/v2/verify_fundamentals.md`, a peer verifier's file written on 14 Oct around 13:37 IST by a session that had live access during the target day. It contains no BSE 14 Oct prices. My refutation of the "0 filings" claim was reproduced from raw feeds with my own code, but I was not blind to that file's conclusion.
* No post-cutoff content influenced a verdict.

## 2. Claim-by-claim

### Check 1. "BSE Ltd made 0 filings on 13 Oct; no Q2 board-meeting intimation" (report sections 1.2, 2, 3.2, 6, 8-U12, 10, 11, 12; label `verified_source`) - REFUTED

Evidence (all raw, all stamped before the cutoff):
* PDF `https://nsearchives.nseindia.com/corporate/BSE1_13102026160203_NSEIntimation.pdf` (892,664 bytes, `Last-Modified: Tue, 13 Oct 2026 10:32:57 GMT` = 16:02:57 IST, sha256 23f84a40...a75e1, identical to the fundamentals copy). Text: Board of Directors meeting "scheduled to be held on Wednesday, November 4, 2026" to approve unaudited results for the quarter and half year ended 30 Sep 2026; trading window "closed from Thursday, October 1, 2026 ... till Friday, November 6, 2026"; signature "Date: 2026.10.13 15:52:17 +05'30'".
* `api/corporate-board-meetings?symbol=BSE` (20 rows, none after the cutoff): `13-Oct-2026 16:02:54` meeting 04-Nov-2026 "Financial Results" (PDF above) and `13-Oct-2026 16:03:59` "Board Meeting Intimation" (iXBRL PRIOR_INTIMATION file).
* The same board-meetings feed with a **meeting-date** window 13-24 Oct has 478 pre-cutoff rows (the analyst's number) and no BSE row; with a 13 Oct-6 Nov window it contains BSE's two rows.
* Lead time 22 days, in the 17-27 day range of the previous five (Jul 2025 -> 7 Aug; Oct 2025 -> 11 Nov; Jan 2026 -> 9 Feb; Apr 2026 -> 7 May; Jul 2026 -> 4 Aug).
* The announcements feed (`corporate-announcements?symbol=BSE`, 1,312 rows, newest `12-Oct-2026 15:30:27`, none after) has no row on 13 Oct and no prior-intimation category. For each of the previous intimation dates (16 Jul 2025, 23 Oct 2025, 13 Jan 2026, 20 Apr 2026, 14 Jul 2026) it has zero rows on that date. So its silence on 13 Oct is not informative.

What survives: "no company event inside the 6-session window" is true; "BSE Q2 results fall 2-12 Nov in 9 of 9 years" is true (I reproduced 3 Nov 2017, 2 Nov 2018, 6 Nov 2019, 7 Nov 2020, 12 Nov 2021, 7 Nov 2022, 10 Nov 2023, 12 Nov 2024, 11 Nov 2025 from the announcements feed) and is consistent with 4 Nov. What is wrong: "no intimation", "0 filings", "not before 24 Oct (FIRM)", section 10's "Confirmed: no intimation by 22:00 IST" (it confirmed a falsehood), U12 (already resolved), and the `verified_source` labels. Precision note: the 16:02:54 stamp belongs to the "Financial Results" row; the "Board Meeting Intimation" row is 16:03:59.

### Check 2. 13 Oct 14:15 bar statistics (8.9x slot median, rank 3 of 495, 27.2%, 53.7% vs 19.8%) - CONFIRMED (numbers), with context caveats

Independent code (`vn/spike.py`, `vn/spike2.py`, `vn/spike3.py`) on `xlsx_15m_clean.csv` filtered to <= 13 Oct; also cross-checked against `data/raw/intraday/20261007_20261013.csv` (identical 14:15 bar: O 3318.6, H 3400.9, L 3318.6, C 3326.3, volume 1,076,912; both are Yahoo-origin, so this checks transcription, not the source).

| Statistic | Report | Mine |
|---|---|---|
| Slot (14:15) median of the other 19 sessions | 121,449 | 121,449 (max 586,351 on 21 Sep) |
| Ratio | 8.87x | 8.867x; 1.84x the slot maximum |
| Bootstrap CI of ratio (5,000 draws, seed 20261013, resample the other 19) | 5.1-10.2x | 5.06-10.22x (slot-median CI 105,385-212,942) |
| Rank by volume / by range among 495 bars | 3 / 4 | 3 / 4 (29 Sep 15:00 and 14:45 are larger by volume) |
| Share of bar-sum volume in this bar | 27.2% | 27.20%; next-highest 14:15 share in any other session 8.96% (21 Sep) |
| 14:15-15:15 window share vs other-19 median | 53.7% vs 19.8% (CI 18.0-27.6%) | 53.7% vs 19.75% (CI 18.0-27.6%); only 29 Sep (85.2%) higher; using 14:15-15:00 only: 53.1% vs 19.3% |
| Bars sum vs official | 3,959,915 = 96.1% of 4,119,552 | same |
| Day total vs trailing-20 median | 0.95x (4,334,371) | 0.950x (4,334,371) |
| Next bar 14:30 | 465,382 = 3.0x slot median | 2.98x |

Caveats the report does not make:
* **"3 of 495" depends on the 2% range threshold.** Using leave-one-session-out slot medians, bars with a >=5x multiple number **11 (2.2% of bars, in 8 of 20 sessions)**: 29 Sep 15:00 (79.5x), 29 Sep 14:45 (10.0x), 18 Sep 15:15 (9.0x, closing-auction bar), **13 Oct 14:15 (8.87x)**, 21 Sep 13:30 (8.2x, 751,692 shares), 30 Sep 15:15, 1 Oct 13:15 (6.7x), 7 Oct 11:45 (6.6x), 7 Oct 11:30 (5.5x, range 1.88%), 29 Sep 14:30, 24 Sep 10:00. With a range threshold of 1.75% or lower the flagged set is 4 bars, not 3 (7 Oct 11:30 enters). So the 13 Oct bar is the largest non-29-Sep, non-auction multiple, but unexplained large-multiple bars (21 Sep 13:30, 1 Oct 13:15, 7 Oct 11:30-11:45) are not rare in this 20-session sample and were not examined.
* "Largest slot multiple on 5-6 Oct was 5.2x (6 Oct 12:45)": I get 4.98x with leave-one-out medians. Immaterial definitional difference.
* "Thresholds fixed before looking" cannot be verified from outside.
* Five sessions lack the 15:15 bar (17 Sep, 22 Sep, 29 Sep, 8 Oct, 9 Oct); this slightly affects window shares but not the conclusion.
* There is no intraday index or peer series, so the claim that the spike is BSE-specific rather than market-wide at 14:15 is untested. The Nifty closed at its high (high = close = 22,721.95), and all of BSE's net gain for the day came after 14:15 (price 3,318.6 = -0.35% vs prev at the bar open; close +1.36%).

### Check 3. "Spike cause not found" and the supporting negatives (block file NO RECORDS, bulk, no NSE notice, 29 filings 13:45-14:40, 520 filings screened) - PARTIALLY CONFIRMED

* **Reproduced:** 520 market-wide announcements stamped <= 22:00 on 13 Oct (13 more after); 29 filings in 13:45-14:40, none about exchanges, SEBI, derivatives or CAS (closest CAMS 14:21:56, Paytm 14:32:03); surveillance notices on 13 Oct: 8 "Spurt in Volume" + 2 "News Verification" = 10 notices to 9 distinct other stocks, none to BSE (plus 3 "Price movement" notices, all after 19:23). BSE's own history of such notices (22-23 Dec 2025, 31 Jul 2024, 30 Aug 2023 and 19 Sep 2024, 11 Mar 2022 price-movement) is in the feed, which acts as a positive control for those categories. This negative is reasonably supported.
* **Weakened by the feed gap (Check 1):** the screen of "520 filings" cannot see board-meeting intimations. On 13 Oct the board-meetings feed has 111 pre-cutoff rows from 53 companies; **32 of those 53 companies have no row at all in that day's announcements feed**. For the specific 13:45-14:40 window the board feed holds only 2 rows (one company, SPORTKING), so the gap did not hide anything relevant to the spike. The spike conclusion survives; the evidential claim "BSE disclosure: 0 filings -> rejected" is factually wrong, although the real filing (16:02) came after the spike (14:15) and is routine, so the rejection stands for the right reason.
* **Not re-verifiable:** NSE `block.csv`/`bulk.csv` for 13 Oct (analyst stamp 13:27:04 GMT = 18:57 IST). These are rolling "latest" files, now overwritten (14 Oct 13:07 GMT). I did not open them. The afternoon block window (14:05-14:20, minimum Rs 25 cr) and the bulk threshold (>0.5% of equity, 0.5% x 407.88M = 2.04M shares) are rule arithmetic I accept.
* **Not testable by me:** media-search negatives (about 20 queries), the "Multibagg auto-generated" page.
* Label `not_found` is appropriate. Status of the F&O positioning line (Oct future close 3,397.6 vs 3,351.1, OI +419,800 to 13,093,800, put OI -348,000 = -5.2%, call OI +8,400, high 3,420.7, basis 22.2): **confirmed** from the 13 Oct F&O bhavcopy (`Last-Modified 13:54:02 GMT` = 19:24 IST, identical stamp to the analyst's).

### Check 4. SEBI: no CAS / derivative-settlement circular as of 22:00 IST, and the Chairman's "about a week" quote (M1, M4; `verified_source`) - CONFIRMED

* Chairman PDF `https://www.sebi.gov.in/sebi_data/attachdocs/oct-2026/1791636650448.pdf`: `Last-Modified Sat 10 Oct 12:50:50 GMT` = 18:20:50 IST. Text: "Following review of the Closing Auction Session, a consultation paper was put out to address concerns in respect of settlement price of derivatives on expiry-day. We are currently examining the comments and hope to issue guidelines in about a week's time." Verbatim match; the speech does not mention VWAP. Location: BSE Brokers' Forum, Capital Market Confluence, Mumbai, 10 Oct.
* Listings re-fetched (post-cutoff, so they also expose any late-posted or back-dated item): circulars - newest three dated 7 Oct (debt-market circulars), then 1 Oct, 9 Sep; **no circular dated 8-13 Oct, and none dated later than 13 Oct either**. Press releases - newest dated 13 Oct is a refund public notice, next the 10 Oct Chairman address. Reports - the 13 Oct LODR consultation, and the CAS paper still dated 12 Sep. Because a late-evening 13 Oct posting would carry the 13 Oct date and appear in a listing fetched two days later, my re-check removes the report's own worry that the listings "may lag" for 13 Oct. The report's lone caveat (a Business Standard 13 Oct IPO-relaxation item not on the lists) is plausibly a press item, not a circular.
* The one blemish: the SEBI RSS "built 22:00:02 IST" is stamped two seconds after the cutoff by the report's own rule ("anything stamped after 22:00:00 was dropped") yet is the report's main negative. Substantively irrelevant; it should have been disclosed as a 2 s overrun. I could not re-fetch the RSS (it now shows current state).

### Check 5. 12 Oct and 13 Oct residuals (section 4, appendix A C3/C4) - CONFIRMED (arithmetic); interpretation limits noted

`vn/resid.py`, `vn/peers.py`. Inputs: BSE R vs bonus-adjusted prev from `src/common.targets`; Nifty 50 from `index_daily.csv` to 12 Oct (22,363.35) plus the official 13 Oct close 22,721.95 (verified in Check 8); beta fitted on the 250 sessions ending the day before (no intercept), residual sd from the same window.

| | 12 Oct | 13 Oct |
|---|---|---|
| BSE R (log) / Nifty (log) | +1.300% / -0.700% | +1.348% / +1.591% |
| beta 0.89: residual, z | +1.923 pp, +0.88 | -0.068 pp, -0.03 |
| rolling-250 beta: beta, residual, sd, z | 1.417, +2.291 pp, 2.131, +1.075 | 1.390, -0.864 pp, 2.116, -0.408 |
| Share of last 250 sessions with larger abs residual (rolling-250 beta) | 26.8% | 64.0% |
| Same share at beta 0.89 | 34.8% | 96.4% |
| Equal-weight Angel One/CDSL/MCX/CAMS/KFin (log) | +1.961% (BSE minus peers -0.66 pp) | +1.604% (-0.26 pp) |
| Nifty Capital Markets | +1.49% log (+1.50% simple) | +0.509% (5,259.00 -> 5,285.75, official) |

Matches the report to the printed precision. Notes:
* The report's single "27%" in section 1.4 is the rolling-250 version only; at beta 0.89 it is 35%.
* "Market-explained" on 13 Oct is beta-dependent: -0.07 pp at 0.89 but -0.86 pp at 1.39. Both |z| < 0.5, so the qualitative statement holds, but it is a daily close-to-close statement; intraday, all of the day's gain came after 14:15.
* The peer set (five names) was not pre-specified in the report. Nuvama (+5.75% on 12 Oct, -3.32% on 13 Oct) is in `peers_daily.csv` but not in the equal-weight mean; including it would raise the 12 Oct peer mean to about 2.6%.
* Status `descriptive_only` is right.

### Check 6. Calendar rows - CONFIRMED, with three corrections

* **Groww (Billionbrains) Q2 on 14 Oct:** NSE announcements 7 Oct 16:19:18/16:23:21 (board feed, "Financial Results"/"Board Meeting Intimation", meeting 14-Oct-2026). Intimation PDF (signed 16:15:51): board meeting "Wednesday, October 14, 2026". Earnings-call PDF (`Last-Modified 7 Oct 11:10:45 GMT` = 16:40:45 IST; feed 16:40:43): call "Wednesday, October 14, 2026 at 04:00 p.m. (IST)". Q1 precedent in the feed: outcome 15 Jul 11:30:46, shareholder letter 11:45:14, KPIs 11:53:56 (in market hours). All as reported; the outcome time for Q2 remains unannounced (labelled SOFT, correctly).
* **Angel One Q2 on 15 Oct:** board feed rows 21 Sep (18:31:16, 18:42:10, 18:52:15) and 6 Oct (16:05:37, 16:12:23 "Dividend", 16:16:53); PDF of 6 Oct: second interim dividend considered, **record date Thursday 22 Oct 2026**. Q1 outcome time precedent 15 Jul 17:42:36 (feed). All as reported. **Correction 1:** the report labels the Angel One earnings call (16 Oct 11:00) SOFT "ScanX headline only"; the 21 Sep primary PDF (`Last-Modified 21 Sep 13:01:18 GMT`) says "earnings call ... on Friday, October 16, 2026 at 11:00 hrs. (IST)". That is FIRM.
* **20 Oct closed:** NSE `holiday-master` (CM and FO): 2 Oct Mahatma Gandhi Jayanti, **20 Oct Tuesday Dussehra**, 8 Nov Sunday "Diwali Laxmi Pujan*" (Muhurat, timings unannounced), 10 Nov Diwali-Balipratipada. No 14 Oct holiday. Next five sessions after 14 Oct: 15, 16, 19, 21, 22 Oct (correct). Caveat: the report fetched the holiday master at about 22:10 IST (post-cutoff, unstamped); my fetch is also post-cutoff. Holidays are fixed in advance, so the exposure is immaterial.
* Other rows spot-checked in the board feed: ICICI Lombard 14 Oct, Wipro/Nestle/TechM/HDFC AMC/360 ONE/5paisa/Jio Fin/L&T Fin/HDFC Life/IIFL 15 Oct, HDFC Bank and ICICI Bank Sat 17 Oct, ABSL AMC 21 Oct (intimated 13 Oct 18:44:48 and 19:41:14), Infosys/Crisil/UTI AMC 23 Oct, CAMS board 29 Oct, KFin 26 Oct, F&O monthly expiry 27 Oct (F&O bhavcopy shows 2026-10-27). All consistent.
* **Correction 2:** "Fri 16 Oct: 57 board meetings" is a **row count**; the feed has 57 rows for 25 companies (each meeting appears in two or three rows). The same applies to the 478/537-row "entries" (rows, not companies).
* **Correction 3:** "CDSL, MCX, Nuvama: no board date in 13-24 Oct list" - CDSL's Q2 board meeting is **31 Oct 2026** (feed rows 12 Oct 13:01:44 and 13:04:04); the 13-24 Oct filter hid it. MCX and Nuvama have no row through 6 Nov.
* Not re-verified: WPI release date, US CPI 18:00 IST 14 Oct, Beige Book 23:30 IST, FOMC 27-28 Oct (all plausible, all after the Indian close), Sensex Thursday weekly expiry (rule-based, taken from the v1 dossier).

### Check 7. Cutoff discipline ("nothing used that was stamped after 22:00 IST") - PARTIALLY CONFIRMED

Structural fact: the analyst's clock read 21:59:33 IST at the start, and the report file's mtime is 16:51 UTC = 22:21 IST, so **every fetch happened at or after the cutoff**. Compliance rests entirely on per-document stamps. Dated items re-tested:

| Item | Analyst stamp | What I observe now | Verdict |
|---|---|---|---|
| NSE F&O bhavcopy 13 Oct | Last-Modified 13:54:02 GMT = 19:24 IST | identical | reproduced |
| SEBI Chairman PDF | 10 Oct 12:50:50 GMT = 18:20 IST | identical | reproduced |
| Groww/Angel One PDFs, board feed rows | 7 Oct 16:40:45; 6 Oct 16:12-16:14; 21 Sep | identical | reproduced |
| NSE `ind_close_all_13102026.csv` | 14:20:38 GMT = 19:50 IST | **17:50:11 GMT = 23:20 IST** (rewritten after the cutoff) | stamp not reproducible; values used (Nifty 22,721.95 +1.60%, VIX 14.12 -7.43%, Capital Markets 5,285.75 +0.51%, IT +5.22%, Next 50 +0.84%, Nifty 500 +1.22%, Midcap 150 +0.97%, Bank +1.03%, Fin Services +1.46%) are identical in the current file; the file also contains a duplicated Nifty 50 row |
| NSE `sec_bhavdata_full_13102026.csv` | 16:25:37 GMT = 21:55 IST | **18:25:36 GMT = 23:55 IST** | stamp not reproducible; BSE row identical (delivery 36.07%, average price 3,343.16, volume 4,119,552) |
| NSE `block.csv`, `bulk.csv` | 13:27:04 GMT = 18:57 IST | 14 Oct 13:07:03 GMT | unverifiable (overwritten; bodies not read) |
| SEBI RSS | built 22:00:02 IST | not re-fetchable | **2 s after the cutoff by the report's own rule**; used as the main negative |
| Yahoo ticker S&P 7,804.86 (-0.03%) | "unstated time about 21:55-22:02" | not re-checkable | possibly post-cutoff; the report labels it uncertain |
| Investing.com page 7,797.63 at "12:17 ET" (21:47 IST) | "midday update" | page now shows "Updated 13 Oct 04:16 PM" and different text | rolling document overwritten; the 21:47 version is not retrievable. Unverifiable. |
| NSE `fiidiiTradeReact` (FII -1,305.13 cr, DII +2,439.24 cr) | no time in payload | live endpoint now shows later data; not opened | unverifiable; report already flags "time unknown" |
| NSE holiday master | fetched about 22:10 IST | n/a | post-cutoff fetch, unstamped (immaterial) |
| ECB USD/INR | about 19:30 IST | 13 Oct 95.28; 12 Oct 95.78; 9 Oct 96.73; 8 Oct 96.78 | values reproduced; publication about 19:30 IST is the ECB's usual time |

Assessment: no number I could test came from content that postdates the cutoff in substance; but the claim as phrased ("anything stamped after 22:00:00 IST was dropped") is not strictly met (RSS 22:00:02; a ticker possibly at 22:02; unstamped live feeds fetched after 22:00), and two key stamps (index close file, delivery file) cannot be reproduced because NSE rewrote them later that night. The values are unchanged, so this is a documentation weakness, not a numerical one.

### Check 8. "Already priced": +10.81% from 1 Oct, only +0.58% since 7 Oct; CAS-rollback story timing and duplicate counting (M2, section 7.3, U1) - PARTIALLY CONFIRMED

* **Numbers reproduce** (`vn/priced.py`): 1 Oct close 3,046.0 -> 3,375.4 = +10.81%; 7 Oct 3,356.0 -> +0.58%; Capital Markets 5,041.8 -> 5,285.75 = +4.84%; Nifty 22,421.95 -> 22,721.95 = +1.34%; 5/6/7 Oct simple returns +4.39/+3.94/+1.54% (log +4.29/+3.87/+1.53%); September cluster 3-4 Sep log +4.27/+3.09, next four sessions summing -3.1%. (The text mixes simple and log; the appendix says log, but the headline percentages are simple.)
* **Attribution problem:** section 3.3 labels 5 Oct the "CAS-rollback story day" and M2 counts +4.39% as the first reaction to the Reuters report. The earliest coverage stamps I could find are **Lapaas Voice `datePublished` 2026-10-05T16:54:43+05:30** (with `dateModified` 6 Oct 02:05), Outlook Money 6 Oct 09:04:52, Whalesbook 6 Oct 05:01 UTC (10:31 IST), Kotak Neo 6 Oct 11:31:31. The 5 Oct rally (open 3,052, price-implied onset in the 12:15 bar, close 3,179.6 at 15:30) was completed **before any coverage I can find**. I could not read the Reuters original (the search returned only outlets citing it) and a Reuters scoop may precede secondary write-ups, so the attribution is unproven rather than wrong. The report itself says the exact story time was not found, but then uses 5 Oct as a reaction day in U1 ("5 first-reaction days") and in the "priced in" register.
* **Duplicate counting:** M2 is handled well (ten outlets counted as one unnamed-source report). But "5 first-reaction days ... 5/5 positive" in U1/section 9 are 5 days from only 2 clusters (3 from one), and the report's own register says n = 2 clusters. The "5/5" phrasing overstates independence.
* M2's label "unverified (single source)" is correctly conservative. The conclusion that the October rally is largely in the price is `descriptive_only` and fairly stated.

## 3. Other items spot-verified (not counted as separate claims)

* Angel One September business update (M7): ADTO Rs 44,879 bn (+8.4% m/m, -6.9% y/y), orders 122.29 mn (-4.1% y/y), F&O option-premium retail share 22.5% (+66 bps y/y), clients 39.98 mn (+17.3% y/y) - all match the 6 Oct PDF (stamp 6 Oct 02:07:01 GMT = 07:37 IST). The interpretation "recovering from the Aug trough" is selective: option-premium ADTO fell 11.2% m/m and Q2 notional ADTO fell 13.9% q/q.
* KOSPI close 6,035.35 (-5.46%, prior 6,384.24 implied), intraday low 5,911.11, Samsung -7.39%, SK hynix -10.09%: corroborated by Seoul Economic Daily (13 Oct), KED Global (13 Oct) and others; some outlets quote different intraday percentages.
* Delivery 36.07% (z -0.64 vs prior 60 valid sessions mean 41.29, sd 8.16; 23rd percentile), VWAP 3,343.16, close +0.96% above VWAP, ATM IV 38.54% at the 33rd percentile of 461 days, trailing-20 volume ratio 0.95: all reproduced.
* S&P 500 12 Oct close 7,807.24, US VIX 15.21, FRED Dated-Brent $125.44 (6 Oct) vs futures $104-107 ("instrument mismatch"): consistent with the FRED files.
* Not re-verified: US bank results figures, JPMorgan stance conflict, CEO CNBC-TV18 quotes, sell-side targets, Groww Q1 profit figures, WPI/CPI dates. They are secondary or low-relevance to the 14 Oct distribution.

## 4. Which "no filing / no announcement found" negatives are weakened by the feed gap

| Negative in the report | Status after this check |
|---|---|
| BSE Ltd 0 filings on 13 Oct; last filing 12 Oct 15:30:27 (1.2, 2, 12) | **False** for the exchange's overall record: the board-meetings feed holds two 13 Oct rows and the PDF exists. Announcements-feed statement itself ("newest row 12 Oct 15:30:27") is true. |
| No Q2 board intimation; "not before 24 Oct (FIRM)"; U12; section 10 "Confirmed" | **False**; meeting 4 Nov. |
| BSE absent from the 13-24 Oct board calendar (478 rows) | True but uninformative (meeting-date filter). |
| 520 market-wide filings screened, "None relevant" (section 2) | **Weakened**: feed lacks prior intimations; 32 of 53 companies with a 13 Oct board intimation have no announcements row that day. The categories that matter for exchange/SEBI news are present. |
| 29 filings 13:45-14:40, none explains the spike (3.2) | Mostly intact; the board feed has only 2 rows (one irrelevant company) in that window. |
| No NSE news-verification / volume-spurt / price-movement notice to BSE | Intact: categories exist in the feed and BSE's own past notices appear in it. |
| "CDSL, MCX, Nuvama: no board date" | CDSL has 31 Oct (hidden by the date window). |
| Block file NO RECORDS; bulk has no BSE row | Different source, unaffected by the API gap; cannot be re-verified now (rolling files). |
| Media-search negatives, no wire story, social sentiment inaccessible | Untested by this check; the report already says absence of evidence. |

Lesson for the pipeline: a negative from `corporate-announcements` needs a positive control (does the feed show a known event of that type on its known date?) and a cross-check against `corporate-board-meetings` by symbol. The analyst's report contained the control (the ABSL and Angel One rows in the board feed) but did not apply it to BSE.

## 5. Corrections requested from the analyst (for the reconciler)

1. Replace "0 filings / no Q2 intimation" with: Q2 FY27 board meeting Wed 4 Nov 2026, intimated 13 Oct 16:02:54 / 16:03:59 IST; trading window 1 Oct-6 Nov.
2. Drop "not before 24 Oct (FIRM)", close U12, and downgrade the section 10 and section 12 labels.
3. State the RSS stamp as 22:00:02 (2 s over the cutoff) and note that the index-close and delivery files were rewritten after 22:00 (values unchanged).
4. Report "57 board meetings" as 57 rows / 25 companies; add CDSL 31 Oct; upgrade the Angel One call (16 Oct 11:00) to FIRM.
5. Add the base rate of >=5x bars (11 of 495) next to "3 of 495", and note the range-threshold sensitivity.
6. Mark 5 Oct as "move preceded all coverage found (earliest 16:54 IST); attribution to the Reuters story unproven", and describe the "5 reaction days" as 2 clusters.

## 6. Reproduction

Scripts: `vn/spike.py`, `vn/spike2.py`, `vn/spike3.py` (bar statistics), `vn/resid.py`, `vn/peers.py` (residuals and peers), `vn/priced.py` (priced-in numbers), `vn/api1.py`-`api7.py` (NSE feed parsing with an explicit `<= 2026-10-13 22:00` filter), all under `/tmp/claude-0/-home-user-pred-18/01384b6e-cd11-5bbc-b7f5-2dd03125e5eb/scratchpad/vn/`. Downloads (NSE archive CSV/PDF/ZIP, SEBI PDF and listings) are in `vn/dl/`.
