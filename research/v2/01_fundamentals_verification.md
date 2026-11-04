# v2 / 01 - Fundamentals, earnings, governance: independent verification of dossiers 01 and 02

- Workstream: `fundamentals` (verification and refresh). Stock: BSE Ltd, NSE:BSE. Target session: Wed 2026-10-14. P0 = Rs 3,375.40.
- Information cutoff respected: every source below was published at or before 2026-10-13 22:00 IST. All fetches were made between about 21:00 and 21:55 IST on 13 Oct 2026 (container clock `TZ=Asia/Kolkata date` = 21:31-21:38 during the work). The latest item used is the NSE board-meeting feed entry stamped 13-Oct-2026 16:03:59 IST.
- Method rule: dossiers 01 and 02 were treated as claims. A claim is `verified_source` only if it was matched to a primary document (exchange filing, SEBI/RBI/Budget document, company filing) or to at least two outlets that do not simply copy each other. WebFetch/WebSearch return model summaries, so every number used here was re-read from the raw page or PDF fetched with curl, except where flagged "WebFetch summary".
- Labels used (from `docs/V2_BRIEF.md`): `verified_source`, `contradicted`, `unverifiable`, `descriptive_only`, `untested`, `not_found`, `validated_out_of_sample`. Nothing in this report is `validated_out_of_sample`: no predictive rule was fitted or walk-forward tested here.

---

## 0. Headline results (numbers)

1. 24 distinct claims checked against primary documents or multi-outlet evidence (table in section 2): 17 `verified_source` as stated, 5 `verified_source` with a material qualification (rows 5, 9, 12, 19, 20; row 5 is additionally `unverifiable` at the level of the NSE bulk-deal record itself), 2 `contradicted` (rows 23, 24). A further 19 corrections or qualifications to earlier statements are listed in section 6.
2. **New primary-source finding that contradicts both dossiers:** the Q2 FY27 board meeting is **Wed 4 Nov 2026** (intimation signed 15:52:17 IST, disseminated by NSE at **16:02:54 IST on 13 Oct 2026**, i.e. after the dossiers' ~15:45 cutoff). The trading window has been closed since **1 Oct** and stays closed to **6 Nov 2026 inclusive**. The dossiers said "not published, estimate 6 Nov".
3. **Primary-source correction on Q1 FY27 earnings quality.** Reported: revenue from operations Rs 1,566.02 cr (+63.5% YoY, +0.16% QoQ), total income Rs 1,706.72 cr, net profit Rs 872.66 cr (Rs 874.02 cr attributable), EPS Rs 21.22. Non-operating income (investment + other) was Rs 140.7 cr vs a trailing-four-quarter average of Rs 78.5 cr. The CFO attributes the rise to reversal of Q4 FY26 bond mark-to-market losses. Arithmetic: the Rs 62.2 cr excess adds about Rs 1.13 to EPS, so EPS "ex-excess" is about Rs 20.1 (20.3 on vendor share count) against a vendor consensus of 20.31-20.51. Revenue missed vendor consensus by 1.9% (15.66B vs 15.97B) and PL's own estimate by 1.1%.
4. The dossier statement that "a Rs 40 cr receivable provision was reversed in the quarter" is **contradicted**: per the CFO on the 4 Aug call, the Rs 40 cr provision was booked in the *previous* quarter (Q4 FY26), in the clearing-corporation subsidiary, and inflated that quarter's other expenses. Nothing was reversed in Q1 FY27.
5. **Reuters-report timing:** the earliest public coverage found is stamped 5 Oct 2026 20:32 IST, after the 15:30 close. The +4.39% on Mon 5 Oct (NSE open 3,052.0 -> close 3,179.6; the whole move was done intraday) therefore predates the report. The +3.94% on 6 Oct (gap-up open 3,209.0 vs prior close 3,179.6, +0.92%) is consistent with it. Dossier 02 groups the three sessions as one reaction.
6. The SEBI chairman's "about a week" quote is verified in SEBI's own speech text (10 Oct 2026). As of 21:38 IST on 13 Oct, SEBI's circular list still ends at 7 Oct (no CAS/settlement circular). The one comparable earlier promise ("within a week", reported 4 Sep 10:45 IST) was delivered 12 Sep, about 9 days later (n = 1).
7. Earnings reactions (next session after an after-hours release, n = 8, Q2 FY25 to Q1 FY27): mean |R| = 3.75% vs 2.27% for all sessions of the last 500; mean |z| = 1.24 vs 0.75 for random non-event days (permutation p = 0.024 raw, Holm-adjusted 0.118 over 5 tests). Signed mean R = +1.28% (p = 0.25). `descriptive_only`.
8. Valuation recomputed from primary EPS: TTM EPS Rs 68.74 -> **49.1x**; 8th percentile of 413 sessions of its own TTM-P/E history (Feb 2025 to Oct 2026; median 63.7x, min 44.3x on 1 Oct 2026). Dossier's own-history P/E series is not reproducible for three of six quarter-ends.

---

## 1. Access log (what worked, what failed)

| Source | Result | Note |
|---|---|---|
| `nsearchives.nseindia.com` PDFs/XBRL | works | Needs `curl --http1.1` and a browser User-Agent; default HTTP/2 returns `INTERNAL_ERROR (err 2)`. |
| `www.nseindia.com/api/corporate-announcements?index=equities&symbol=BSE` | works (1,312 items, 2017-02-14 to 2026-10-12 15:30:27) | Primary exchange feed, carries NSE dissemination timestamps (`exchdisstime`). |
| NSE `corporate-board-meetings`, `event-calendar`, `corporate-share-holdings-master`, `corporates-corporateActions`, `corporates-financial-results` | work | `corporates-financial-results` stops at Q3 FY25 (NSE moved to integrated filing). `corporates-pit`, `corporate-sast-reg29`, `corporate-pledgedata` return empty `data` for BSE. |
| `www.nseindia.com/api/snapshot-capital-market-largedeal` | works for 13 Oct only | No BSE entry in bulk or block lists; one short-deal row (6 shares, 12 Oct). |
| NSE `/api/historical/bulk-deals`, `/api/historical/cm/bulkblock` | **fails** | WAF returns an HTML block page (22 KB) even with cookies. The 29 Sep bulk-deal record could not be read from NSE itself. |
| `nseindia.com` root, `/api/quote-equity`, `api.bseindia.com` | 403 | `bseindia.com` home loads but is a script shell. |
| `archives.nseindia.com` FY26 annual report (15.3 MB) | works | |
| `sebi.gov.in` listings, circular PDF, consultation-paper PDF, speech PDF, annual-report chapter | work | |
| `rbi.org.in` press release 30 Mar 2026 and revised Directions text | works | |
| `indiabudget.gov.in` Budget speech and Finance Bill PDFs | work | |
| News/aggregator pages via curl (Kotak Neo, HDFC Sky, Goodreturns, Business Today, Outlook Money/Business, IANS via Punjab Kesari, NiftyTrader, 5paisa, Groww, Upstox, FPJ, Angel One, Bajaj, Equentis, stockanalysis, Trendlyne, TradingEconomics, PL Capital PDF) | work | Publication timestamps read from `datePublished` meta tags. |
| Investing.com earnings table | curl 403; **WebFetch works on `ca.`, `ng.`, `in.investing.com/equities/bse-ltd-earnings`** | Three mirrors returned identical numbers; they are one feed, not independent. Treated as WebFetch summaries (re-checked row by row against filings for the actuals). |
| TradersUnion earnings page, TipRanks, MarketScreener | 403 | TradersUnion figures exist only as a WebSearch summary (flagged "snippet"). |
| Yahoo `quoteSummary` / `timeseries` | 429 | No earnings-estimate history from Yahoo. |
| TradingView | not fetched | Brief forbids it. The TradingView numbers come only from `data/raw/tradingview/public_page_NSE-BSE_summary_2026-10-13.md`. |
| Reuters original | not accessed | Only syndicated/derivative coverage was available. |

---

## 2. Verification table (claims from dossiers 01 and 02)

Verdict key: V = verified_source; V* = verified with a material qualification; C = contradicted; U = unverifiable at primary level.

| # | Claim (dossier) | Verdict | Evidence (primary first) | URL | Published (IST) | Event date |
|---|---|---|---|---|---|---|
| 1 | Q1 FY27: revenue from ops Rs 1,566 cr (+63.5% YoY), total income Rs 1,707 cr, PAT Rs 872.7 cr, EPS 21.22 (01 R-1) | V | BSE outcome filing. Consolidated Rs lakh: revenue 1,56,602 (vs 95,795 Q1 FY26 restated); total income 1,70,672; net profit total ops 87,266 (attributable 87,402); EPS 21.22 basic = diluted. Standalone EPS 19.45. Reconciles: +65.8% is vs continuing-ops base 52,622; +62.2% vs total-ops base 53,817 | https://nsearchives.nseindia.com/corporate/BSE1_04082026184424_NSEIntimation.pdf | 2026-08-04 18:45:51 (NSE feed `an_dt`) | 2026-08-04 (board 15:50-17:30) |
| 2 | Results released after market hours (01, results_dates.csv "pattern") | V | NSE `exchdisstime` for all ten results since May 2024 is after 15:30; list in section 3.2 | NSE feed above | see 3.2 | |
| 3 | June-2026 shareholding: FPI 21.3%, DII 24.2%, LIC 5.57% (01 G-1, G-2) | V | SEBI-format XBRL: 407,884,077 shares; FPI 86,960,684 = 21.32% (Cat I 20.08%, Cat II 1.24%); domestic institutions 98,496,537 = 24.15% (MF 11.69%, insurance 11.85%, banks 0.06%); LIC 22,729,500 = 5.57%; non-institutions 54.45%; promoters none; "Vanguard and others" PAC 8,796,590 = 2.16% (not in dossier) | https://nsearchives.nseindia.com/corporate/xbrl/SHP_1692530_14072026061904_WEB.xml | 2026-07-14 18:19:08 | 2026-06-30 |
| 4 | FPI trend 16.3 / 17.5 / 19.4 / 21.3% (Sep-25 to Jun-26) (01 G-1) | V | Same XBRL series: 16.25, 17.45, 19.42, 21.32 | SHP_1550037_..., SHP_1604968_..., SHP_1652898_... under the same path | 2025-10-16 to 2026-07-14 | quarter-ends |
| 5 | Goldman Sachs Investments Mauritius I and BNP Paribas Financial Markets sold 68.33 lakh shares (1.67%, about Rs 2,186 cr); UTI MF and Nippon MF bought 52.43 lakh | V* (U at NSE-record level) | Four outlets citing NSE bulk-deal data: Kotak Neo (30 Sep 12:37), HDFC Sky/PTI (30 Sep 12:21), Goodreturns (30 Sep 12:57), Equentis (30 Sep 14:56). PTI says BNP "sold 44.51 lakh shares on **Tuesday**" (29 Sep). Cross-check from our NSE bhavcopy: 29 Sep volume 30,101,047 shares (turnover Rs 9,578.6 cr, delivery 75.2%), close 3,200.00 = deal price. NSE historical bulk-deal API blocked, so the NSE record itself was not read | https://hdfcsky.com/news/bnp-paribas-goldman-sachs-sell-nearly-1-7-pc-stake-in-bse-for-rs-2186-cr-stock-falls-nearly-4-pc ; https://www.kotakneo.com/news/stocks/bse-shares-fall-after-goldman-sachs-bnp-paribas-stake-sale/ ; https://www.goodreturns.in/news/bse-shares-fall-nearly-4-after-bnp-paribas-goldman-sachs-sell-nearly-1-7-stake-worth-rs-2186-cr-1538231.html | 2026-09-30 | 2026-09-29 |
| 6 | BSE joins Nifty 50 replacing Wipro; effective after close 29 Sep (from 30 Sep); 6-month avg free-float mcap Rs 1,40,879 cr vs Rs 55,930 cr | V | Angel One (11 Aug 10:43), FPJ (11 Aug 13:16), Bajaj Broking (11 Aug): all cite NSE Indices. NSE Indices' own release not fetched. Announcement time on 10 Aug not established (BSE rose +4.02% on 10 Aug; cause unknown) | https://www.angelone.in/news/market-updates/bse-to-enter-nifty-50-replace-wipro-from-september-30-2026 ; https://www.freepressjournal.in/business/bse-replacing-wipro-in-nifty-50-what-it-means-for-shareholders | 2026-08-11 | announced ~2026-08-10; effective 2026-09-29 close |
| 7 | NSE (exchange) listed 24 Sep 2026 at Rs 1,800 vs issue price Rs 1,785 (band 1,700-1,785; OFS 12,64,36,650 shares; Rs 22,561.57 cr; 5.71x) | V | HDFC Sky 10:31, Groww 11:09, 5paisa 11:47, Kotak Neo 13:38 agree on 1,800 / 1,785 / 0.84% / 5.71x. Intraday high differs by timestamp (1,839 at 10:02; 1,845; 1,878) | https://hdfcsky.com/news/nse-ipo-shares-list-at-rs-1800-on-bse-0-84-percent-above-rs-1785-issue-price ; https://www.5paisa.com/blog/nse-shares-make-flat-market-debut-list-at-rs1800-on-bse | 2026-09-24 | 2026-09-24 |
| 8 | STT hike in Budget 1 Feb 2026, effective 1 Apr 2026: futures 0.02->0.05%, options premium 0.10->0.15%, exercise 0.125->0.15% (02 R9) | V (primary) | Budget speech para 140; Finance Bill 2026 memorandum clause 143: "These amendments will take effect from 1st April, 2026". Dossier conflict D-9 (Outlook Money "from 0.01%") is wrong: old futures rate was 0.02% | https://www.indiabudget.gov.in/doc/budget_speech.pdf ; https://www.indiabudget.gov.in/doc/Finance_Bill.pdf | 2026-02-01 | effective 2026-04-01 |
| 9 | RBI circular on bank funding of proprietary trading: issued 13 Feb 2026, effective 1 Jul 2026 after deferral from 1 Apr (02 R10) | V* | RBI press release: Directions issued 13 Feb 2026, "extend the effective date ... to July 1, 2026". Revised Directions RBI/2025-26/254 dated 30 Mar 2026 "come into force from July 1, 2026, or an earlier date when adopted by a bank" and supersede the 13 Feb text. **Qualification:** para 219Z bars *credit facilities* for own-account/prop trading, but para 219ZA allows *guarantees* for prop trading if fully secured by cash/equivalents/G-Secs with at least 50% cash/FD; paras 219X-219Y: guarantees issued for brokers/clearing members to exchanges or clearing houses (security deposits, margins) need at least 50% collateral of which 25% cash. The press release words it as "financing ... for proprietary trading may be undertaken against 100% collateral comprising of cash or cash equivalents". "No bank funding of prop trading" (02 R10, 01 M-11) is an over-simplification. Dossier 01 M-11 guarantee terms (100% collateral, at least 50% cash) are correct for prop guarantees | https://www.rbi.org.in/scripts/BS_PressReleaseDisplay.aspx?prid=62476 ; https://www.rbi.org.in/scripts/BS_CircularIndexDisplay.aspx?Id=13346 | 2026-03-30 | 2026-02-13 / 2026-07-01 |
| 10 | SEBI closing auction session (CAS) live 3 Aug 2026 (02 R1) | V (primary) | SEBI circular HO/47/11/11(3)2025-MRD-POD2/I/2765/2026 dated 16 Jan 2026, para 6.1: "implemented in the cash segment from August 03, 2026"; auction 15:15-15:35 pm, phased, initially stocks with F&O. Confirmed by SEBI's 12 Sep consultation paper para 1.1. Our data: `last == close` in every session since 3 Aug (audit F11) | https://www.sebi.gov.in/legal/circulars/jan-2026/introduction-of-closing-auction-session-cas-in-the-equity-cash-segment-and-certain-modifications-in-the-pre-open-auction-session_99122.html | 2026-01-16 | 2026-08-03 |
| 11 | SEBI consultation paper 12 Sep 2026; comments to 3 Oct; Option 1 blended VWAP vs Option 2 CTS-VWAP interim for at least one year (02 R5) | V (primary) | Paper text para 3.4, 3.5, 7.1 ("latest by October 3, 2026"); "Issued on: September 12, 2026" | https://www.sebi.gov.in/sebi_data/attachdocs/sep-2026/1789202841824.pdf | 2026-09-12 | 2026-09-12 |
| 12 | Reuters report 5-6 Oct: SEBI likely to stop using CAS for derivatives settlement for at least a year, last-30-min VWAP, by end-October (02 R6) | V as a *report*; timing C | Coverage: NiftyTrader (published **5 Oct 20:32**), Outlook Money (6 Oct 09:04), Business Today (6 Oct 09:44), Kotak Neo (6 Oct 11:31); all cite Reuters and "two sources". Reuters original not accessed. It is not an official decision. **Timing correction:** earliest coverage is after the 5 Oct close, so the +4.39% on 5 Oct is not a reaction to it (see section 6 C5) | https://www.niftytrader.in/markets/sebi-cas-update-30-minute-vwap-derivatives/ ; https://www.outlookmoney.com/invest/sebi-likely-to-suspend-closing-auction-session-mechanism-for-derivatives-settlement-revert-to-vwap-for-a-year | 2026-10-05 20:32 / 2026-10-06 09:04 | 2026-10-05 |
| 13 | SEBI chairman 10 Oct: "hope to issue guidelines in about a week's time" (02 R7) | V (primary) | SEBI's own speech text: "We are currently examining the comments and hope to issue guidelines in about a week's time." Also IANS (10 Oct 20:31) and Outlook Money (11 Oct 14:06). Event: BSE Brokers' Forum Market Confluence 2026, Mumbai, Saturday | https://www.sebi.gov.in/sebi_data/attachdocs/oct-2026/1791636650448.pdf | 2026-10-10 | 2026-10-10 |
| 14 | No CAS/settlement circular issued as of 13 Oct (02 R8) | V | SEBI circular list fetched 21:38 IST: latest items 7 Oct (debt); press list latest 13 Oct (refund notice) and 10 Oct (speech); orders list latest 13 Oct (not BSE Ltd) | https://www.sebi.gov.in/sebiweb/home/HomeAction.do?doListing=yes&sid=1&ssid=7&smid=0 | fetched 2026-10-13 21:38 | |
| 15 | Jefferies Hold -> Underperform, TP Rs 2,940 (from 3,520), 17 Aug | V | Business Today (17 Aug 09:28), Upstox (17 Aug 11:24), S&P/stockanalysis forecast table ("Jefferies Downgrades 3,520 -> 2,940, Aug 17, 2026") | https://www.businesstoday.in/markets/stocks/story/bse-shares-jefferies-downgrades-rating-to-underperform-lowers-target-price-549492-2026-08-17 | 2026-08-17 | 2026-08-17 |
| 16 | Nuvama Buy -> Hold, TP Rs 3,240 (-21%), FY27/FY28 EPS -6.3% / -15%, 18 Aug | V | Business Today (18 Aug 14:18), Outlook Business (18 Aug 17:08) | https://businesstoday.in/markets/stocks/story/bse-shareholders-in-a-fix-two-downgrades-in-two-days-where-is-the-stock-headed-549789-2026-08-18 | 2026-08-18 | 2026-08-18 |
| 17 | Bernstein initiates Underperform, TP Rs 2,820, 32x FY28E EPS, 9 Sep | V | Business Today (9 Sep 10:12, citing Bloomberg): about 9% below consensus on 2Q FY27 volumes, 2-4% below on FY27-29 EPS | https://www.businesstoday.in/markets/stocks/story/bse-share-price-falls-4-after-bernsteins-underperform-mcx-shares-up-for-3rd-day-554147-2026-09-09 | 2026-09-09 | 2026-09-09 |
| 18 | Macquarie initiates Outperform, TP Rs 4,000 (40x FY29E), 24 Sep | V | Business Today (30 Sep) quotes Macquarie "on September 24"; India Infoline (24 Sep) and Equentis (30 Sep) agree | https://www.businesstoday.in/markets/trending-stocks/story/bse-shares-enter-nifty-club-stock-tanks-4-what-consensus-target-suggests-558670-2026-09-30 | 2026-09-30 | 2026-09-24 |
| 19 | JPMorgan upgrade to Overweight, TP Rs 3,950 (from 4,090), about 15 Sep | V* | Streamline Feed (15 Sep 10:21 IST, minor aggregator) and Business Today 30 Sep ("JPMorgan ... overweight with a target of Rs 3,950"). S&P-based stockanalysis table is stale: still shows J.P. Morgan "Hold, Maintains 4,090, Aug 6" | same Business Today URL | 2026-09-15 / 2026-09-30 | ~2026-09-15 |
| 20 | Auditor: S.R. Batliboi continues; KKC & Associates LLP approved 4 Aug 2026 for 5 years (01 G-7) | V* | Outcome-of-board filing Annexure B: Batliboi "will continue ... until the conclusion of the 22nd AGM to be held in 2027, marking completion of their second term"; KKC for five years "from the conclusion of the 22nd AGM (FY2027-28) till the conclusion of the 27th AGM (FY2032-33), subject to approval of the Shareholders". **Dossier's claim that the change "needs another route (e.g. postal ballot)" and is pending now is not supported:** nothing is pending before the 2027 AGM cycle | https://nsearchives.nseindia.com/corporate/BSE1_04082026184424_NSEIntimation.pdf | 2026-08-04 18:45 | 2026-08-04 |
| 21 | CEO Sundararaman Ramamurthy: in office since Jan 2023, 5 years or age 65 (01 G-6) | V (primary) | Board outcome 8 Dec 2022: appointed "for a period of 5 years or till he attains the age of 65, whichever is earlier"; 30 Dec 2022 filing: assumes office **4 Jan 2023**; SEBI approval letter 28 Nov 2022. Tenure at 14 Oct 2026 = 3.78 years; term cannot run past 3 Jan 2028. Predecessor Ashishkumar Chauhan resigned 25 Jul 2022 | https://nsearchives.nseindia.com/corporate/BSE_08122022132730_NSEIntimation.pdf ; https://nsearchives.nseindia.com/corporate/BSE_30122022175513_NSEIntimation.pdf | 2022-12-08 / 2022-12-30 | 2023-01-04 |
| 22 | Dividend and bonus history (01 B-6, B-7) | V (primary) | NSE corporate-actions feed: Rs 10 (ex 10 Jul 2026); Rs 23 (ex 14 May 2025; 18 regular + 5 special per 6 May 2025 outcome); bonus 2:1 ex/record 23 May 2025 (board 30 Mar 2025, postal ballot 9 May 2025, allotment 26 May 2025); Rs 15 (ex 14 Jun 2024); Rs 12 (ex 4 Aug 2023); buyback record 14 Sep 2023; Rs 13.50 (ex 23 Jun 2022); bonus 2:1 ex 21 Mar 2022. Last interim dividend Dec 2018. Post-2025-bonus equivalents: 10.00, 7.67, 5.00, 4.00, 4.50 | https://www.nseindia.com/api/corporates-corporateActions?index=equities&symbol=BSE | fetched 2026-10-13 | |
| 23 | Q2 FY27 results date "NOT announced; estimate 6 Nov" (01 R-13, 02 section c) | **C** | Board meeting **Wed 4 Nov 2026** to approve results for the quarter and half year ended 30 Sep 2026; trading window closed 1 Oct to 6 Nov inclusive | https://nsearchives.nseindia.com/corporate/BSE1_13102026160203_NSEIntimation.pdf | 2026-10-13 16:02:54 | 2026-11-04 |
| 24 | Rs 40 cr receivable provision "reversed in the quarter" (01 R-2) | **C** | Call transcript (CFO Deepak Goel): "a provision of about Rs. 40 crores made in our subsidiary clearing company from one of the debtors. Because of that, in previous quarter, other expenses were slightly higher." Q4 FY26 other expenses Rs 100.0 cr -> Q1 FY27 Rs 63.2 cr | https://nsearchives.nseindia.com/corporate/BSE1_10082026115817_NSEIntimation.pdf | 2026-08-10 12:00 | call 2026-08-04 |

Additional primary-source checks that passed (not counted above): FY26 consolidated revenue from operations Rs 4,833.95 cr, total income Rs 5,148.10 cr, net profit Rs 2,487.25 cr, EPS Rs 60.61 (FY26 column of the Q1 FY27 filing); Q1 FY27 cash ADTO Rs 9,955 cr (99,553 mn), equity-derivatives premium ADTO Rs 29,615 cr (296,154 mn, +96% YoY, +2.4% QoQ), transaction charges Rs 1,327.7 cr (+80% YoY, +1% QoQ), treasury income 400 mn, listing 1,007 mn (-4% YoY, -15% QoQ), other operating income 977 mn (+40%) (investor presentation 4 Aug 18:55); IIBH stake plan (50 crore shares, Rs 50.50 cr, SEBI approval 13 Jul 2026); market-data licensing moves in-house from 1 Jan 2027 (BSE media release 29 Jun 2026); AGM 19 Aug 2026 votes (accounts and Rs 10 dividend 99.9992% in favour; Mukkavilli re-appointment 83.37% for, 16.63% against); 52-week range 2,326.10 (31 Oct 2025, intraday) to 4,446.80 (27 May 2026) recomputed from NSE bhavcopy; dossier 02's 65-session close series and daily % changes (13 Jul to 13 Oct) match `bse_daily.csv` for 65 of 65 sessions.

---

## 3. Earnings: last eight quarters

### 3.1 Reported results (consolidated, Rs crore, latest restated figures in later filings; EPS on the post-2025-bonus basis)

| Quarter | Release (NSE dissemination, IST) | Revenue from ops | YoY | Total income | Net profit (total ops) | EPS reported | Source filing |
|---|---|---|---|---|---|---|---|
| Q2 FY25 (Sep-24) | 12 Nov 2024 19:05 | 740.73 (orig 746.32) | | 812.63 (orig 818.98) | 345.77 | 8.42 (25.25 / 3) | NSE XBRL; restated in Nov-25 filing |
| Q3 FY25 (Dec-24) | 6 Feb 2025 18:13 (results) / 18:55 (XBRL) | 768.10 (orig 773.54) | | 829.35 | 218.59 | 5.33 (16.00 / 3) | NSE XBRL; Feb-26 filing |
| Q4 FY25 (Mar-25) | 6 May 2025 18:51 | 846.64 | | 926.38 | 493.67 | 12.00 | May-26 filing comparative |
| Q1 FY26 (Jun-25) | 7 Aug 2025 18:18 | 957.95 (orig 958.39) | | 1,044.45 | 538.17 | 13.09 | Aug-25 / Aug-26 filings |
| Q2 FY26 (Sep-25) | 11 Nov 2025 18:02 | 1,068.39 | +44.2% | 1,139.53 | 557.02 | 13.56 | Nov-25 filing |
| Q3 FY26 (Dec-25) | 9 Feb 2026 18:40 | 1,244.10 | +62.0% | 1,333.95 | 596.59 | 14.61 | Feb-26 filing |
| Q4 FY26 (Mar-26) | 7 May 2026 17:36 | 1,563.51 | +84.7% | 1,630.17 | 795.47 | 19.35 | May-26 filing |
| Q1 FY27 (Jun-26) | 4 Aug 2026 18:45 | 1,566.02 | +63.5% | 1,706.72 | 872.66 | 21.22 | Aug-26 filing |

Earlier: Q4 FY24 released 8 May 2024 20:45, Q1 FY25 7 Aug 2024 17:19 (consolidated PAT Rs 106.89 cr for Q4 FY24 per XBRL; EPS 7.79 pre-2025-bonus = 2.60). Original (pre-restatement) revenue/total income differ from restated figures because BSE Institute was moved to discontinued operations. QoQ revenue growth in Q1 FY27 was +0.16% (Q4 FY26: +25.7%), the slowest in the series shown (next slowest: Q3 FY25 at +3.7%). Attributable profit: Q1 FY27 Rs 874.02 cr.

All ten release times are after the 15:30 close, so the reaction session is always the next trading day. This upgrades the `after_market_evidence` column of `data/results_dates.csv` from "pattern" to "confirmed by NSE dissemination time" for Q2 FY25, Q4 FY25 and Q1 FY26, and adds the missing Q3 FY25 (6 Feb 2025) release.

### 3.2 Consensus vs actual (Investing.com table via WebFetch on three mirrors; revenue "actual" matches BSE filings as originally reported)

Revenue in INR billion. EPS "actual" on the vendor's own share-count basis (differs from company-reported EPS; see 3.3). Only the five quarters whose EPS forecast is on the post-bonus basis are used for EPS; for Q2 FY25, Q4 FY25, Q1 FY25 the vendor forecast is pre-bonus (22.05, 32.17, 19.60 vs actual 8.43, 12.03, 6.53) and for Q3 FY25 there is no EPS forecast, so those surprises are **not computable** from this source (dividing by 3 would give +14.7%, +12.2%, 0.0%, but that rescaling is an unverified assumption).

| Quarter | Revenue actual / forecast | Revenue surprise | EPS vendor actual / forecast | EPS surprise (vendor) | EPS surprise (company-reported) | Next-session R (log, vs adj. prev close) | Nifty 50 same day | Gap G | Intraday I |
|---|---|---|---|---|---|---|---|---|---|
| Q2 FY25 | 7.46 / 7.35 | +1.50% | n/c | n/c | n/c | -4.07% (13 Nov 2024) | -1.37% | +1.26% | -5.33% |
| Q3 FY25 | 7.74 / 7.30 | +6.03% | n/a | n/a | n/a | +2.81% (7 Feb 2025) | -0.18% | -1.22% | +4.03% |
| Q4 FY25 | 8.47 / 8.40 | +0.83% | n/c | n/c | n/c | +6.32% (7 May 2025) | +0.14% | +1.98% | +4.34% |
| Q1 FY26 | 9.58 / 9.67 | -0.93% | 13.09 / 11.46 | +14.22% | +14.22% | -2.04% (8 Aug 2025) | -0.95% | +2.34% | -4.38% |
| Q2 FY26 | 10.68 / 10.50 | +1.71% | 13.90 / 12.71 | +9.36% | +6.69% | +4.84% (12 Nov 2025) | +0.70% | +4.65% | +0.19% |
| Q3 FY26 | 12.44 / 12.38 | +0.48% | 14.80 / 13.56 | +9.14% | +7.74% | +6.14% (10 Feb 2026) | +0.26% | +4.10% | +2.04% |
| Q4 FY26 | 15.64 / 16.05 | -2.55% | 19.50 / 16.38 | +19.05% | +18.13% | -1.43% (8 May 2026) | -0.62% | 0.00% | -1.43% |
| Q1 FY27 | 15.66 / 15.97 | -1.94% | 21.40 / 20.51 | +4.34% | +3.46% | -2.33% (5 Aug 2026) | +0.04% | +1.27% | -3.60% |

(n/c = not computable on a consistent basis; n/a = no forecast shown.) Earlier events for context: Q4 FY24 (reaction 9 May 2024) R = -3.95%; Q1 FY25 (8 Aug 2024) R = +8.06% (gap +10.23%).

Second vendor (TradersUnion, WebSearch summary only, page itself 403): EPS actual vs estimate Q1 FY27 21.22 vs 20.45 (+3.8%), Q4 FY26 19.69 vs 17.49 (+12.6%), Q3 FY26 14.80 vs 14.43 (+2.6%), Q2 FY26 13.57 vs 12.75 (+6.4%), Q1 FY26 13.09 vs 11.54 (+13.4%). Same sign (beat) in 5 of 5, but estimate levels differ by up to Rs 1.1 (Q4 FY26: 16.38 vs 17.49). Consensus is vendor-dependent; magnitudes of "surprise" are not reliable, signs are.

Broker check for Q1 FY27 (PL Capital, 5 Aug 2026, primary broker document): actual vs PL estimate: revenue from ops 15,660 vs 15,838 mn (-1.1%); other income 1,407 vs 897 (+56.8%); PAT 8,727 vs 8,515 (+2.5%); EPS 21.2 vs 20.7 (+2.3%). PL's other-income overshoot (Rs 51 cr pre-tax, about Rs 38 cr after 25% tax) exceeds its whole PAT overshoot (Rs 21 cr).

### 3.3 The TradingView claim (Q1 FY27 EPS 21.40 vs 20.31 estimate, +5.38%; revenue 15.66B vs 15.97B)

- Arithmetic: 21.40 / 20.31 - 1 = +5.37%. Correct.
- Actual EPS 21.40: reproduced by Investing.com (21.40) but **not the company's reported EPS (21.22)**. BSE's EPS note: "calculated on outstanding shares issued ... including shares held in abeyance"; implied denominator 87,402 lakh / 21.22 = 411.9 mn vs 407.88 mn listed shares. The vendor appears to divide by the listed count (872.66 cr / 407.88 mn = 21.39). `unverifiable` as a company figure; `verified_source` as a vendor figure.
- Estimate 20.31: **not reproduced**. Investing.com shows 20.51; TradersUnion 20.45. Surprise range on vendor actual 21.40: +4.3% to +5.4%; on company-reported 21.22: +3.5% to +4.5%.
- Revenue: actual 15.66B = Rs 1,566.02 cr (primary); forecast 15.97B reproduced by Investing.com. Miss of 1.9% (PL's own estimate: -1.1%).
- Link to the dossiers: dossier 01 reports "EPS 21.22" correctly; the TradingView page gives 21.40 because of the share-count basis, not a data error in the filing.

### 3.4 Quality of the Q1 FY27 beat (arithmetic, not a causal claim)

| Item (Rs crore) | Q1 FY26 | Q2 FY26 | Q3 FY26 | Q4 FY26 | Q1 FY27 |
|---|---|---|---|---|---|
| Investment income + other income (total income - revenue from ops) | 86.5 | 71.1 | 89.9 | 66.7 | **140.7** |

Trailing-four-quarter average 78.5; excess in Q1 FY27 = 62.2 cr pre-tax; effective tax 25.0% -> 46.6 cr after tax -> Rs 1.13 per share on the reported-EPS denominator (Rs 1.14 on the listed count). EPS excluding the excess is about Rs 20.1 (reported basis) or 20.3 (vendor basis), 1-2% below the 20.31-20.51 consensus. Management (CFO, call): "in quarter four last year ... some MTM loss we had to put, we got reversed due to ease in bond yields in this particular [quarter]", and the combined line "moved from Rs 67 crores ... to Rs 140.7 crores".

Other Q1 FY27 composition facts (primary): total expenses Rs 536.69 cr (-3.6% QoQ), of which other expenses -37% QoQ (Q4 carried the Rs 40 cr provision), depreciation -22% QoQ (CFO: WDV reset at the start of the financial year, so Q1 depreciation is seasonally low), employee cost +37% QoQ; core-SGF contribution Rs 25.9 cr vs PL's Rs 53.8 cr estimate; tax rate 25.0%.

Forward-looking caveat for Q2 FY27 (4 Nov; **not** next-session relevant): India's 10-year yield was about 6.87% on 21 Aug (TradingEconomics: "near two-month high"), about 7.18% on 28 Sep and about 7.29% on 7 Oct. The 30 Jun level was not obtained. If BSE's bond book is marked to market the way the CFO described, a Q2 reversal of the Q1 gain is plausible. Inference only; portfolio size and duration are undisclosed (`untested`).

### 3.5 Does the reaction depend on the surprise? (all tests pre-defined in code comments before outcomes were viewed; family of 5; Holm)

| Test | Definition | n | Statistic | Raw p | Holm p |
|---|---|---|---|---|---|
| T1 magnitude | mean abs z of reaction-day R, z = R / sd of R over the 60 prior sessions; null = 8 random non-event days from 2024-11-13 to 2026-10-13 (pool 465 days, 20,000 draws) | 8 | 1.243 vs pool mean 0.749 (random-8 5th-95th pct: 0.42-1.15) | 0.0236 | 0.118 |
| T2 signed | mean R of the 8 reaction days vs same draws, two-sided | 8 | +1.281% vs +0.140% | 0.253 | 0.759 |
| T3 | Spearman rho between revenue surprise and R, exact permutation | 8 | rho = 0.262 | 0.536 | 1.0 |
| T4 | Spearman rho between EPS surprise (vendor) and R | 5 | rho = 0.100 | 0.950 | 1.0 |
| T5 (added after seeing the sign pattern; counted in the family) | Fisher exact: sign(revenue surprise) vs sign(R) | 8 | 7 of 8 signs agree (table [[4,1],[0,3]]) | 0.143 | 0.571 |

Reading: results sessions are larger in magnitude than ordinary sessions (mean |R| 3.75% over the eight, vs 2.27% for all sessions of the last 500), but the evidence does not survive Holm at 5%, and the sign of the move is not predicted by the EPS surprise (EPS beat 5 of 5 times; the stock fell in 3 of those 5). The only visible pattern is that all three revenue misses inside the window (Q1 FY26, Q4 FY26, Q1 FY27) were followed by declines. n = 8, so the effective information is tiny. Status: `descriptive_only`. Exceptions: Q2 FY25 (revenue beat, stock -4.07%); outside the window, Q1 FY25 (revenue -0.16% vs forecast, stock +8.06% with a +10.23% gap).

Unconditional baseline R over the sample (all 2,388 sessions): mean +0.14%, sd 2.60%, mean |R| 1.76%, 47.8% up days; last 500: mean +0.19%, sd 3.03%, mean |R| 2.27%, 53.2% up. Dossier numbers for next-day reactions (simple %): Q1 FY27 -2.31, Q4 FY26 -1.42, Q3 FY26 +6.33, Q2 FY26 +4.96, Q1 FY26 -2.02, Q4 FY25 +6.53, Q3 FY25 +2.85, Q2 FY25 -3.98 all reproduce from `bse_daily.csv`.

---

## 4. Governance, litigation, regulatory orders, related-party and insider items

New or contradicting the dossiers (all from NSE filings unless stated):

1. **Senior-management and board changes in 2026** (dossier 01 G-6: "no leadership change found in 2026"). CEO (Ramamurthy), CFO (Deepak Goel) and company secretary (Vishal Bhat) are unchanged. Below them, after the amended SECC Regulations of 21 Nov 2025: Viral Davda re-designated CIO -> CTO (17 Dec 2025); change in Chief Risk Officer (9 Feb 2026); cessation of Vivek Garg and Prahlad Salian as KMP/senior management (1 Apr 2026); Gopalan S. Raghavan appointed Executive Director, Vertical 2 (regulatory, compliance, risk, investor grievance) from 18 Jun 2026 until age 65; Kamala Kantharaj resigned as Chief Regulatory Officer (29 May) and re-designated Chief - Special Duty; Geetha Gangadharan Chief Regulatory Officer from 5 Jun; Saurabh Shukla appointed Executive Director, Vertical 1 (critical operations) for 5 years from 4 Sep 2026 (both Executive Director appointments ratified by postal ballot, scrutiniser's report filed 24 Jul 2026); names for Executive Director Vertical 3 submitted to SEBI (pending); Dr Padmini Srinivasan re-appointed PID for 3 years from 14 Feb 2026 (SEBI letter 16 Dec 2025); SEBI approved Jagannath Mukkavilli's re-appointment on 11 Sep 2026 after 16.63% votes against at the AGM (17.72% against among institutions). Effect on earnings: none identified. Pending item: Vertical 3 ED approval, informational.
2. **GST order (not in the dossiers).** Order under section 73 CGST Act from the Mumbai South Commissionerate (received 16 Dec 2025; period Apr 2021-Mar 2022; alleged excess input tax credit): GST Rs 6,59,26,901 + penalty Rs 65,92,690 = **Rs 7.25 cr**, interest not quantified; appeal filed 6 Mar 2026 (FY26 annual report). Immaterial (0.3% of FY26 net profit).
3. SEBI orders (annual report FY26 and NSE filings): Rs 3 cr (12 Apr 2022, Karvy-related inspection) stayed by SAT, appeal pending; Rs 3 lakh (29 Jul 2022) set aside by SAT on 2 May 2025; Rs 25 lakh (25 Jun 2025, inspection period Feb 2021-Sep 2022) paid; show-cause on clearing-corporation interoperability disposed 15 May 2025 without penalty. No 2026 SEBI order, show-cause or penalty against BSE Ltd found in SEBI's orders/press lists or a targeted web search. The "fourth settlement scheme" on illiquid stock options concerns 2014-15 trades of participants on BSE's platform, not BSE as respondent.
4. **Related-party:** IIBH acquisition is a related-party transaction "at arm's length" (disclosed in Annexure C): direct 3.33% for Rs 10.10 cr (31 Jul 2026), plus secondary purchase of 50 crore shares from subsidiaries India INX and India ICC for Rs 50.50 cr (4 Aug, SEBI approval 13 Jul 2026, "under process" on 10 Sep), plus a **rights-issue subscription of Rs 9.28 cr on 10 Sep 2026** taking the direct stake from 3.33% to 5.54% (new vs dossiers). IIBH consolidated turnover Rs 10.47 cr (FY26). Disclosed outlays are Rs 10.10 cr + Rs 9.28 cr + up to Rs 50.50 cr (at most about Rs 70 cr, 0.05% of market cap); the 20% end-state is stated to include the 5.54%, so the amounts may overlap.
5. **Insider/bulk/promoter activity:** no promoter (public 100%); no pledges; NSE PIT, SAST (Reg. 29) and pledge feeds return no records for BSE. Bulk/block deals: the only ones found in the last three months are the Goldman/BNP sales and UTI/Nippon purchases on 29 Sep (claim 5). The 13 Oct NSE large-deal snapshot has no BSE bulk or block entry. Trading window closed for designated persons 1 Oct to 6 Nov. The dossier's "26 May 2026 block of 63,793 shares at Rs 4,300" remains `unverifiable`: the historical block-deal API is blocked.
6. News verification: on 22-23 Dec 2025 NSE sought clarification from BSE on a news item (monthly index option products; stock +3.5%); BSE responded (filings 22 Dec 18:18 and 23 Dec 10:54). Not in dossiers; historical only.
7. Investor-relations calendar: 167 "Analysts/Institutional Investor Meet" filings since 2025 (routine). The 24 Sep 2026 (16:03) and 18 Sep filings are meeting schedules only.
8. Annual-report items re-confirmed: no borrowings; contingent liabilities (tax, claims) about Rs 330 cr at 31 Mar 2026 vs Rs 239 cr a year earlier (dossier 01 B-4; not re-verified line by line here).

---

## 5. Valuation (recomputed)

Inputs: price 3,375.40 (NSE close 13 Oct); listed shares 407,884,077 (SHP filing); company EPS denominator about 411.9 mn (includes shares held in abeyance).

| Measure | Value | How computed / source |
|---|---|---|
| Market cap | Rs 1,37,677 cr | 3,375.40 x 407,884,077 |
| TTM EPS | Rs 68.74 | 13.56 + 14.61 + 19.35 + 21.22 (company-reported) |
| TTM P/E | **49.10x** | matches stockanalysis 49.10 at the 13 Oct 15:28 price |
| TTM attributable PAT | Rs 2,831.6 cr | 558.43 + 601.81 + 797.33 + 874.02 |
| Market cap / TTM attributable PAT | 48.6x | |
| Annualised Q1 FY27 | 39.8x on EPS (84.88); 39.4x on attributable PAT | Q1 x 4 (includes Rs 62 cr excess non-operating income, section 3.4) |
| Forward P/E (S&P consensus, FY27E EPS 76.74 / FY28E 88.50) | 44.0x / 38.1x | stockanalysis forecast page, 13 Oct; stockanalysis's own forward PE is 42.36x |
| P/B (attributable equity Rs 6,673.01 cr at 31 Mar 2026, BV/share 163.6) | 20.6x | aggregator shows 17.12x on BV 194.17 because it includes core settlement guarantee funds in equity |
| Dividend yield | 0.296% | Rs 10 / 3,375.40 |
| Consensus target | Rs 3,693 (+9.4%), median 3,800, range 2,820-4,711, 19 analysts, "Buy", targets last updated 17 Aug (S&P); Investing.com 3,704.26 | stockanalysis forecast page; Investing.com via search summary |
| 52-week range | 2,326.10 (31 Oct 2025, intraday; lowest close 2,419.70 on 28 Oct 2025) to 4,446.80 (27 May 2026; highest close 4,403.30 on 26 May 2026) | recomputed from bhavcopy, bonus-adjusted; price is -24.1% from high, +45.1% from low |

**Own history (information-available TTM P/E, bonus-adjusted closes, 413 sessions 2025-02-07 to 2026-10-13):** current 49.1x sits at the **8.2th percentile**; median 63.7x; min 44.3x (1 Oct 2026); max 97.2x (29 Apr 2025). Within the last 250 sessions: median 61.4x, p10 48.1x, p90 66.6x, current at the 13.6th percentile. This is a compression driven by earnings (TTM EPS +77% YoY: 38.84 -> 68.74) rather than by price; the series is non-stationary and heavily autocorrelated, so the percentile is `descriptive_only`.

Quarter-end P/E on the quarter's own TTM EPS (as aggregators show it) vs dossier 01 V-3:

| Quarter-end | Adjusted close | TTM EPS through that quarter | P/E recomputed | Dossier V-3 |
|---|---|---|---|---|
| Mar-25 | 1,826.6 | 32.18 | 56.8x | n/a |
| Jun-25 | 2,770.1 | 38.84 | 71.3x | 101.7x |
| Sep-25 | 2,040.2 | 43.98 | 46.4x | 62.9x |
| Dec-25 | 2,632.2 | 53.26 | 49.4x | 63.2x |
| Mar-26 | 2,683.5 | 60.61 | 44.3x | 43.8x |
| Jun-26 | 3,865.6 | 68.74 | 56.2x | 55.7x |

Mar-26 and Jun-26 reproduce; Jun-25, Sep-25 and Dec-25 do not (differences of 15-30 turns; the aggregator series looks like it used stale EPS). Dossier forward-P/E history cannot be recomputed (no historical consensus).

**Peers (stockanalysis statistics pages, 13 Oct 2026, S&P Global data; TTM P/E / forward P/E / P/B):** BSE 49.10 / 42.36 / 17.12; CDSL 56.16 / 48.07 / 13.21; MCX 56.07 / 46.93 / 20.51; Angel One 27.98 / 20.67 / 4.61; CAMS 34.15 / 29.82 / 12.80; KFin Tech 43.96 / 36.59 / 8.95; Nuvama 32.07 / 25.27 / 8.36; IEX 18.31 / 17.36 / 6.80. These reproduce dossier 01 V-4 (which used 12 Oct BSE data). Kotak Neo shows MCX at 70.32x and Motilal Oswal at 60.74x on its own basis, so peer multiples depend on the vendor definition. NSE (exchange): Kotak Neo page (13 Oct): market cap Rs 4,33,620 cr, P/E 46.26, previous close 1,729.45, 52-week range 1,712-1,878; reported Q1 FY27 revenue Rs 5,252.17 cr and profit Rs 3,120.08 cr. BSE therefore trades at about a 6% premium to NSE on vendor TTM P/E (49.1 vs 46.3). Not primary-verified (NSE's results are not in BSE's NSE-feed; the 13 Oct quote time is unknown).

---

## 6. Facts in earlier dossiers that must be corrected or qualified

| ID | Where | Statement | Correction (evidence) |
|---|---|---|---|
| C1 | 01 R-13, N-2; 02 section (c) | Q2 FY27 board-meeting intimation not published; results estimate 6 Nov | Board meeting Wed **4 Nov 2026**, intimated 13 Oct 16:02:54 IST (22 days ahead; prior lead times 17-27 days). Trading window 1 Oct to 6 Nov inclusive. The "6 Nov" is the aggregators' stale algorithmic estimate (still shown by Investing.com). |
| C2 | 01 R-2 | Rs 40 cr receivable provision reversed in Q1 FY27 | Provision was booked in Q4 FY26; no reversal. What reversed in Q1 was bond MTM losses (investment income Rs 135.2 cr vs 61.7 cr in Q4). |
| C3 | 02 R10; 01 M-11 | "No bank finance for own-account/proprietary trading" | Credit facilities for own-account acquisition are barred (para 219Z), but guarantees for prop trading are allowed against 100% collateral with at least 50% cash/FD (219ZA); RBI's 30 Mar press release says prop financing "may be undertaken against 100% collateral comprising of cash or cash equivalents". Effective 1 Jul 2026 (revised text of 30 Mar supersedes the 13 Feb text). |
| C4 | 01 G-7 | Auditor change "needs another route (e.g. postal ballot)"; status not found | Primary: Batliboi continues to the 22nd AGM (2027); KKC & Associates LLP starts at the conclusion of that AGM for 5 years (to the 27th AGM). Shareholder approval is part of the 2027 AGM cycle; nothing is pending now. |
| C5 | 02 R6, A15, B4 timeline | +4.39% / +3.94% / +1.54% (5/6/7 Oct) all attributed to the Reuters report; cause of 5 Oct "not stated" | Earliest coverage found is 5 Oct 20:32 IST, after the close. The 5 Oct move (15-minute bars: steady rise from open, largest bar 12:15, close 3,179.6) preceded it. A candidate for 5 Oct is SEBI's Sat 3 Oct 20:40 IST statement of 20,000 comments with "framework to follow soon" (association only). The 6 Oct gap-up (open 3,209, +0.92%) fits the report. |
| C6 | 01 A.2, M-7, N-3 | August BSE premium ADTO Rs 18,100 cr (Nuvama) as the August level | Article is dated 18 Aug 17:08 IST; the figure is month-to-date (about 2 weeks), not a full month. Full-month Aug and any September BSE option-premium data remain not found. |
| C7 | 01 D-6 / appendix A note | Kotak's Q4 FY25 PAT of 106.89 looks "standalone" | It is the **Q4 FY24 consolidated** PAT (Jan-Mar 2024, XBRL `ProfitLossForPeriod` 1,068,900,000), shown as a comparator on Kotak's page. Q4 FY25 consolidated PAT Rs 493.67 cr is right. |
| C8 | 01 B-8 | FY24 "Rs 14.2 cr repurchase", nature UNVERIFIED | A real buyback: NSE corporate-actions feed "Buy Back", record date 14 Sep 2023; BSE's own table: Rs 93 mn (Rs 9.3 cr) including transaction cost and tax for FY2023-24. No buyback in FY25 or FY26. |
| C9 | 01 G-6 | "No leadership change found in 2026" | CEO/CFO/CS unchanged, but several ED, CRO, CTO and KMP changes below them in 2026 (section 4, item 1). |
| C10 | 01 G-8 | Litigation list (SEBI orders only) | Add the Rs 7.25 cr CGST order (Dec 2025; appealed 6 Mar 2026). |
| C11 | 01 V-3 | Own-history trailing P/E for Jun-25, Sep-25, Dec-25 = 101.7x, 62.9x, 63.2x | Recomputed from primary EPS: 71.3x, 46.4x, 49.4x (section 5). |
| C12 | 01 header | "BSE scrip 532809 (per Kotak Neo)" | The company's own SHP filing shows ScripCode 000000 and MSEI symbol NOTLISTED; BSE Ltd is not listed on its own platform (consistent with the brief: NSE only). Drop the code. |
| C13 | 01 R-1 / 02 C7 | PAT growth quoted both as +62% and +66% | Both are correct on different bases: +65.8% vs continuing-ops Q1 FY26 (52,622 lakh); +62.2% vs total-ops (53,817 lakh, which includes a Rs 11.95 cr profit on BSE Institute sale). Specify the base. |
| C14 | 01 R-1, TradingView file | EPS 21.22 vs 21.40 | 21.22 is company-reported (denominator includes abeyance shares); 21.40 is a vendor figure on the listed share count (section 3.3). |
| C15 | 01 S-10 | IIBH purchases | Add the 10 Sep 2026 rights-issue subscription (Rs 9.28 cr; stake 5.54% pending the secondary purchase to 20%). |
| C16 | 01 G-2 | Named holders above 1% | Add "Vanguard and others" (PAC, 8,796,590 shares = 2.16%). |
| C17 | 01 A-1 / A-10 | Consensus Rs 3,703.74; target range up to Rs 4,850 | S&P-based mean is Rs 3,693.21 on the 13 Oct page (Investing.com Rs 3,704.26); range 2,820-4,711. Rs 4,850 is PL Capital's own target (reiterated 5 Aug, PL report). |
| C18 | 02 B4 (10 Aug) | NSE Indices announcement dated 10 Aug "day of announcement, +4.02%" | Date confirmed (10 Aug), time not established; the +4.02% may have preceded it. Do not attribute. |
| C19 | 01 P-7, 02 (a)(1) | beta 0.96 and 10d/20d/50d sd 2.45/2.35/2.23% | Recomputed from `bse_daily.csv`: 10d/20d/50d sd = 2.58/2.41/2.26%; counts of abs move >= 3% (4/5/11) match; sd since 13 Jul 2.13% (dossier 2.11%); beta since 1 Apr = 1.03, correlation 0.38 (dossier 0.96 / 0.37). Differences of at most 0.13 points in sd and 0.07 in beta; method differences, not errors. |

---

## 7. What matters for the next session (Wed 14 Oct) vs long-term

**Next-session relevant (information state at 22:00 IST on 13 Oct):**

| Item | State | Numbers | Status |
|---|---|---|---|
| SEBI CAS / expiry-settlement guidelines | Not issued; chairman "hope ... in about a week" (said Sat 10 Oct). Reuters-sourced expectation: 30-min VWAP for derivatives for at least a year, by end-October. | One analogue: SEBI's 3-4 Sep "within a week" -> paper on 12 Sep (about 9 days). Price history around CAS headlines: +4.36%, +3.14% (3-4 Sep), -3.07% (9 Sep), +3.94% (6 Oct). Outcome space (VWAP-only / blended / CAS retained) is asymmetric; part of a favourable outcome is in P0. | `descriptive_only`. Highest-impact unscheduled item; timing on 14 Oct itself is possible but not the central expectation (Tue 20 Oct is a market holiday). |
| Q2 FY27 results date | Now known: 4 Nov | 21 days after the target session | No effect on 14 Oct beyond removing date uncertainty. |
| September-quarter shareholding pattern | Not yet filed | Past filing dates: 16 Oct 2025, 20 Jan, 17 Apr, 14 Jul 2026 (14-20 days after quarter-end); deadline 21 Oct. Will show passive/MF additions after Nifty inclusion and FPI change. | Informational, can arrive any day 14-21 Oct. |
| Insider supply | Designated persons barred 1 Oct to 6 Nov; no promoter | No bulk/block in BSE on 13 Oct | Low |
| Overhang from 29 Sep sale | Goldman/BNP 68.33 lakh sold; UTI/Nippon bought 52.43 lakh | 6.83 mn shares = 1.67% of equity = 22.7% of that day's 30.1 mn volume; 13 Oct volume was 4.12 mn | In P0 |
| Peer read-throughs | Groww Q2 (14 Oct, single-source list), Angel One Q2 and dividend (15 Oct after close) | | outside fundamentals scope |

No ex-date, record date, AGM, lock-in expiry or index event falls on 14 Oct (dividend ex-date was 10 Jul; Nifty inclusion done 29 Sep). NSE's holiday master (`/api/holiday-master?type=trading`, fetched 13 Oct) lists no holiday on 14 Oct and lists Tue 20 Oct (Dussehra), 8 Nov (Diwali Laxmi Pujan, Sunday), 10 Nov and 24 Nov as the next ones. The Q1 FY27 results, STT (1 Apr), RBI rules (1 Jul), CAS start (3 Aug), analyst actions (17 Aug to 24 Sep) and the NSE listing (24 Sep) are all in the 13 Oct close.

**Long-term / later-event relevance:** Q2 FY27 earnings on 4 Nov (volume decline in Jul-Sep, possible reversal of Q1 treasury gain if yields stayed higher; revenue growth was already flat QoQ in Q1); direct market-data licensing from 1 Jan 2027; co-location expansion to 500 racks (management: current pricing about 20% of market, per PL); cash-segment share goal of double digit by CY2027; IIBH/bullion; Executive Director appointments; auditor transition at the 2027 AGM; STT and RBI drag (management on 4 Aug: "minimal impact" on BSE so far but "we cannot be drawing solace", impact may appear as existing bank guarantees mature); valuation compression (49x vs own 8th percentile) and sell-side split.

---

## 8. Contrary evidence and what would reverse each conclusion

- Q1 "quality of beat" conclusion (non-operating income drove the beat): reversed if BSE's disclosed investment-income split shows the excess was recurring rather than MTM; the CFO statement and the PL variance both point the other way.
- "Reuters report did not cause the 5 Oct rally": reversed if a Reuters timestamp before 15:30 IST on 5 Oct is found (the Reuters original was not accessed; earliest secondary timestamp 20:32).
- "Results sessions are larger than ordinary sessions": reversed on more data; p = 0.024 raw / 0.118 Holm with n = 8.
- Valuation percentile: depends on the 413-session window and on EPS growing 77%; a longer history would change the percentile.
- Counter-evidence to the negative reading of Q1: operating EBITDA +67% to Rs 1,046 cr, margin 67% vs 65% (call), transaction charges +80% YoY, record cash ADTO Rs 9,955 cr, and analysts' Q1 consensus "beat" on EPS in 5 of 5 comparable quarters.
- RBI qualification (C3): reversed if the circular's operative text for 219Z differs from the revised directions page fetched (it was read from rbi.org.in circular index Id=13346, RBI/2025-26/254).

---

## 9. Not found / could not verify

1. The NSE bulk-deal record of 29 Sep (API blocked); trade-date evidence is PTI's "Tuesday" plus bhavcopy volume.
2. NSE Indices' own press release for the Nifty 50 change and its time on 10 Aug.
3. The Reuters original and its publication time.
4. Consensus estimates from a second independent estimate provider; TradingView's 20.31 and TradersUnion's pages (403/not fetched). Pre-bonus vendor forecasts for Q1/Q2/Q4 FY25.
5. Full-month August and any September BSE option-premium/market-share data; October month-to-date.
6. The 30 Jun 2026 India 10-year yield and BSE's bond-portfolio size/duration (needed to size a Q2 MTM effect).
7. Whether the 14 Oct session carries a SEBI circular (unknowable at cutoff).
8. PL's call-based claims (co-location 20% of market pricing, 500 racks) rest on PL's report; the transcript supports "500 racks" and "at least next 1.5 years" language but pricing at 20% of market was not located in the transcript.
9. Q3-FY24 and earlier quarterly EPS (own-history P/E starts Feb 2025).
10. The divested associate referred to in Q1 FY27 note 5 ("in-principle approval ... divestment of its holding in one of the associate company", board 11 Nov 2025, awaiting regulatory approval) is not named in the filing text read; the annual report mentions a completed sale of Ebix Insuretech.

---

## 10. Effect on the next-session forecast

- No fundamental fact found here shifts the centre of the 14 Oct distribution: all verified scheduled/regulatory events are in P0 and the only live catalyst is the SEBI settlement-method decision, which remains of unknown timing (single analogue: 9 days for "within a week").
- The Q2 results date is now fixed at 4 Nov, so there is no earnings event inside the 14-15 Oct window; the dossiers' small allowance for an unscheduled results-date headline can be removed.
- Reaction-size evidence for results days is not relevant to 14 Oct and should not be used to widen the interval.
- The correction C5 matters for any event-study of CAS headlines: use 6 Oct, not 5 Oct, as the first reaction day to the Reuters report; 5 Oct (+4.39%) is an unexplained pre-report move.

---

## Appendix A. Definitions and reproducibility

- Returns: log returns vs the bonus-adjusted previous kept close (`src/common.py` `load_bse`, `targets`): G = ln(open/prev), I = ln(close/open), R = G + I. Percentages above are log unless stated "simple".
- Reaction day: the first session after an after-hours release (all ten releases were after 15:30 IST).
- z for T1: R(t) / sample sd of R over the 60 sessions ending at t-1 (no look-ahead). Event z values: -0.92, 0.85, 1.41, -0.74, 1.81, 2.51, -0.51, -1.20.
- Permutation seed 20261014, 20,000 draws, pool = all sessions 2024-11-13 to 2026-10-13 except event reaction days (n = 465).
- Spearman permutation tests are exact (8! and 5! permutations). Holm over the five tests listed in 3.5.
- Own-history P/E: adjusted close = close / product of later `ca_factor`; TTM EPS = sum of the last four company-reported quarterly EPS, effective from the session after the release.
- Scripts (outside the repo, in the session scratchpad because the brief limits writes to the assigned path): `.../scratchpad/react.py`, `surprise_tests.py`, `val.py`, `webget.py`; downloaded filings in `.../scratchpad/dl/` and pages in `.../scratchpad/web/`.
