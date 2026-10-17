# Audit of the supplied "TradingView" input (sections 1–2 of the v2 brief)

Input: `data/raw/tradingview/BSE_intraday_30d_1.xlsx` (uploaded 2026-10-13). Machine audit: `src/audit_xlsx.py` → `results/xlsx_audit.json`, cleaned 15-minute table `data/processed/xlsx_15m_clean.csv`.

## 1. What the input actually is

| Item | Finding | Evidence |
|---|---|---|
| **Source** | **Yahoo Finance chart API, not TradingView.** The workbook's own Notes sheet says "Source: Yahoo Finance chart API (NSE prices, INR)". No TradingView chart, link, screenshot, indicator setting or export metadata was supplied, and the Claude-in-Chrome tools are not present in this session, so **no TradingView chart has been inspected**. | Notes sheet; `ToolSearch` found no `mcp__claude-in-chrome__*` tools |
| TradingView content actually read | One read of the public, not-logged-in page `tradingview.com/symbols/NSE-BSE/` through a summarising fetch tool (internally inconsistent: e.g. 1-day change 1.36% vs 1.31%, technicals "Neutral" vs "buy"). Stored in `data/raw/tradingview/public_page_NSE-BSE_summary_2026-10-13.md`; **not used as a model input** | that file |
| Ticker / exchange | The sheets carry no ticker column. Identity is established by data: 20/20 session closes equal the official NSE closes of NSE:BSE to the paisa; highs/lows within ₹4.2; the Notes say "BSE Ltd (NSE: BSE)" | `results/xlsx_audit.json` |
| Instrument / currency | Common equity (series EQ), INR; all prices are multiples of the ₹0.05 tick | audit: 0 prices off-tick |
| Time zone / bar labelling | IST; the label is the **bar start** time (09:15 … 15:15). First bar always 09:15; last bar 15:15 (covers 15:15–15:30) | audit; Notes |
| Timeframes / range | 15-min (495 rows), 30-min (255), 1-hour (135); 20 sessions, 2026-09-15 → 2026-10-13 | audit |
| Latest candle | 2026-10-13 15:15–15:30. **Not forming**: the market had closed, its close ₹3,375.40 equals the official NSE close, volume 26,268 | audit; NSE bhavcopy |
| Live vs delayed | A static snapshot; workbook created 2026-10-13 15:52:08 (zone not stated; container clock is UTC → ≈21:22 IST, after the close). Not a live feed. All bars are time-stamped ≤ 15:30 IST on 13-Oct, i.e. before the v1 cutoff (16:55 IST) | file properties |
| Sessions | Regular session only (NSE cash equities have no extended hours). The pre-open call auction (09:00–09:08) is not in the bars, so the **first bar's open is the first continuous-session trade, not NSE's official open** (differences up to ₹11.7 vs the NSE open in this window). The closing-auction window is inside the 15:15 bar | audit |
| Adjusted vs unadjusted | Unadjusted per the Notes. No corporate action falls in the window (2:1 bonus ex 2025-05-23; ₹10 dividend ex 2026-07-10), so adjusted = unadjusted here; verified against NSE unadjusted closes | audit |
| Chart type | Ordinary OHLC time bars. Not Heikin Ashi/Renko: bar opens continue from the previous close (max gap 0.19%) and every price sits on the tick grid, which synthetic candles would violate | audit |
| Indicators | **None.** The workbook has OHLCV columns only; no indicator values or settings were supplied | file |
| Volume | Yahoo's feed volume in shares for the NSE listing (the only venue). Per-session total is **87–100% of NSE's official daily volume (mean 95%)**, also on complete 25-bar sessions, so it is not a reconciled exchange total; the cause (auction/other prints not in the feed?) is **not established**. The 1-hour sheet volume is defective (16 hourly bars show zero where the 15-minute bars have volume). The 15:15 bar volume is 0 on 6 sessions | audit |
| Ordering / duplicates / nulls | Sorted; 0 duplicate timestamps; 0 nulls | audit |
| Missing bars | The 15:15 bar is missing on 17-Sep, 22-Sep, 29-Sep, 8-Oct, 9-Oct (as the Notes say), in all three timeframes | audit |
| Internal consistency | 0 OHLC-inconsistent bars. 30-min and 1-hour bars reproduce exactly from the 15-min bars (OHLC); volumes agree except the defective 1-hour zeros | audit |
| Match to NSE daily OHLCV | Closes: 20/20 identical. Opens: up to ₹11.7 different (auction vs first trade). Highs ≤ NSE high by up to ₹4.0; lows ≥ NSE low by up to ₹4.2 (extreme ticks/auction prints not captured) | audit |
| Match to the 15-min bars I fetched earlier (summarising tool) | 495 overlapping bars: 0 OHLC mismatches (> ₹0.05), 2 volume mismatches, both first-bar volumes (16-Sep and 7-Oct) that the earlier fetch had at about half the workbook value; the workbook totals reconcile better | audit |
| Screenshots | None supplied; therefore no value in this study comes from reading pixels | — |

**Correction to earlier statements.** My earlier note that bars' volume runs below NSE's because the feed lacks "auction volume" (DEVIATIONS #14, #17) was a hypothesis. The workbook shows the shortfall persists on complete sessions, so the cause is unknown. Also, the earlier first-bar volume share (8.4%) was inflated relative to the workbook's 6.9% for the common sessions only because two fetched first bars were understated; the workbook is preferred for overlapping dates.

## 2. What the inputs support

| Purpose | Workbook alone | With the rest of the repo | Remaining gap and effect |
|---|---|---|---|
| Longer-term trend / regime | No (20 sessions) | Yes: NSE daily OHLCV 2017-02 → 2026-10-13 (2,388 sessions) | none material |
| Recent daily price and volume | Aggregates match NSE; NSE daily is better | Yes | none |
| Intraday structure / session patterns | Partly: 20 sessions (15 with the full 25 bars, 5 missing the 15:15 bar) | Union with the earlier fetched Yahoo bars (Aug 17 →) ≈ 45 sessions, all post-closing-auction | low statistical power; no pre-open prices, no order book, no auction-price series → only descriptive patterns |
| Reactions to earnings, news, stress | No | Daily data + dossiers: 7 earnings events, ≈ 20 regulatory/news events, stress sets E1–E3 | small samples; no verified consensus for most quarters |
| Model training and evaluation | No (cannot train or back-test on 20 sessions) | Daily walk-forward done in v1 (1,887 forecasts) | intraday models cannot be trained; none is claimed |
| Overnight / cross-asset information | No | FRED (USD/INR, Brent, US 10-year, S&P 500, VIX) and ECB rates acquired; lags noted | FRED series lag by 1–10 days; GIFT Nifty and live futures unavailable here |
| TradingView-specific content (indicators, technical rating history, user chart annotations) | **Not supplied** | public-page summary only | cannot be back-tested; not used as a signal |

A screenshot or a 30-day export alone cannot support a comprehensive back-test or an exact next-day trajectory, and none is claimed.
