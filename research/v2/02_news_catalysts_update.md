# v2 / 02 — News, sentiment, catalysts and market conditions to the 22:00 IST cutoff (BSE Ltd, NSE: BSE)

Workstream "news". Target session Wed 2026-10-14. P0 = ₹3,375.40 (official NSE close 2026-10-13). v2 cutoff 2026-10-13 22:00 IST; frozen v1 cutoff 16:55 IST. Frozen v1 record (`results/forecast_record_2026-10-14.json`) and `research/02_regulatory_macro_catalysts.md` were read, not edited. No git commands were run. This is the only file written. All times IST unless stated; ET = UTC−4 on this date (so 12:17 ET = 21:47 IST).

**Cutoff discipline.** The container clock read 21:59:33 IST when I started and the work ran to about 22:30 IST. Many endpoints return "current state", so every item below carries its own publication stamp, and anything stamped after 22:00:00 IST was dropped (2 of 522 NSE filings dated 13 Oct were stamped after 22:00 and are excluded). Where an endpoint carries no usable stamp (SEBI listing pages show dates only; the NSE FII/DII provisional JSON has no time; web tickers) the item is flagged and given low weight. Results of searches or fetches after 22:00 IST are used only if the underlying document is stamped ≤ 22:00 IST.

**Method statement.** This workstream is source verification plus descriptive statistics. No hypothesis was tested, so no p-value or multiplicity adjustment applies; the descriptive protocol (definitions, windows) was written as code comments before any output was read (Appendix A). Nothing here is `validated_out_of_sample`; the one validated linkage I rely on (S&P 500 → BSE gap) belongs to workstream `03_market_linkages.md` and is quoted, not re-derived.

---

## 1. Bottom line (numbers)

1. **No new regulatory or company catalyst was found between 16:55 and 22:00 IST.** SEBI circular listing: newest item dated 7 Oct (3 debt-market circulars); zero circulars dated 8–13 Oct. SEBI press-release listing: newest 13 Oct (a refund public notice). SEBI RSS (30 items, all 12–13 Oct orders, appeals and recovery notices) was built at 22:00:02 IST. SEBI "Reports/consultation" listing: newest 13 Oct (LODR issue-proceeds paper); the CAS paper is still the 12 Sep one. **No CAS / derivative-settlement circular exists as of 22:00 IST** (`verified_source`, with one caveat: a 13 Oct Business Standard item on a SEBI IPO relaxation is not visible on these listings, so listings may lag).
2. **BSE Ltd made 0 filings on 13 Oct.** NSE announcements API (1,312 records since 2017): newest is 12 Oct 15:30:27 (routine depository-participant certificate). Trading window closed 30 Sep 11:28:54. No Q2 board-meeting intimation; BSE is absent from NSE's board-meeting calendar for 13–24 Oct (478 entries). BSE's Q2 results came 2–12 Nov in 9 of 9 years (2017–2025). **No company-specific scheduled event falls inside the 6-session window.**
3. **The 13 Oct 14:15 spike has no identified cause.** The bar (₹3,318.6→high 3,400.9→close 3,326.3, 1,076,912 shares) is **8.9× the median volume of the same slot in the other 19 sessions** (bootstrap 95% CI of the ratio 5.1–10.2×; 1.84× the largest of those 19), **3rd largest of 495 bars**, 27.2% of the day's bar volume. 14:15–15:15 held 53.7% of the day's volume vs a 19.8% median (CI 18.0–27.6%) in the other 19 sessions; only 29 Sep (index-inclusion day, 85.2%) was higher. NSE block-deal file: "NO RECORDS"; no BSE row in the bulk file; no NSE news-verification, price-movement or volume-spurt notice for BSE; no BSE, SEBI or sector filing in 13:45–14:40 IST explains it (`not_found`).
4. **The two big up-days differ.** 13 Oct (+1.36%) is **market-explained**: beta-implied residual −0.07 pp at β = 0.89 (z −0.03) or −0.86 pp at the rolling-250 β of 1.39 (z −0.41). 12 Oct (+1.31%) carries a residual of **+1.92 pp (β 0.89, z +0.88) to +2.29 pp (β 1.42, z +1.08)** while Nifty fell 0.70%; 27% of the last 250 sessions had a larger |residual|. It was sector-wide (equal-weight Angel One/CDSL/MCX/CAMS/KFin +1.96% vs BSE +1.30%), and the Nifty Capital Markets index rose 1.50%. The Saturday 10 Oct SEBI Chairman remark is a timing candidate; no source ties the move to it (association only).
5. **Official 13 Oct closes (NSE archive, stamped 19:50 IST):** Nifty 50 22,721.95 (+1.60%, high = close), India VIX 14.12 (−7.43%, from 15.25), Nifty Capital Markets 5,285.75 (+0.51%), Nifty IT +5.22%. NSE provisional flows: FII/FPI −₹1,305.13 cr, DII +₹2,439.24 cr (stamp unknown). USD/INR 95.28 (ECB reference) vs 95.78 (12 Oct) and 96.73 (9 Oct): rupee +0.52% and +0.99%.
6. **Overnight at 21:47 IST:** S&P 500 7,797.63 (−0.12% vs 7,807.24), Dow 51,672.75 (−0.34%), Nasdaq 27,210.61 (−0.13%); Dow had been +0.47% at the open (20:20 IST). Bank Q3 results mixed (JPM EPS $5.57 vs $5.90 estimate; Goldman revenue $18.68B vs $16.71B). Asia (13 Oct): KOSPI 6,035.35 (−5.46%), Nikkei 225 −1.82%, Topix +0.14%. Brent ≈ $105.6–106.0 (−0.6 to −1.0%); US 10-year ≈ 5.22%; DXY ≈ 102.0. **GIFT Nifty was not obtainable** from any reputable public source. Per workstream 03, the S&P move implies a mechanical gap adjustment of only −0.05 to −0.10 pp (sd of gap 1.11%).
7. **Already priced:** BSE +10.81% from the 1 Oct close (3,046.00) to P0, vs Nifty Capital Markets +4.84% and Nifty 50 +1.34%; only +0.58% since 7 Oct (3,356.00), the last day of the Reuters-CAS rally (+4.39 / +3.94 / +1.54%). Following the earlier September CAS-review rally, the next four sessions summed −3.09%; after the October rally, +0.58% (n = 2 clusters, `descriptive_only`).
8. **Calendar (primary sources):** 14 Oct is a normal full session (NSE holiday master). Next five sessions: 15, 16, 19, 21, 22 Oct; **20 Oct (Dussehra) closed**. Groww (Billionbrains) board and Q2 results **14 Oct**, earnings call 16:00 IST (outcome in Q1 was filed 11:30 IST, i.e. in market hours); Angel One board **15 Oct** (Q2 + second interim dividend, record date 22 Oct); Sensex weekly expiry Thu 15 Oct; US CPI Wed 14 Oct 18:00 IST (after the Indian close).
9. **Does anything invalidate v1?** Nothing found by 22:00 IST invalidates the v1 distribution. Section 8 lists exactly which developments before or at the open would, and in which direction.

---

## 2. Ledger: what happened after the v1 cutoff (16:55 IST) and before 22:00 IST

| Time (IST) | Item | Source and stamp | Relevant to BSE? | Status |
|---|---|---|---|---|
| ≈16:00–17:00 (event; time inferred from "before the open") | JPMorgan, Goldman, Citi, Wells Fargo Q3 results, pre-US-open | Reuters via Yahoo, published 13 Oct 8:11 CDT (18:41 IST) | Indirect (global financials tone) | confirmed |
| 18:13 | US futures: Dow e-mini +0.84%, S&P −0.06%, Nasdaq-100 −0.71% | same Reuters piece, "at 8:43 a.m. ET" | Indirect | confirmed |
| 18:57 | NSE block-deal file "NO RECORDS"; bulk-deal file 172 rows, no BSE/peer row | `nsearchives…/content/equities/block.csv`, `bulk.csv`, Last-Modified 13:27:04 GMT | Yes (rules out a recorded block trade) | verified_source |
| 18:44 and 19:41 | ABSL AMC board intimation for 21 Oct | NSE board-meetings API | Peer calendar only | verified_source |
| 19:24 | NSE F&O bhavcopy: BSE Oct future closed 3,397.6; OI +419,800 | `BhavCopy_NSE_FO_…20261013`, Last-Modified 13:54:02 GMT | Yes (positioning) | verified_source |
| ≈19:30 | ECB reference: USD/INR 95.28 | Frankfurter API (ECB data), date 2026-10-13 | Indirect (FPI flows) | verified_source |
| 19:50 | Official index closes incl. India VIX | `ind_close_all_13102026.csv`, Last-Modified 14:20:38 GMT | Yes | verified_source |
| 20:20 (page stamp; levels are opening-bell levels, 19:00 IST) | US opening bell: Dow +0.47%, S&P −0.15%, Nasdaq −0.39% | Reuters via Sunday Guardian ("Last Updated 20:20:26 IST") | Indirect | confirmed |
| 21:47 | S&P 7,797.63 (−0.1%), Nasdaq 27,210.61, Dow 51,672.75 (−0.3%) | Investing.com/Reuters midday update "12:17 ET" | Indirect | confirmed |
| 21:54 | Yahoo live blog update (text) | "Updated 11:24 AM CDT" | Indirect | confirmed |
| 21:55 | Official delivery data: BSE delivery 36.07% | `sec_bhavdata_full_13102026.csv`, Last-Modified 16:25:37 GMT | Yes | verified_source |
| 22:00:02 | SEBI RSS built; no CAS item; newest circular 7 Oct | `sebirss.xml`; circular listing | **Yes (main negative result)** | verified_source |
| all day | BSE Ltd filings with NSE | NSE announcements API | 0 filings after 12 Oct 15:30:27 | verified_source |
| 17:00–22:00 | 520 market-wide NSE filings dated 13 Oct (≤22:00) screened for exchange/SEBI/CAS/derivative/BSE terms | NSE announcements API | None relevant | verified_source |
| (before cutoff) | NPCI defers UPI MDR until after Diwali (Paytm filing 14:32) | NSE filing PDF | No | confirmed, irrelevant |
| (13 Oct dated) | SEBI orders (Wipro insider-trading adjudication, IIFL Capital Services inspection), LODR consultation, refund notice | SEBI RSS/listings | No | confirmed, irrelevant |

Not obtained: any Reuters, Bloomberg or PTI text about BSE, SEBI or CAS dated after 16:55 IST (about 20 targeted searches returned nothing for 13 Oct; search recall for same-day items is poor, so this is **absence of evidence, not evidence of absence** for wire stories). The only independent hard negatives are the SEBI and NSE primary feeds above.

---

## 3. The 13 Oct 14:15–14:30 IST volume spike

### 3.1 What the data show (Yahoo 15-minute bars, bar START times, 20 sessions 15 Sep–13 Oct, 495 bars)

| Measure | Value | Benchmark / interval |
|---|---|---|
| Bar 14:15: O/H/L/C | 3,318.6 / 3,400.9 / 3,318.6 / 3,326.3 | NSE daily high 3,403.2 (tick not in Yahoo bar) |
| Volume | 1,076,912 | slot median, 19 other sessions: 121,449 (95% CI 105,385–212,942); slot max 586,351 |
| Ratio to slot median | 8.87× | CI 5.1–10.2× |
| Rank among 495 bars | volume 3rd, range 4th (2.45%) | only 29 Sep 15:00 (22.5M, index inclusion) and 29 Sep 14:45 (1.70M) are larger |
| High vs bar open; close vs bar open | +2.45%; +0.23% | up-spike then −1.85% round-trip inside one bar |
| Next bar 14:30 | 3,326.2→3,385.0 (low 3,310.4)→3,379.9; 465,382 shares (3.0× slot median) | second leg up |
| Share of day's bar volume | 27.2% in this bar; 53.7% in 14:15–15:15 | other-19 median 19.8% (CI 18.0–27.6%); 1 of 19 sessions higher |
| Day total vs official | bars sum 3,959,915 = 96.1% of NSE 4,119,552 | consistent with the 87–100% range |
| Day total vs history | 4,119,552 = 0.95× trailing-20 median (4,334,371) | day total is normal; intraday concentration is not |
| Bars with volume ≥ 5× slot median **and** range ≥ 2% | 3 of 495: 24 Sep 10:00, 29 Sep 15:00, 13 Oct 14:15 | thresholds fixed before looking; the first two have documented events |

### 3.2 Candidate explanations checked

| Candidate | Evidence | Result |
|---|---|---|
| SEBI document | Circulars, press releases, consultations, RSS: nothing on CAS or derivatives after 7 Oct | rejected for 13 Oct |
| BSE Ltd disclosure | 0 filings on 13 Oct | rejected |
| Sector/peer filing | 29 market-wide NSE filings stamped 13:45–14:40 IST read; none about exchanges/SEBI/derivatives. Closest: CAMS call schedule (14:21:56), Paytm/NPCI (14:32) | rejected |
| Recorded block trade | afternoon block window is 14:05–14:20 (min ₹25 cr, from several secondary sources, not re-verified at NSE); NSE block file for 13 Oct: **NO RECORDS** | rejected for a recorded block |
| Bulk deal | bulk threshold is >0.5% of equity (≈2.0M shares) so a 1.08M-share trade would not appear; the file shows no BSE row | **uninformative** |
| Media report | ~20 targeted searches, none found; Multibagg's auto-generated 13 Oct roundup says "no fresh database headline" (an automated page, not independent confirmation); NSE sent 10 news-verification/volume-spurt notices to 9 other stocks on 13 Oct but none to BSE (BSE received news-verification queries on 22–23 Dec 2025, 31 Jul 2024, 30 Aug 2023) | not found; weak negative |
| Derivatives positioning | Oct future closed 3,397.6 vs 3,351.1 prior (+1.39%), OI +419,800 (+3.3% to 13.09M), futures high 3,420.7; Oct put OI −348,000 (−5.2%), call OI +8,400; basis 22.2 pts (0.66%) vs 20.9 (0.63%) | consistent with long build-up and put unwinding on the day; cannot be timed within the day |
| Thin-book sweep | +2.45% in <15 min on 8.9× volume, fully retraced to +0.23% by bar close | shape is consistent with it, but equally consistent with news; no intent is inferred (brief rule 5) |
| Index/ETF event | No index effective date on 13 Oct in the v1 dossier; MSCI/FTSE/other reviews not checked | not checked |

### 3.3 Comparison with the other large bars

| Bar | Volume | Documented event on that date (source) |
|---|---|---|
| 29 Sep 15:00 / 14:45 / 14:30 | 22.5M / 1.70M / 0.85M | Nifty 50 inclusion effective at close (NSE Indices; v1 dossier C5) |
| 5 Oct 15:00 | 995,107 | CAS-rollback story day (+4.39%); price-implied onset 12:15 (bar +1.20% on 3.5× volume), a further push 13:30 (3.5×) — timing is an inference from price only |
| 24 Sep 10:00 | 911,116 | NSE listing day; Macquarie initiation (v1 dossier C1, C6) |
| 6 Oct 09:15 | 847,268 | First session after the Reuters story (Outlook Money 6 Oct 09:04) |
| 1 Oct 15:00 | 833,296 | No event identified |
| **13 Oct 14:15** | **1,076,912** | **None identified** |

On the CAS-news days 5–6 Oct the largest slot multiple of any bar was 5.2× (6 Oct 12:45), versus 8.9× on 13 Oct; the 6 Oct 09:15 open bar had a similar price excursion (high +2.52% above its open) on 3.9× volume. The 5 Oct move built up over several bars (+1.20% bar at 12:15, +0.69% at 13:30) rather than in one bar. So the 13 Oct spike is larger than the news-day bars in volume multiple and comparable in price excursion.

### 3.4 Conclusion

**No cause could be established** (`not_found`). Effect on the forecast: none to the centre. It is recorded as an unexplained abnormal-volume event that coincided with a +1.36% close; I did not (and cannot) classify it as informed trading. v1's statement "volume ratio on 13-Oct was low-to-normal" is correct for the daily total (0.95× trailing-20 median) but hides the intraday concentration above. What would resolve it: NSE trade-by-trade data, 1-minute bars (Yahoo returned 429; NSE chart endpoint returned an empty series), or a wire story stamped 14:00–14:30 IST.

---

## 4. The +1.31% (12 Oct) and +1.36% (13 Oct) moves

| Item | 12 Oct | 13 Oct |
|---|---|---|
| BSE close-to-close (simple / log) | +1.31% / +1.30% | +1.36% / +1.35% |
| Nifty 50 (log) | −0.70% | +1.59% (official 22,721.95) |
| Beta-implied residual, β = 0.89 (full sample, workstream 03) | +1.92 pp, z +0.88 | −0.07 pp, z −0.03 |
| Beta-implied residual, rolling-250 β (1.42 / 1.39) | +2.29 pp, z +1.08 (resid sd 2.13%) | −0.86 pp, z −0.41 (resid sd 2.12%) |
| Share of last 250 sessions with larger \|residual\| | 26.8% | 64.0% |
| Nifty Capital Markets | +1.50% | +0.51% |
| Peers (log): Angel One / CDSL / MCX / CAMS / KFin | +3.45 / +0.48 / +2.14 / +0.97 / +2.77 | +2.53 / +2.03 / −2.45 / +3.18 / +2.72 |
| Equal-weight peer mean; BSE minus peers | +1.96%; −0.66 pp | +1.60%; −0.26 pp |
| Delivery % (60-day mean 41.29, sd 8.16) | 40.85 | 36.07 (z −0.64; 23rd percentile) |
| Day VWAP vs close | n/a | VWAP 3,343.16, close 3,375.40 (+0.96% above VWAP) |

* **13 Oct** needs no BSE-specific explanation: the stock moved with the market and slightly less than peers. The market driver reported by every source is the IT-led rally (HCLTech/TCS results; Nifty IT +5.22%), rupee strength after the 10 Oct RBI measures, Trump's "no Iran strike before 3 Nov" remark and lower crude. KOSPI's −5.46% occurred during Indian hours (KRX trades 05:30–12:00 IST) and did not stop the Nifty.
* **12 Oct** was a sector-wide rally on a down day for the index. Candidate catalysts, none of them confirmed as the cause: (a) the SEBI Chairman's remark on Sat 10 Oct that CAS "guidelines [will be issued] in about a week's time" (primary PDF, stamped 18:20 IST); (b) the rupee's best day in six months; (c) Angel One's Sept update (6 Oct). A ~2 pp unexplained residual is about 1 sd of BSE's idiosyncratic noise, so it does not by itself demand a news cause.
* **Status:** `descriptive_only`; n = 2 days, one benchmark choice each way (two β values); no test.

---

## 5. Overnight and pre-session conditions available by 22:00 IST

| Item | Value | Source, stamp | Status | Relevance for the 14 Oct open |
|---|---|---|---|---|
| Nifty 50 (13 Oct) | O 22,364.15 H 22,721.95 L 22,288.45 C 22,721.95 (+358.60, +1.60%) | NSE `ind_close_all_13102026.csv`, 19:50 IST | verified_source | Already in P0 |
| India VIX | 14.12 (H 15.35, L 13.945, −7.43%); 12 Oct 15.25 | same | verified_source | Lower vol backdrop; ATM IV of BSE options 38.5% on 12 Oct (33rd percentile of 461 days) |
| Other NSE indices | Next 50 +0.84%, Nifty 500 +1.22%, Midcap 150 +0.97%, Bank +1.03%, Fin Services +1.46%, IT +5.22%, Capital Markets +0.51% | same | verified_source | Breadth supportive |
| FII/FPI and DII (provisional) | FII buy 13,465.39 / sell 14,770.52 = −₹1,305.13 cr; DII buy 16,232.97 / sell 13,793.73 = +₹2,439.24 cr | NSE `fiidiiTradeReact` API; **no time in payload** | verified_source (time unknown) | Mild; vs −₹44,166 cr FPI in Oct to 9 Oct (v1 dossier) |
| USD/INR | 95.28 (13 Oct), 95.78 (12 Oct), 96.73 (9 Oct), 96.78 (8 Oct) | ECB via Frankfurter; FRED `DEXINUS` ends 2 Oct (96.31) | verified_source | Rupee +0.52% / +0.99%; v1 Yahoo ~95.27 agrees |
| US cash, 12:17 ET (21:47 IST) | S&P 7,797.63 (−0.1%); Nasdaq 27,210.61 (−0.1%); Dow 51,672.75 (−0.3%) | Investing.com (Reuters-based) | confirmed | Workstream 03: gap adjustment −0.05 to −0.10 pp |
| US cash, other snapshots | Open (20:20 IST): Dow 52,092.99 (+0.47%), S&P 7,795.27 (−0.15%), Nasdaq 27,138.73 (−0.39%); Yahoo ticker S&P 7,804.86 (−0.03%) at an unstated time ≈12:25–12:32 ET (21:55–22:02 IST) | Reuters via Sunday Guardian; Yahoo | confirmed / ticker time uncertain | Range of S&P: −0.03% to −0.15% inside the last two hours |
| VIX (US) | 15.44 (+1.51%) ticker, time unstated; 12 Oct close 15.21 (FRED) | Yahoo | low confidence | Slight rise |
| US banks | JPM: EPS $5.57 vs $5.90 est; $5.75 excluding $658M securities losses; premarket −0.7%, later +0.3% to +2% (sources differ). GS: revenue $18.68B vs LSEG $16.71B, profit +29%, +3.5% premarket, +2% after open. WFC: profit up on loan growth, −2.9% premarket, ~−1% to −1.5% later. Citi: beat, card spending +11%, −0.4% premarket, ticker −3.45%. BAC −1.18%, MS −0.87%, BLK −0.81% (ticker). | Reuters via Yahoo (18:41 IST); Investing.com (21:47 IST); Yahoo live blog (21:54 IST). Summariser-read, numbers not re-verified at primary | confirmed (direction), conflicting (magnitudes) | Mixed; no consistent sign |
| US chips | Micron −4.6% (fourth straight fall); Nvidia −0.8%, AMD −1.9%, Marvell −3% premarket | same | confirmed | Weighs on Nasdaq; Broadcom CEO "casino" remark cited |
| Asia (13 Oct close) | KOSPI 6,035.35 (−348.89, −5.46%; intraday low 5,911.11, −7.41%; sell sidecar 09:47:58 KST); Samsung −7.39%, SK hynix −10.09%; Nikkei 225 −1.82% (≈67,778), Topix +0.14%; Hang Seng "edged higher" | Korea Daily (fetched), Seoul Economic Daily (search summary, 10:44 KST article), Il Sole 24 Ore, Reuters via Dainik Jagran | confirmed (two sources for KOSPI) | **Already priced on 13 Oct**: it happened before the Indian close |
| Brent | futures ≈ $105.63 (−0.96%) ticker; $105.98 (−0.6%) mid-morning Reuters; Monday close ≈106.65 was the highest since 15 Sep; Houthi strikes on Saudi infrastructure Mon; Russia diesel remark Tue | Investing.com; Reuters via search summary; v1 Yahoo | conflicting direction across sources | Oil is the main India macro swing factor; workstream 03 found no BSE–Brent association |
| FRED Brent spot | $125.44 (6 Oct), $135.51 (2 Oct) | `DCOILBRENTEU.csv` | **instrument mismatch**: Dated-Brent spot vs futures $104–107 | Not used for any level claim |
| US 10-year | 5.22% (8 Oct), 5.24% (9 Oct); no 12 Oct fixing (Columbus Day); 13 Oct live ≈ 5.22–5.23% | Treasury daily par yield curve (to 9 Oct); tickers | verified_source / ticker | 13 Oct fixing is published after the cutoff and not used |
| Dollar index | ≈102.0 (−0.35%) | Investing ticker, time unstated | low confidence | n/a |
| Fed | Beige Book Wed 14 Oct 14:00 ET (23:30 IST); FOMC 27–28 Oct, statement 28 Oct 14:00 ET; Sept minutes were 7 Oct | federalreserve.gov calendar, Last-Modified 21:30 IST | verified_source | After the Indian close |
| **GIFT Nifty** | **not obtained** | NSE IX site 403; investing.com 404; moneycontrol, Economic Times blocked; search found no 13/14 Oct item | not_found | v2 gap estimate cannot use it; at 08:45 IST use BSE gap ≈ β × Nifty gap |

**How much of this is new for the 14 Oct open?** Asia's 13 Oct moves and the rupee's 13 Oct move were already in P0. New since the Indian close: the US session after 19:00 IST (S&P −0.03% to −0.15%, a fade from a Dow-led open), bank results, and the unfinished US day. Workstream 03's validated slope (0.276 pp BSE gap per 1% S&P; CI 0.215–0.337) gives −0.05 pp (full-sample β) to −0.10 pp (last-250 β) against sd(G) = 1.11% (v1 σ_G = 0.88%): negligible.

---

## 6. Calendar: 14 Oct and the next five sessions (certainty labels)

Key: **FIRM** = primary source (exchange, regulator, company filing, central bank); **FIRM-rule** = follows from a stated exchange rule; **SOFT** = secondary or pattern; **TENTATIVE** = estimate.

| Date | Time (IST) | Event | Certainty | Source (access) |
|---|---|---|---|---|
| Wed 14 Oct | 09:00–09:08 pre-open; 09:15–15:30 | **Normal full session** (CM/FO holiday list shows none between 2 Oct and 20 Oct) | FIRM | NSE `holiday-master` API (fetched ~22:10 IST); v1 holiday lists agree |
| Wed 14 Oct | ~12:00 | India WPI (Sept); Aug was 9.92%; economist range ≥ 9.5–10.2% | SOFT (release date not confirmed by a 2026 calendar; Aug data was due 14 Sep) | Asianet Newsable / Times of Oman reports of India Ratings (10.2%) and ICRA forecasts (search summary) |
| Wed 14 Oct | outcome possibly ~11:30; call 16:00 | **Groww (Billionbrains Garage Ventures) board + Q2/H1 results and earnings call** | FIRM (date, call); SOFT (outcome time) | NSE filing 7 Oct 16:40:43 (PDF Last-Modified 16:40:45 IST); Q1 precedent: outcome 15 Jul 11:30:46, KPIs 11:53, shareholder letter 11:45 |
| Wed 14 Oct | board meeting | ICICI Lombard Q2 | FIRM | NSE board-meetings API |
| Wed 14 Oct | 18:00 | US Sept CPI (08:30 ET) | FIRM (two Reuters-based reports on 13 Oct; BLS site 403) | Investing.com, Yahoo/Reuters |
| Wed 14 Oct | ~16:15 onwards | BofA, Morgan Stanley, BlackRock Q3 | FIRM | Reuters/Investing |
| Wed 14 Oct | 23:30 | Fed Beige Book | FIRM | federalreserve.gov |
| Wed 14 Oct → Fri 17 Oct | unscheduled | **SEBI CAS / derivative-settlement guidelines** ("about a week" from Sat 10 Oct; Reuters: effective by end-Oct) | SOFT (no date) | SEBI Chairman PDF (primary); Reuters (secondary) |
| Thu 15 Oct | 09:15–15:30 | **Sensex weekly expiry** (BSE) under current CAS settlement unless changed | FIRM-rule | v1 dossier (Groww expiry table); no change notice found |
| Thu 15 Oct | board meeting (outcome pattern: after 17:40) | **Angel One Q2 + second interim dividend** (record date Thu 22 Oct); Wipro, Nestle, Tech M, HDFC AMC, 360 ONE, 5paisa, IIFL Finance, Jio Financial, L&T Finance, HDFC Life | FIRM | NSE announcements + board-meetings API; Angel One Q1 outcome filed 15 Jul 17:42:36 |
| Thu 15 Oct (Fri 16 Oct) | 11:00 | Angel One earnings call 16 Oct | SOFT | ScanX headline only |
| Thu 15 Oct | ~16:00 | India trade data | TENTATIVE | pattern |
| Fri 16 Oct | all day | 57 board meetings (Q2 season); US retail sales/PPI "this week" (dates unverified) | FIRM / SOFT | NSE API; Reuters |
| Sat 17 Oct | no trading | HDFC Bank, ICICI Bank Q2 | FIRM | NSE board-meetings API |
| Mon 19 Oct | 09:15–15:30 | Weekly Nifty expiry moved forward from Tue 20 Oct | FIRM-rule (previous trading day); SOFT (source: Dhan) | v1 dossier |
| **Tue 20 Oct** | closed | **Dussehra: CM, FO closed** | FIRM | NSE holiday master |
| Wed 21 Oct | 09:15–15:30 | ABSL AMC Q2; RBI MPC minutes (usual 14-day lag) | FIRM / SOFT | NSE API; v1 |
| Wed 21 Oct | n/a | Angel One page's "Muhurat 21 Oct" is **wrong**: NSE lists Muhurat on Sun 8 Nov | FIRM | NSE holiday master |
| Thu 22 Oct | 09:15–15:30 | Sensex weekly expiry; Angel One dividend record date | FIRM | v1; NSE |
| Fri 23 Oct | after close | Infosys, Crisil, UTI AMC results | FIRM | NSE |
| Tue 27 Oct | | Monthly F&O expiry (BSE Oct future/options expire 27 Oct); FOMC 27–28 Oct | FIRM | NSE F&O file; federalreserve.gov |
| Sun 8 Nov; Tue 10 Nov | | Muhurat (timings unannounced); Diwali-Balipratipada holiday | FIRM (dates) | NSE holiday master |
| BSE Ltd Q2 results | | Not before 24 Oct (board calendar); history 2–12 Nov (2017–2025: 3 Nov, 2 Nov, 6 Nov, 7 Nov, 12 Nov, 7 Nov, 10 Nov, 12 Nov, 11 Nov); window closed 30 Sep | FIRM (not before 24 Oct); TENTATIVE (Nov date) | NSE announcements API |
| Peers | | CAMS earnings call 2 Nov (filing 13 Oct 14:21:56); KFin earnings call scheduled (7 Oct); CDSL, MCX, Nuvama: no board date in 13–24 Oct list | FIRM / absent | NSE API |

---

## 7. Material-item register and sentiment separation

### 7.1 Material items

Columns: published stamp / event time / status / change vs prior expectation / transmission / priced? Evidence uses the price data in Section 4 and Appendix A.

| ID | Item | Source and publication stamp | Event time | Status | Change vs prior expectation | Transmission | Already priced? |
|---|---|---|---|---|---|---|---|
| M1 | SEBI Chairman Pandey: "We are currently examining the comments and hope to issue guidelines in about a week's time" on the expiry-day settlement price | SEBI speech PDF (Last-Modified Sat 10 Oct 12:50:50 GMT = 18:20:50 IST); IANS 20:31 IST; Outlook Money 11 Oct 14:06 | Sat 10 Oct evening, Mumbai | **confirmed (primary, verbatim)** | Converts "likely/by end-Oct" into a ~1-week official horizon; says nothing about the outcome (no VWAP mention); same speech: interoperability for buybacks/OFS by end-Nov, AI/ML guidelines "shortly" | Settlement rule → expiry-day options volume → BSE transaction-charge revenue | Partly: peers +1.96% and BSE +1.30% on 12 Oct (association only) |
| M2 | Reuters (unnamed sources): SEBI likely to stop using CAS for derivative settlement ≥1 year, revert to final-30-minute VWAP, effective by end-Oct | Niftytrader/Lapaas dated 5 Oct; Outlook Money 6 Oct 09:04; Business Today 6 Oct; DSIJ 10 Oct 11:00; ≥10 outlets | 5–6 Oct | **unverified (single source, not officially confirmed)** | First concrete signal of rollback | same | **Yes**: +4.39, +3.94, +1.54% (5–7 Oct), BSE +10.81% from 1 Oct; +0.58% since 7 Oct |
| M3 | SEBI consultation paper on CAS/timings/settlement (7 proposals; ~20,000 comments) | SEBI "Reports" listing, 12 Sep | 12 Sep | confirmed (primary) | Formal start of review | same | Largely: Sept rally +4.36/+3.14% then −3.5% in the next three sessions |
| M4 | **Absence of a SEBI CAS circular** at 22:00 IST | SEBI listings, RSS 22:00:02 | | verified_source | Keeps the key binary event open for 14 Oct | | n/a |
| M5 | SEBI Chairman 10 Sep: "CAS will remain part of India's market structure" (cash close stays; derivative settlement under review) | Kotak Neo, updated 11 Sep 12:49 | 10 Sep | confirmed (secondary) | Reconciles with M2: only derivative settlement changes | | Yes |
| M6 | Groww Q2 results, 14 Oct | NSE filing 7 Oct 16:40:43 | 14 Oct | **confirmed (primary)** | Previously soft (single Upstox list); now firm. Q1 FY27: net profit ₹735 cr (+94% y/y), retail derivatives share 11% | Retail-derivatives activity → exchange volumes | No (event pending) |
| M7 | Angel One Sept business update: ADTO ₹44,879 bn (+8.4% m/m, −6.9% y/y), orders 122.29 mn (−4.1% y/y), F&O premium share 22.5% (+66 bps y/y), clients 39.98 mn (+17.3% y/y) | NSE filing 6 Oct 07:36:59; ScanX 6 Oct 07:44 | Sept 2026 | confirmed (company-reported) | Retail activity recovering from the Aug trough | Same | Angel One +3.45% (12 Oct), +2.53% (13 Oct) |
| M8 | Angel One Q2 board 15 Oct, second interim dividend | NSE filings 21 Sep 18:42, 6 Oct 16:12 | 15 Oct | confirmed (primary) | Firm date | Read-through to retail F&O revenue | No |
| M9 | Sell-side: Macquarie Outperform ₹4,000 (24 Sep); Jefferies Underperform ₹2,940 and Nuvama Hold ₹3,240 (17–18 Aug); Bernstein ₹2,820; consensus mean ₹3,703.74 (stockanalysis, 19 analysts, v1 13 Oct) | v1 dossier; searches for 12–13 Oct found no new action | | confirmed (v1); JPM stance conflicting (Overweight ₹3,950 v1 vs Hold ₹4,090 in a search summary), unresolved | None found since 24 Sep | Valuation anchor | Yes (rating changes are 3–8 weeks old) |
| M10 | NSE (13 Oct, 18:57 IST): block-deal file "NO RECORDS" | NSE archive | 13 Oct | verified_source | n/a | n/a | n/a |
| M11 | BSE derivatives positioning 13 Oct (OI, put unwinding) | NSE F&O file 19:24 IST | 13 Oct | verified_source | n/a | Positioning supports momentum | Yes |
| M12 | KOSPI −5.46% on CXMT DRAM news; US chip slide | Section 5 | 13 Oct | confirmed | Chip/AI de-rating in North Asia | FPI rotation | Yes for 13 Oct (Nifty +1.6%) |
| M13 | Houthi strikes on Saudi infrastructure (Mon 12 Oct); Brent highest since 15 Sep | Reuters via Investing/search | 12 Oct | confirmed (secondary) | New geopolitical oil risk not in the v1 dossier | Oil → India CAD/INR/FPI | Partly (Brent 105.6–106 vs 104.4 Yahoo on 13 Oct IST) |
| M14 | FII/DII provisional flows | NSE API (time unknown) | 13 Oct | verified_source (time unknown) | Small vs October run-rate | Flows | Yes |

### 7.2 Four sentiment channels kept separate

| Channel | State as of 22:00 IST | Evidence | Change since v1 |
|---|---|---|---|
| **News sentiment** | Net positive but stale. BSE-specific unique stories in 5–13 Oct: 3 (Reuters CAS report M2; Chairman remark M1; Angel One update M7); 0 negative BSE-specific stories; no story dated 13 Oct. The "rally" headlines are syndications of one source (7.3). I did not score sentiment with a model (Bigdata.com connector failed to connect). | Groww news page lists nothing newer than ~1 week | none |
| **Analyst sentiment** | Split and static: Outperform (Macquarie ₹4,000) vs Underperform (Jefferies ₹2,940, Bernstein ₹2,820) vs Hold (Nuvama ₹3,240); mean ₹3,703.74 = +9.7% vs P0. No rating or target change found 25 Sep–13 Oct | v1 C6; searches | none |
| **Management tone** | Last public remarks 3 Sep (CEO Ramamurthi on CNBC-TV18): CAS has "few takers", index-option volumes fell since 3 Aug, BSE collating dealer feedback including delinking F&O expiry from CAS; an undated Bloomberg item (via AllMind) says CAS pricing has "largely stabilised" (date and text unverified). No October remark found; BSE's trading window is closed since 30 Sep. The SEBI Chairman spoke at the BSE Brokers' Forum (a broker association) on 10 Oct; no BSE Ltd management statement from that event was found | Kotak Neo, News Bytes, search | none |
| **Social sentiment** | **Not accessible.** Reddit 403, StockTwits "symbol not found", Google Trends 429; no dated social feed found by search. The only retail-style item is a promotional StockGro post (4 Oct), unusable | access tests this session | none |

### 7.3 Duplicate syndication, stale and promotional content

| Type | Finding |
|---|---|
| **Duplicate syndication (one story, many outlets)** | The Reuters CAS-rollback report (M2) appears in at least 10 outlets: Outlook Money (6 Oct 09:04), Niftytrader and Lapaas Voice (5 Oct), Business Today (6 Oct), Kotak Neo, DSIJ (10 Oct 11:00), ICICI Direct, Whalesbook, Finimize, News Bytes, Groww news page (as "Business Standard, 1 week ago"). Count as **one** signal from one unnamed-source Reuters story, not ten. Company-reported items (Angel One Sept update) are syndicated by ScanX and others the same way |
| **Stale** | DSIJ (10 Oct) re-runs the 5 Oct story; Swastika "15% slide since CAS rollout" and Groww news items are 1–3 weeks old; StockGro (4 Oct); analyst notes 3–8 weeks old; the Groww-page headline "SEBI chairman said nothing beyond the published paper is under consideration for BSE's equity derivatives" (Livesquawk) is untraced and about two weeks old |
| **Promotional / automated** | StockGro post by a SEBI-registered analyst (600 likes, misstates the 30 Sep move); Multibagg 13 Oct roundup is auto-generated ("no fresh database headline supplied") and cannot confirm the absence of news; Samco and Sahi blog pages contain historical errors; Angel One's holiday page lists Muhurat on 21 Oct, contradicted by the NSE holiday master (8 Nov); tradingview news mirror not used (terms of service) |
| **Contradicted figures resolved** | India VIX 13 Oct 14.12 (v1: Yahoo only) is now official; Nifty 22,721.95; Capital Markets +1.50% on 12 Oct confirmed from `index_daily.csv`; Muhurat date; Groww 14 Oct and Angel One 15 Oct dates now primary |

---

## 8. Which developments, before or at the 14 Oct open, would update or invalidate the v1 distribution

**v1 anchors (frozen record):** median R = 0 (P0 3,375.40), σ_R 2.48%, 90% close interval 3,246.83–3,507.94, 50% interval 3,322.33–3,428.83; gap G quantiles 5/25/50/75/95% = 3,333.81 / 3,368.22 / 3,375.40 / 3,386.68 / 3,413.52; scenario weights bear 26.6% / base 47.6% / bull 25.8%; v1's own invalidation rules (pre-open > P0+0.5% with peers firm kills the bear case; a SEBI circular adopting pure last-30-minute VWAP kills the bear case; a text keeping CAS for expiry settlement kills the bull case); subjective event grid p_event 0–15%.

Magnitudes below are **arithmetic anchors or descriptive analogues, not validated predictions** (`untested`/`descriptive_only`; analogue days were selected after the fact from press coverage and so overstate typical reactions).

| # | Development (if observed before or at the open) | Observable by | Direction for v1 | Anchors | Which v1 element changes |
|---|---|---|---|---|---|
| U1 | **SEBI circular adopting pure last-30-minute VWAP for derivative settlement, effective ≤ end-Oct** (the Reuters outcome) | SEBI listing/RSS; any time, incl. overnight | **Up**, but pre-priced | 5 first-reaction days in the dossier: +4.36, +3.14 (3–4 Sep), +4.39, +3.94, +1.54% (5–7 Oct), each smaller than the last in October (diminishing returns); no "confirmation" day exists in the sample (n = 0). BSE is already +10.81% from 1 Oct | Bear case invalidated per v1; shift weight to base/bull; widen σ (event grid p_event ≥ 0.10) |
| U2 | **Circular with blended VWAP, only partial relief, or CAS retained for expiry settlement** | same | **Down**, large | Arithmetic: full give-back of the 5–7 Oct rally = 3,046 (−9.76%); half = ≈3,201 (−5.2%). Analogues for adverse expiry/regime news: −4.58% (11 Sep 2025), −7.56% (21 Aug 2025), −1.17% close/−6% intraday (18 Jun 2025) | Bull case invalidated per v1; bear weight up; p_event grid upper end |
| U3 | Any SEBI/RBI/finance-ministry action on weekly expiry, STT, fees or margins | headlines | **Down**, tail | Dossier analogue closes: −6.56% (4 Jul 2025), −7.56% (21 Aug 2025), ≈−8% (1 Feb 2026 Budget), −7.30% (16 Feb 2026), −13.7% (29 Apr 2024) | Tail: P(R ≤ −4%) above v1's 4.4% |
| U4 | **No circular by the open** (the base case I expect to hold) | SEBI listing at 09:00 | None | Day 4 of the Chairman's "about a week" (to ~16–17 Oct) | None; v1 stands |
| U5 | Pre-open indicative price (09:08) outside v1 gap 5–95% band, i.e. < 3,333.81 or > 3,413.52 (−1.24% / +1.12%) | NSE pre-open | Follow the open | v1: close ≈ open × exp(I), σ_I 2.2% | Re-centre per v1 rule (quantile multipliers −3.7 / −1.4 / 0 / +1.4 / +3.5% at 5/25/50/75/95%) |
| U6 | Overnight US/Asia: S&P cash close or futures differing from the 21:47 IST level by x% | 08:30 IST | Sign of x | Workstream 03 slope 0.276 pp of gap per 1% S&P (CI 0.215–0.337; OOS R² 7.9%, validated, unstable: 0.03 in 2019, 0.68 in 2026). A ±1% change moves G by ±0.28 pp, versus a 5–95% gap half-width of ~1.2% | Gap centre only; no change to σ |
| U7 | GIFT Nifty (not observed) | 08:45 IST | Sign of Nifty gap | BSE gap ≈ 0.89 × Nifty gap (CI 0.77–1.01; rolling-250 β 1.39, unstable) | Gap centre |
| U8 | Brent > ≈$110 (+4%) or Hormuz escalation overnight | 08:30 IST | **Down**, via index | Workstream 03 found no BSE–Brent association (Holm p = 1.0), so effect is via Nifty beta and VIX, not a direct link | Widen σ, no centre change |
| U9 | Groww Q2 outcome (likely ~11:30 IST in-session): retail derivatives share, active clients, revenue vs Q2 FY26 ₹1,018.7 cr and Q1 FY27 | exchange filing | Sign of surprise | v1 already lists it as a scenario trigger; no consensus found | Intraday update only |
| U10 | Peer divergence: Angel One / MCX / CDSL / CAMS vs BSE > 2% in the first 30 min | live | Stock-specific flow | v1 rule | Per v1 |
| U11 | Holiday notice, market-wide halt or BSE-specific halt on 14 Oct | NSE circulars | Invalidates the whole forecast | NSE holiday master clean as of ≈22:10 IST | v1 whole-forecast invalidation |
| U12 | A BSE Ltd Q2 board intimation dated ≤ 16 Oct or a corporate action | NSE announcements | Event risk | History says Nov; no filing found | New scheduled event |
| U13 | Wire/press explanation that dates the 14:15 spike (e.g. a leak of the circular's content) | news | Would raise p_event | None found | Treat as U1/U2 |

**What does not warrant an update:** the 13 Oct volume spike (no cause; no sign-conditioned evidence); KOSPI/Nikkei declines (priced on 13 Oct); US bank earnings (mixed); delivery 36.07% (z −0.64); BSE's 10.8% rally by itself (descriptive; two clusters of post-rally outcomes went −3.1% and +0.6%, so no stable reversal or continuation pattern).

---

## 9. Contrary evidence and what would reverse each conclusion

| Conclusion | Contrary evidence | Would reverse it |
|---|---|---|
| No new catalyst after 16:55 IST | Search recall for same-day wire stories is poor (≈20 queries returned nothing dated 13 Oct for BSE/SEBI, but that is also true of the Nifty close itself); SEBI listings carry dates only and may lag (the Business Standard IPO-relaxation item dated 13 Oct is not on them); NSE announcements cover only filings; I cannot see Bloomberg/Reuters terminals | A wire story stamped 16:55–22:00 IST naming BSE/SEBI; a SEBI document posted late on 13 Oct |
| Spike has no found cause | The window overlaps the end of the afternoon block window (14:05–14:20), and informed trading ahead of an unpublished event cannot be excluded; absence of an NSE query is weak (the exchange queries mostly news-driven moves); BSE rose +1.36% that day | Trade-level data or a story dated 14:00–14:30 |
| 13 Oct was market-explained | At the rolling-250 β of 1.39 BSE underperformed by 0.86 pp; the peer mean beat BSE by 0.26 pp; β is unstable (0.28 to 1.82 by year) | A β estimate stable near 1.4 would make BSE a mild laggard; neutral for the forecast |
| 12 Oct was sector-wide, not stock-specific | Capital Markets index +1.5% includes BSE itself (constituent weight 15–23% per unverified sources); peers' dispersion is wide (CDSL +0.48% to Angel One +3.45%) | A peer-ex-BSE index series |
| Priced in (+10.8%) | The rally may have been justified by the leak, and price could keep rising if the circular lands; 5/5 analogue days were positive | U1-type circular with larger relief than the leak (e.g. also delinking timing changes, or fee relief) |
| US session is a negligible adjustment | S&P is unfinished (≈3.7h left at 21:47 IST); US CPI 18:00 IST on 14 Oct and the Beige Book come after the Indian close; Dow had swung from +0.47% to −0.34% | A large late US move (|x| > 1%) or a Fed-hike repricing |

---

## 10. Confirmations and corrections to v1 and the v1 dossier

| v1 statement | v2 finding |
|---|---|
| India VIX 14.12 and Nifty 22,721.94 on 13 Oct were Yahoo-only | **Official**: VIX 14.12 (−7.43%), Nifty 22,721.95 |
| Groww Q2 14 Oct: "soft, single Upstox list" | **Confirmed, primary** (NSE filing 7 Oct); call at 16:00 IST; Q1 precedent suggests an in-session outcome |
| Angel One Q2 15 Oct: soft | **Confirmed**, with a second interim dividend and a 22 Oct record date |
| BSE Q2 board date: "not yet intimated; estimates 6–12 Nov" | **Confirmed**: no intimation by 22:00 IST; 9 of 9 prior years 2–12 Nov |
| "Latest SEBI circular 7 Oct; no CAS circular" | **Still true at 22:00 IST** |
| "Exact time of the Reuters CAS story not found" | **Still not found**; the price-implied onset on 5 Oct is the 12:15 IST bar (inference only) |
| Delivery "40.9% on 12 Oct vs 41.3% 60-day mean" | Correct for 12 Oct; **13 Oct official 36.07%** (published 21:55 IST) |
| "Volume ratio on 13 Oct low-to-normal" | True for the day total (0.95× trailing-20 median); the 14:15 bar is 8.9× its slot median |
| Angel One page says Muhurat 21 Oct | **Wrong**; NSE holiday master: Sun 8 Nov |
| Nifty Capital Markets +1.5% on 12 Oct (brief) | Confirmed (+1.50%); 13 Oct +0.51% |
| Brent: v1 used Yahoo ≈ 104.4 for 13 Oct | Reuters/Investing show ≈105.6–106.0 at US hours; FRED Dated-Brent spot ($125–135) is a different instrument |
| Hang Seng +0.3% (Yahoo) | Reuters (via Dainik Jagran): "edged higher"; consistent |

---

## 11. Not found, failed access attempts, and effect on the forecast

| Item | Attempt and result | Effect |
|---|---|---|
| GIFT Nifty | NSE IX 403; investing.com 404; moneycontrol and Economic Times fetch blocked; searches returned only Aug 2026 items | Gap cannot be anchored to a Nifty futures quote; relies on S&P linkage (small) |
| Reuters/Bloomberg/PTI full text | Not reachable (paywalls, 403 for CNBC, TheStreet, Business Today; numbers via WebFetch summarisation, possible summariser error) | US bank figures marked "numbers not re-verified at primary" |
| 1-minute/5-minute BSE bars | Yahoo chart API 429 on both hosts; NSE `chart-databyindex` returned an empty series; NSE `quote-equity` 403 | Spike cannot be timed inside the 15-minute bar |
| BSE India announcements API | 403 | NSE copies of BSE Ltd filings used instead (complete for NSE-listed symbol) |
| Stooq, Frankfurter | Stooq connection reset; Frankfurter OK | USD/INR from ECB |
| NSE `latest-circular` | HTTP 500; NSE home page timed out | No NSE circular listing; changes to 14 Oct trading would show on the holiday master and filings (clean) |
| US BLS release calendar | 403 | CPI date from two Reuters-based reports, not the primary |
| Treasury 13 Oct par yield | Published after cutoff | Not used |
| Social sentiment | Reddit 403, StockTwits "symbol not found", Google Trends 429 | Channel unscored |
| Sub-5-minute tick or order-book data, short interest, securities lending | Not available | Cannot test the thin-book hypothesis |
| `/root/.ccr/README.md` | A read was denied by the permission classifier; not retried or worked around | No effect |
| Sell-side changes on 12–13 Oct | Searches found none; Business Today 5 Aug page 403 | JPM stance conflict unresolved |
| FII/DII timestamp | Payload has no time | Used with low weight |
| September 2026 BSE/NSE exchange volumes | Not found (also missing in v1) | Cannot update the volume-recovery thesis |

---

## 12. Consolidated claim register (brief rule 4)

| Claim | Definition | n | Period | Benchmark | Exceptions / sub-periods | Interval | Status |
|---|---|---|---|---|---|---|---|
| No SEBI CAS circular as of 22:00 IST | Absence from circular, press-release, consultation listings and RSS built 22:00:02 | 4 feeds | to 13 Oct | v1 check (7 Oct) | Listings carry dates only; may lag | n/a | `verified_source` |
| Chairman's remark verbatim | Text in SEBI PDF (Last-Modified 18:20 IST 10 Oct) | 1 document | 10 Oct | v1 secondary quotes | none | n/a | `verified_source` |
| BSE filed nothing on 13 Oct; no Q2 intimation | NSE announcements API, an_dt, 1,312 records | 1,312 | 2017–13 Oct 2026 | | API may omit non-NSE-dissemination items | n/a | `verified_source` |
| Spike abnormal | Volume ratio to slot median; rank; window share | 19 sessions (slot), 495 bars, 20 sessions | 15 Sep–13 Oct 2026 | other-19 slot median; other-19 window share | 20-session, post-CAS-era sample only; Yahoo-sourced bars | ratio 8.87× (5.1–10.2× bootstrap); share 53.7% vs 19.8% (18.0–27.6%) | `descriptive_only` |
| Spike cause | Explicit search of SEBI, BSE, NSE filings, block/bulk, news-verification, media | 8 hypotheses | 13 Oct | | Recall of media search limited | n/a | `not_found` |
| 13 Oct move market-explained | R − β·r_Nifty, β = 0.89 and rolling-250 | 2 days × 2 β | 12–13 Oct | residual sd of last 250 | β unstable | z −0.03 / −0.41 | `descriptive_only` |
| 12 Oct sector-wide | Equal-weight peer mean log return vs BSE | 5 peers | 12–13 Oct | | Wide dispersion; MCX −2.45% on 13 Oct | peers +1.96% vs BSE +1.30% | `descriptive_only` |
| Priced in | BSE vs Capital Markets and Nifty 1 Oct→13 Oct; post-cluster returns | 2 clusters | Sept–Oct 2026 | Capital Markets +4.84%, Nifty +1.34% | n = 2; cluster outcomes −3.09% and +0.58% | n/a | `descriptive_only` |
| Calendar items | Primary filings, NSE APIs, federalreserve.gov | 14 events | 14–28 Oct | v1 calendar (secondary) | WPI and Angel One call date secondary | n/a | `verified_source` (labelled where secondary) |
| Overnight conditions | Timestamped Reuters-based reports, ECB, Treasury, Korea/Japan outlets | ~15 series | 12–13 Oct | v1 Yahoo prints | Magnitudes differ across vendors; tickers untimed | n/a | `verified_source` / `unverifiable` (tickers) |
| Social sentiment | Access test | 3 sources | 13 Oct | | | n/a | `not_found` |
| Event-conditional reaction sizes (U1–U3) | Dossier analogue days | 5 + 3 | 2024–26 | unconditional σ_R 2.48% | Selected after the fact from press; n tiny | none | `untested` |
| GIFT Nifty | Public quote search | 5 attempts | 13 Oct | | | | `not_found` |

Counts: 0 hypothesis tests; roughly 60 descriptive statistics reported (listed in Appendix A output); no p-values; no multiplicity adjustment needed.

---

## Appendix A. Protocol and reproducibility

Script (outside the repo because only this file may be written): `/tmp/claude-0/-home-user-pred-18/01384b6e-cd11-5bbc-b7f5-2dd03125e5eb/scratchpad/news_analysis.py`, run as `cd /home/user/pred_18 && PYTHONPATH=src python3 -I …`. Protocol (written as the module docstring before any output was read):

* **C1** spike bar: volume ratio vs median of the same START slot in the other 19 sessions; rank among 495 bars by volume and by (high−low)/open; share of session bar volume inside 14:15–15:15; bootstrap (5,000 draws, seed 20261013) for the slot median and for the other-19 window share. **C2** top-8 bars by volume. **C3** residual = R − β·r_Nifty on 12 and 13 Oct, rolling 250 sessions ending the day before for β (no look-ahead), also β = 0.89; the 13 Oct Nifty return uses the official 22,721.95. **C4** peers: log(close/prev) for Angel One, CDSL, MCX, CAMS, KFin, equal-weight mean. **C5** BSE, Nifty 50 and Capital Markets levels (official 13 Oct 5,285.75), ATM-IV percentile (461 days), post-cluster returns. **C6** delivery z vs trailing 60 valid sessions.
* Bar timestamps are START times in IST; the 13 Oct 14:15 bar covers 14:15:00–14:29:59. Yahoo bars exclude some ticks (the NSE high 3,403.2 is above the bar high 3,400.9).

Key outputs (copied from the run): slot n = 19, median 121,449, spike 1,076,912, ratio 8.87; rank by volume 3 of 495, by range 4; flagged bars (≥5× slot median and range ≥ 2%): 24 Sep 10:00, 29 Sep 15:00, 13 Oct 14:15; window share 0.537 vs other-19 median 0.198 (excluding 29 Sep 0.194; max 0.852); 14:15 bar alone 0.272. C3: 12 Oct R 1.30% vs Nifty −0.70%, β250 1.42, residual 2.29% z 1.08, β 0.89 residual 1.92% z 0.88, share of last-250 with larger |residual| 0.268; 13 Oct R 1.35% vs Nifty 1.59%, β250 1.39, residual −0.86% z −0.41, β 0.89 residual −0.07% z −0.03, share 0.640. C4: 12 Oct peer mean 1.96%, BSE minus peers −0.66 pp; 13 Oct 1.60% and −0.26 pp. C5: 1 Oct→13 Oct BSE +10.81%, Capital Markets +4.84%, Nifty +1.34%; 7 Oct→13 Oct +0.58% / +0.53%; ATM IV 0.3854, percentile 0.332 (min 0.292, median 0.413, max 0.651); September cluster headline days +4.27, +3.09 (log) then next four −3.09% total; October cluster +4.29, +3.87, +1.53 then +0.58%. C6: delivery 36.07 vs mean 41.29, sd 8.16, z −0.64.

## Appendix B. Primary source URLs and stamps (all fetched 13 Oct 2026, 21:59–22:30 IST)

* SEBI circulars `https://www.sebi.gov.in/sebiweb/home/HomeAction.do?doListing=yes&sid=1&ssid=7&smid=0`; press releases `…sid=6&ssid=0&smid=0`; reports/consultations `…sid=4&smid=35&ssid=38`; RSS `https://www.sebi.gov.in/sebirss.xml` (Last-Modified 16:30:02 GMT; lastBuildDate 22:00:02 IST); Chairman's speech PDF `https://www.sebi.gov.in/sebi_data/attachdocs/oct-2026/1791636650448.pdf` (Last-Modified Sat 10 Oct 12:50:50 GMT).
* NSE archives: `…/content/indices/ind_close_all_13102026.csv` (14:20:38 GMT); `…/products/content/sec_bhavdata_full_13102026.csv` (16:25:37 GMT); `…/content/fo/BhavCopy_NSE_FO_0_0_0_20261013_F_0000.csv.zip` (13:54:02 GMT); `…/content/equities/block.csv`, `bulk.csv` (13:27:04 GMT).
* NSE APIs (www.nseindia.com): `api/corporate-announcements?index=equities&symbol=BSE` (also ANGELONE, GROWW, CDSL, MCX, CAMS, KFINTECH, NUVAMA, and a market-wide 13 Oct query), `api/corporate-board-meetings?index=equities&from_date=13-10-2026&to_date=24-10-2026`, `api/holiday-master?type=trading`, `api/fiidiiTradeReact`.
* Company filings: Groww `…/corporate/BILLIONBRAINS_07102026163914_EarningCall_inti_SD.pdf`; Angel One `…/corporate/ANGEL8896_06102026161317_October062026_Prior_intimation_of_dividend.pdf`.
* Other: ECB via `https://api.frankfurter.app/2026-10-01..2026-10-13?from=USD&to=INR`; Treasury `home.treasury.gov` daily par yield curve (to 9 Oct); `https://www.federalreserve.gov/newsevents/2026-october.htm` (Last-Modified 16:00:16 GMT); Reuters-based pages `https://www.investing.com/news/stock-market-news/us-stock-futures-steady-as-bank-earnings-inflation-data-loom-4945262`, `https://finance.yahoo.com/markets/stocks/articles/p-500-dow-futures-muted-112400648.html`, `https://finance.yahoo.com/markets/live/stock-market-today-tuesday-october-13-dow-sp-500-nasdaq-080236234.html`, `https://sundayguardianlive.com/business/us-stock-market-today-live-dow-jones-gains-047-sp-500-falls-015-nasdaq-drops-039-as-chip-stocks-slide-check-what-investors-should-know-304986/`; KOSPI `https://en.koreadaily.com/kospi-plunges-to-defend-6000-mark/`, `https://en.sedaily.com/finance/2026/10/13/kospi-plunges-6-percent-falls-below-6000-on-memory-supply`; Multibagg `https://multibagg.ai/market-pulse/articles/top-value-traded-india-today-cmv6la04c000636nrw84rxga1`; Kotak Neo `https://www.kotakneo.com/news/regulations/closing-auction-session-sebi-derivatives-settlement-price/`; ScanX `https://scanx.trade/stock-market-news/companies/angel-one-client-base-rises-17-3-yoy-39-98-mn-sep-2026/52798476`.
