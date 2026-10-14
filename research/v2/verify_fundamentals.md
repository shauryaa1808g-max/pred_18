# v2 verification of workstream "fundamentals" (research/v2/01_fundamentals_verification.md)

Verifier: independent re-check, BSE Ltd (NSE: BSE), target session Wed 2026-10-14, P0 = Rs 3,375.40, information cutoff 2026-10-13 22:00 IST.
Written to this single file only. The analyst's files were not edited. No git commands were run. Scratch files are in the session scratchpad under `vf/`.

## 0. Bottom line

1. **The fundamentals workstream is right and the news workstream is wrong on the Q2 board-meeting intimation.** BSE Ltd did file a Q2 FY27 board-meeting intimation on 13 Oct (meeting Wed 4 Nov 2026), signed 15:52:17 IST, disseminated about 16:02:54-16:03:59 IST, i.e. before the 22:00 cutoff. The news workstream's "BSE Ltd made 0 filings on 13 Oct / no Q2 intimation" is refuted. The cause is a design flaw (see section 3), not a data change after the cutoff.
2. All primary-source numbers I re-read (Q1 FY27 revenue, total income, PAT, EPS, investment/other income, share counts, shareholding, the CFO quotes, the SEBI chairman quote, the SEBI consultation paper, the NSE holiday master) match the report exactly. The earnings-reaction permutation test reproduces to the third decimal (raw p 0.0236 with seed 20261014). The own-history P/E percentile reproduces exactly (8.2nd of 413 sessions).
3. One headline over-reaches: "the +4.39% on 5 Oct therefore predates the [Reuters] report". What is verified is only that the earliest *secondary* coverage found is stamped 5 Oct 20:32:57 IST. The Reuters original was never read (reuters.com is also blocked for my tools), so "predates" is an inference, not a verified fact. Supporting evidence exists (MCX did not move on 5 Oct and jumped +4.0% on 6 Oct) but was not in the report.
4. Overall severity for the fundamentals report: **minor**. The error that matters for the pipeline is in the *news* workstream (it would be major there if left unreconciled, although it does not move the 14 Oct forecast because 4 Nov is outside the window).
5. Nothing in the fundamentals report depends on information published after 22:00 IST. The file was last written at 16:27 UTC = 21:57 IST (file mtime), consistent with its own account.

## 1. Cutoff and exposure statement (read this first)

- At the start of my fetches the sandbox clock read Wed 14 Oct 2026 13:27 IST (target session in progress). Judgement is as of 22:00 IST on 13 Oct.
- I did not look at BSE prices, volumes or headlines for 14 Oct. All local CSVs were read with an explicit `date <= 2026-10-13` filter (bse_daily.csv ends 2026-10-13; the 15-minute file was filtered the same way).
- Live endpoints return current state. Where a response could contain post-cutoff rows I filtered by timestamp before printing:
  - NSE `corporate-announcements?symbol=BSE`: newest row is 12 Oct 15:30:27 (1,312 rows, identical to the analyst's count). No row after the cutoff exists for BSE.
  - NSE market-wide announcements for 13 Oct: 533 rows returned, 520 stamped <= 22:00 on 13 Oct (the same 520 the news workstream reports); 13 rows outside my filter were counted, not read.
  - NSE `corporate-board-meetings`: window 13-24 Oct returned 485 rows (478 stamped <= cutoff, same 478 as the news workstream); window 13 Oct-6 Nov returned 808 (770 <= cutoff). Rows after the cutoff were counted, not read. For symbol BSE no row is stamped after the cutoff.
  - SEBI circular listing: parsed by date; 0 rows dated after 13 Oct (titles of nothing later were seen).
- Web searches (4) and page fetches returned only pages published on or before 6 Oct, plus live pages (Investing.com earnings table). **Exposure disclosed:** the Investing.com earnings page also displayed its current Q2 FY27 consensus row (EPS 15.23, revenue 13.85B) and "next earnings 06-11-2026". That consensus row has no publication stamp. I did not use it for any verdict (it only confirms the aggregator still shows the stale 6 Nov date, which is consistent with the analyst's statement that the 6 Nov date is an algorithmic estimate).
- No post-cutoff content influenced a verdict.

## 2. Claim-by-claim verification

### Check 1. Q2 FY27 board meeting is Wed 4 Nov 2026, intimated 13 Oct 2026 (report rows 23, C1) - CONFIRMED

Independent evidence:
- Re-downloaded `https://nsearchives.nseindia.com/corporate/BSE1_13102026160203_NSEIntimation.pdf` (892,664 bytes, sha256 23f84a40...a75e1 - byte-identical to the analyst's copy). Text: "a meeting of the Board of Directors is scheduled to be held on Wednesday, November 4, 2026, to inter alia, consider and approve Unaudited financial results (Standalone and Consolidated) ... for the quarter and half year ended September 30, 2026"; trading window "closed from Thursday, October 1, 2026, and will remain closed till Friday, November 6, 2026 (both days inclusive)". Digital signature of the Company Secretary: 2026.10.13 15:52:17 +05:30.
- HTTP header on the PDF: `Last-Modified: Tue, 13 Oct 2026 10:32:57 GMT` = 16:02:57 IST (the file name stamp 160203 = 16:02:03).
- NSE `api/corporate-board-meetings?symbol=BSE`: two rows for the 4 Nov meeting, `bm_timestamp` 13-Oct-2026 16:02:54 (purpose "Financial Results") and 16:03:59 (purpose "Board Meeting Intimation", sysTime 16:04:02); the linked iXBRL "Prior Intimation of Board Meeting" shows proposed date 04-11-2026, trading-window closure 01-10-2026 to 06-11-2026, date of report 13-10-2026.
- Lead times in the same feed for previous results: 14 Jul->4 Aug 2026 (21 days), 20 Apr->7 May (17), 13 Jan->9 Feb (27), 23 Oct->11 Nov 2025 (19), 16 Jul->7 Aug 2025 (22); this one 22 days. Matches "17-27 days".
- Minor precision point: the report says "disseminated by NSE at 16:02:54". The 16:02:54 stamp belongs to the "Financial Results" row; the "Board Meeting Intimation" row is 16:03:59. Both are before 16:55 (frozen v1 cutoff) and after the dossiers' ~15:45 cutoff, so the report's "contradicts both dossiers" is fair relative to the v1 cutoff but the dossiers were not wrong at their own cutoff.

Forecast effect: none for 14 Oct (4 Nov is 21 days after the target session), as the report says.

### Check 2. News workstream: "BSE made 0 filings on 13 Oct; no Q2 board-meeting intimation" - REFUTED (fundamentals is right)

See section 3 for the full reconciliation. Short form: the NSE `corporate-announcements` API has no "Board Meeting Intimation" category at all (zero such rows in all 1,312 BSE rows and zero among 520 market-wide filings of 13 Oct); intimations live only in `corporate-board-meetings`. The news workstream's second check used a meeting-date window (13-24 Oct) that by construction cannot contain a 4 Nov meeting.

### Check 3. Q1 FY27 outcome filing (revenue, PAT, EPS, non-operating income) - CONFIRMED

Re-read `BSE1_04082026184424_NSEIntimation.pdf` (HTTP Last-Modified 4 Aug 13:16:49 GMT = 18:46:49 IST; NSE feed `an_dt` 18:45:51). Consolidated, Rs lakh, quarter ended 30 Jun 2026 / 31 Mar 2026 / 30 Jun 2025:
- Revenue from operations 1,56,602 / 1,56,351 / 95,795 -> +63.47% YoY, +0.16% QoQ (report: +63.5%, +0.16%).
- Investment income 13,518 / 6,169 / 7,906; other income 552 / 497 / 744; total income 1,70,672 / 1,63,017 / 1,04,445.
- Net profit total operations 87,266 / 79,547 / 53,817; attributable 87,402; continuing-ops base for Q1 FY26 52,622 (so +65.8% vs continuing, +62.2% vs total, both in the report).
- EPS basic = diluted 21.22 (Q4 FY26 19.35; Q1 FY26 total ops 13.09); standalone 19.45; FY26 EPS 60.61. The footnote says EPS is "calculated on outstanding shares ... including shares held in abeyance" (supports the 21.22 vs vendor 21.40 explanation).
- Derived: non-operating income = 13,518 + 552 = 14,070 lakh = Rs 140.70 cr (Q4 FY26 66.66, Q1 FY26 86.50); other expenses 10,003 -> 6,316 (-36.9%), depreciation 5,479 -> 4,260 (-22.3%), employee 6,352 -> 8,705 (+37.0%), total expenses -3.6%, tax 29,100/1,16,366 = 25.0%, core SGF contribution 2,591. All as in the report.
- TTM EPS 13.56 + 14.61 + 19.35 + 21.22 = 68.74; 3,375.40 / 68.74 = 49.10x; market cap 3,375.40 x 407,884,077 = Rs 1,37,677 cr. Own-history percentile recomputed with my own code from `bse_daily.csv`: n = 413, current 49.1x, median 63.7x, min 44.3x (2026-10-01), max 97.2x (2025-04-29), percentile 8.2, last-250 median 61.4x, percentile 13.6 - identical to the report.
- Vendor consensus: Investing.com (in. mirror) shows 04-08-2026 EPS 21.40 vs 20.51, revenue 15.66B vs 15.97B; Q4 FY26 19.50 vs 16.38 and 15.64B vs 16.05B; Q3 FY26 14.80 vs 13.56; Q2 FY26 13.90 vs 12.71; Q1 FY26 13.09 vs 11.46. Matches the report's table. These mirrors are one feed (the report says so). 20.31 (TradingView) remains unreproduced.

### Check 4. Quality of the Q1 beat (CFO attribution) and the Rs 40 cr provision contradiction - CONFIRMED with two qualifications

- Transcript `BSE1_10082026115817_NSEIntimation.pdf` (Last-Modified 10 Aug 06:32:37 GMT = 12:02 IST): CFO: "there was a provision of about Rs. 40 crores made in our subsidiary clearing company from one of the debtors. Because of that, in previous quarter, other expenses were slightly higher." And on non-operating income: "quarter four last year ... some MTM loss we had to put, we got reversed due to ease in bond yields ... So, if you compare quarter-on-quarter, in quarter 4 last year, it was drop in invest income which has got to a large [extent] compensated in this particular quarter." Both quotes are accurate. The analyst's spelling of the speaker (Goel/Goyal) follows the transcript's own inconsistency.
- Qualification 1: "Nothing was reversed in Q1 FY27" is an inference. The CFO says the provision was booked in the previous quarter; he does not say there was no reversal. The numbers are consistent with it (Q4 other expenses 10,003 minus about 4,000 provision is about 6,000, close to Q1's 6,316), so the contradiction of the dossier claim stands, but the sentence is stronger than the quote.
- Qualification 2: the "excess" of Rs 62.2 cr over the trailing-four-quarter average is a mechanical baseline. The CFO says the Q4 drop was "to a large extent compensated", which would make the reversal closer to the Q4 shortfall (roughly Rs 16-25 cr against trend), not Rs 62 cr. I recomputed with alternative baselines: Q1 FY26 level (86.5) gives EPS ex-excess 20.23; max of last four quarters (89.9) gives 20.30; the report's average gives 20.09. All remain at or below the vendor consensus 20.31-20.51, so the *sign* of the conclusion is robust, but the "non-recurring portion" is not established. The report labels this "arithmetic, not a causal claim" (correct) and lists the reversal condition in its section 8, but the executive summary states it more firmly.

Forecast effect: none for 14 Oct (results are ten weeks old and in P0).

### Check 5. Reuters report timing correction (earliest coverage 5 Oct 20:32 IST) - PARTIALLY CONFIRMED

Confirmed:
- NiftyTrader `sebi-cas-update-30-minute-vwap-derivatives`: `datePublished` 2026-10-05T20:32:57+05:30 (`dateModified` 6 Oct 19:10:12). Outlook Money: published 6 Oct 09:04:52. I also found Business Today `...559699-2026-10-06`: published 6 Oct 07:55:34 IST ("Reuters reported, quoting two sources"), earlier than the 09:44 Business Today stamp quoted by the analyst (probably a different article), and Kotak Neo 6 Oct 11:31:31. A second NiftyTrader piece (`?p=31835`) is 6 Oct 12:49:52. No outlet I could reach carries an earlier stamp. Two searches for a Reuters/Investing/MarketScreener/Yahoo original found nothing for October.
- 5 Oct price path (15-minute bars): open 3,053, largest bar 12:15 (+1.21%, 366,612 shares vs 100,000-135,000 in the six preceding bars), close 3,179.6; 6 Oct opens 3,209.0 (+0.92% gap), close 3,305.0. The report's numbers (NSE open 3,052.0, close 3,179.6) reproduce.

Not established:
- "The +4.39% on 5 Oct therefore predates the report" (executive summary item 5, C5, section 10) is stated as fact. It rests on the absence of an earlier *secondary* article. The Reuters original was never accessed, and a Reuters "sources" story can precede a content-site write-up by hours (NiftyTrader's 16-minute explainer at 20:32 is plainly a later write-up). A pre-15:30 Reuters timestamp is exactly what the report's own section 8 says would reverse the conclusion, and that check could not be made. The 12:15 bar (+1.21% on about 2.8x volume) is an intraday jump with no identified cause.
- Supporting evidence the report did not use: on 5 Oct MCX was -0.70%, CDSL +0.60%, CAMS +0.97% (peers_daily) while on 6 Oct MCX was +4.03%, Angel One +3.44%; the Nifty Capital Markets index was +1.87% on 5 Oct and +2.41% on 6 Oct (log returns, index_daily.csv). So the exchange-sector reaction clustered on 6 Oct, which is consistent with the report reaching the market overnight. This is association only.
- Labelling slip: "+4.39%" and "+3.94%" are simple returns (3,179.6/3,046.0 - 1; 3,305.0/3,179.6 - 1); the same days in log terms are +4.29% and +3.87%, whereas the report's Appendix A says percentages are log unless marked "simple".

Suggested label: `verified_source` for "earliest secondary coverage found 5 Oct 20:32:57 IST"; `descriptive_only` / "not established" for "5 Oct move preceded the report".

### Check 6. SEBI chairman "about a week" quote; no CAS/settlement circular as of 13 Oct; the 9-day analogue - CONFIRMED

- SEBI speech PDF `.../oct-2026/1791636650448.pdf` (Last-Modified Sat 10 Oct 12:50:50 GMT = 18:20 IST): "Capital Market Confluence 2026 - Bombay Stock Exchange Brokers' Forum, Mumbai, October 10, 2026 ... Following review of the Closing Auction Session, a consultation paper was put out to address concerns in respect of settlement price of derivatives on expiry-day. We are currently examining the comments and hope to issue guidelines in about a week's time." Exact quote verified. "About a week" from Sat 10 Oct points to about 17 Oct; 14 Oct is inside the window.
- SEBI consultation paper `.../sep-2026/1789202841824.pdf` (Last-Modified Sat 12 Sep 08:47 GMT): Option 1 blended VWAP (para 3.4), Option 2 CTS VWAP (3.5), comments "latest by October 3, 2026". 
- SEBI circular listing (parsed by date, fetched after the cutoff but nothing after 13 Oct appears): newest three items dated 7 Oct (debt-market circulars), then 1 Oct, 9 Sep. No circular on CAS or derivatives settlement. The page shows no item dated after 13 Oct either. Caveat: listing pages are dated, not time-stamped, and may be cached or lag, so this supports "none dated up to 13 Oct" but cannot exclude a late-13-Oct posting.
- Analogue: FPJ `datePublished` 2026-09-04T10:45:55 IST ("SEBI said to review derivatives settlement rules"); a WebSearch summary of a Reuters-derived Investing.com item (not re-read raw) says a discussion paper "within one week"; the paper is dated 12 Sep. About 8-9 days; n = 1, as the report says.
- NSE holiday master: 20 Oct 2026 (Dussehra) is the next holiday; 14 Oct is not a holiday.

### Check 7. Earnings-reaction statistics (n = 8) and vendor "surprise" table - CONFIRMED (`descriptive_only` is the right label)

I wrote my own code (`vf/code/react_check.py`; definitions fixed before outputs; same seed as the report's disclosed 20261014) using `src/common.py` read-only:
- Reaction-day R (log, vs adjusted prev): -4.066, +2.808, +6.321, -2.039, +4.843, +6.142, -1.428, -2.332 (%). Mean |R| 3.747%, mean R +1.281%, mean |z| 1.243 (60-session sd, no look-ahead). Event z values match the report.
- Pool of non-event days 2024-11-13..2026-10-13: n = 465, pool mean |z| 0.749; random-8 5th-95th percentile 0.415-1.146; upper-tail p = 0.0236 (20,000 draws); signed test two-sided p = 0.257. Last-500 mean |R| 2.268%, sd 3.027%, up-days 53.2%; all 2,388 sessions mean +0.14%, sd 2.604%, mean |R| 1.756%, 47.8% up. All identical to the report.
- Holm over the report's family of 5 gives 0.118 for T1 (0.0236 x 5), so the conclusion "does not survive Holm" is arithmetically right. T5 was added after seeing the sign pattern; the report discloses this and counts it in the family.
- Caveat the report mostly states: n = 8 over a window with large regime and event changes (bonus 2025, CAS, index inclusion), and the non-event pool contains other news days; the test is not forecast-relevant for 14 Oct and the report says so. Three of the ten "release time" entries in section 3.1 (8 May 2024 20:45, 7 Aug 2024 17:19, 12 Nov 2024 19:05) differ from the first NSE dissemination stamps in the feed (8 May 2024 17:18:55, 7 Aug 2024 16:49:54, 12 Nov 2024 17:49:43); they look like later XBRL stamps. All are after 15:30, so the "reaction session is next day" conclusion is unaffected; the other seven match the feed to the minute.

### Check 8. 29 Sep Goldman/BNP sale of 68.33 lakh shares (overhang) - PARTIALLY CONFIRMED (matches the analyst's own V* label)

- Consistency checks I could do: Rs 2,186 cr / 68.33 lakh shares = Rs 3,199.4 per share, equal to the 29 Sep close of 3,200.00; 29 Sep volume 30,101,047 and delivery 75.21% in `bse_daily.csv`; 68.33 lakh = 22.7% of that volume; 6.83 mn = 1.67% of 407.88 mn shares. Arithmetic holds.
- Not independent: the four outlets (Kotak Neo, HDFC Sky/PTI, Goodreturns, Equentis) are one PTI story citing NSE bulk-deal data, as the analyst itself notes; the NSE record could not be read (WAF). I also could not read it. "Tuesday 29 Sep" vs "Wednesday" wording conflict remains unresolved by primary data, though the bhavcopy volume and price make 29 Sep the only consistent date.
- Forecast effect: none (10 sessions old, in P0).

### Other spot checks that passed (not counted as separate claims)

- June-2026 shareholding XBRL (Last-Modified 14 Jul 12:49:13 GMT = 18:19 IST): 407,884,077 shares; FPI 86,960,684 (21.32%); domestic institutions 98,496,537 (24.15%); LIC 22,729,500 (0.0557); "VANGUARD AND OTHERS" PAC 8,796,590.
- NSE announcements feed has the 30 Sep 11:28:54 trading-window filing, the 10 Sep IIBH stake filing and the 11 Sep SEBI approval for Mukkavilli's re-appointment, as the report cites.
- JPMorgan "overweight, target Rs 3,950": Business Today (30 Sep 09:42:50 IST) says so in one sentence; no second primary source; the stockanalysis table is stale; the news workstream calls the JPM stance unresolved. The report's V* is the most that can be said. Low forecast relevance.
- NSE PIT feed: returns 20 rows for ANGELONE and CDSL but 0 rows for BSE and MCX. Empty for both exchanges (plausible, since exchange insiders are restricted), so "no insider records" is a plausible negative but not proof of absence.

## 3. Which workstream is right, and what it implies for the NSE announcements API

**Verdict: fundamentals (01) is right; news (02) is wrong on this point.**

Evidence for the mechanism:
1. The NSE `corporate-announcements` taxonomy (`desc` field) has no "Board Meeting Intimation" value. In all 1,312 BSE rows the categories include "Outcome of Board Meeting", "Trading Window", "Financial Result Updates" etc., but none for prior intimation. Among the 520 market-wide rows of 13 Oct <= 22:00 there is likewise no such category (27 "Outcome of Board Meeting" rows only).
2. The five previous BSE intimations that the board-meetings feed shows (16 Jul 2025, 23 Oct 2025, 13 Jan 2026, 20 Apr 2026, 14 Jul 2026) have **zero** corresponding rows in the announcements feed on those dates. So the announcements feed never carried BSE's intimations; its silence on 13 Oct carries no information about them.
3. The news workstream's second test ("BSE absent from the board-meeting calendar for 13-24 Oct, 478 entries") filtered on **meeting date**. I reproduced its 478 count exactly; widening the window to 6 Nov shows BSE's two rows (4 Nov meeting, intimated 13 Oct 16:02:54 and 16:03:59). The query could not have found a 4 Nov meeting.
4. "0 filings on 13 Oct" is also literally false: the intimation PDF exists on NSE's archive with a 15:52:17 digital signature and a 16:02:57 server stamp.
5. The announcements feed has also not changed since: 1,312 rows with newest 12 Oct 15:30:27 at 13 Oct ~21:00 IST (analyst) and at 14 Oct ~13:30 IST (me). The feed is simply not where this event lives.

What survives in the news report: its substantive conclusion "no company-specific scheduled event inside the 6-session window" is still true (4 Nov is outside), and its "9 of 9 years results 2-12 Nov" base rate is consistent with 4 Nov. What must be corrected: the sentence that no intimation exists, the `verified_source` label on "BSE filed nothing on 13 Oct" (its own table row 308 flags "API may omit non-NSE-dissemination items" but the label stayed), and the downstream uncertainty item U12 ("a BSE Q2 board intimation dated <= 16 Oct"), which is already resolved.

Implications for trusting the API as a completeness source:
- **Do not treat absence in `corporate-announcements` as absence of a filing.** It is category-incomplete (no prior-intimation category) and keyed by announcement time, not meeting date. A negative needs a cross-check against the dedicated endpoints (board-meetings, event-calendar, corporate actions, shareholding, PIT/SAST) and, ideally, a direct archive PDF.
- Negatives the news workstream drew from the same feed (no news-verification, price-movement or volume-spurt notice for BSE; "0 filings") are weaker than labelled. Those specific categories do exist in the feed (8 "Spurt in Volume" and 3 "Price movement" rows market-wide on 13 Oct), so that negative is less exposed than the intimation one, but it is still a feed whose completeness was never tested.
- Positive hits from the feed are reliable (every positive I tested matched the PDFs: 4 Aug results 18:45:51, 14 Jul shareholding, 30 Sep trading window). The feed is good for dating known events, unsafe for proving that none occurred.
- For the report under verification, the exposure is small: it used the feed to *date* releases and the board-meetings feed to find the 4 Nov intimation.

## 4. Duplicate counting, over-confident labels and cutoff compliance

- Duplicate counting: row 5 (four outlets) is one PTI story, flagged V* by the analyst (fair). Row 12 (four outlets on the Reuters report) is correctly treated as one report. Rows 12, 13 and 14 plus C5 are one CAS story chain, and rows 3 and 4 are one XBRL series, so "24 distinct claims" overstates independent evidence; the verified counts (17 / 5 / 2) are not wrong, only generous in granularity.
- Over-confident phrasing: (a) "predates the report" (check 5); (b) "Nothing was reversed in Q1 FY27" (check 4); (c) row 19 JPM upgrade date "about 15 Sep" from a minor aggregator; (d) NSE premium of about 6% on vendor P/E is flagged as not primary-verified by the analyst itself.
- Cutoff compliance: no evidence of use of post-22:00 information. The report's latest cited timestamp is 13 Oct 16:03:59 (NSE board-meetings feed); items dated 13 Oct such as the SEBI listing fetch (21:38 IST) and the 15:28 stockanalysis quote are within the cutoff; the file mtime is 21:57 IST. By contrast the news workstream states its work "ran to about 22:30 IST" on live endpoints (it says it dropped items stamped after 22:00, and its 520/478 counts match mine, so the filtering was done correctly), but that workstream's SEBI RSS was "built at 22:00:02", which is at the edge of the cutoff.

## 5. What I could not verify

- Reuters original and its timestamp (blocked); NSE bulk-deal record for 29 Sep (WAF); NSE Indices' own release for the Nifty 50 change; TradingView's 20.31 consensus; PL Capital's call-derived claims; RBI/STT/Budget items (long-term relevance only, not re-read); the full list of ten historical release stamps for Q4 FY24-Q2 FY25 (see check 7).

## 6. Recommended corrections to carry into the reconcile step

1. Adopt 4 Nov 2026 (board meeting), intimation 13 Oct 16:02:54/16:03:59; delete "no intimation" and "0 filings" from the news summary.
2. Reword the 5 Oct statement to: "earliest secondary coverage found 5 Oct 20:32:57 IST; Reuters original not accessed; the 5 Oct move is not shown to be a reaction to it" and use 6 Oct as the first documented reaction day.
3. State the 5/6 Oct returns in one convention (simple +4.39% / +3.94%, or log +4.29% / +3.87%).
4. Treat the NSE announcements feed as dating evidence only, never as completeness evidence.
5. Keep the earnings-reaction and valuation percentile results as `descriptive_only` and out of the 14 Oct interval.
