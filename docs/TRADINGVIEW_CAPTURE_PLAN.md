# TradingView capture plan for NSE:BSE (read-only) and how it feeds a v2 forecast

Status: **not executed** — at the time of writing no `mcp__claude-in-chrome__*` tools were present in the cloud session, so no TradingView data has been used anywhere in `FORECAST_REPORT.md` or in `results/forecast_record_2026-10-14.json` (v1, cutoff 2026-10-13 16:55 IST, immutable).

## Ground rules
1. **Read-only.** No alerts, orders, drawings saved, ideas posted, layout edits or account/settings changes. Only open public chart/symbol pages and read what they show.
2. One browser tab at a time (a single Chrome cannot be driven by parallel agents). Record the on-screen timestamp and data-delay label of every page; TradingView NSE quotes may be 15 minutes delayed unless the account has the exchange entitlement.
3. If the extension asks for site permission, stop and wait; do not work around it. After 2–3 failed actions, stop and report.
4. TradingView content is a **new, third-party source**. Everything taken from it is tagged `[TV]` and cross-checked against the NSE archive where an overlap exists (daily OHLC, volume). Technical "ratings" and community ideas are computed from / about the same price series and are treated as *untested hypotheses*, not independent confirmations.

## What to capture (priority order)
**A. NSE:BSE itself**
1. Quote header: last, change, volume, time stamp, "delayed/real-time" label.
2. 1-minute and 5-minute bars for the last 5–10 sessions via *Export chart data* (CSV) if the plan allows, otherwise 15-minute screenshots with OHLC legend. These replace the third-party, summarised Yahoo bars and are validated with `src/validate_intraday.py`.
3. Technicals tab: oscillator / moving-average summary and the individual values (RSI, MACD, ADX, Stoch, MAs). Compare with `results/snapshot.json`.
4. Overview / Financials / Forecasts tabs: market cap, P/E, EPS TTM, dividend, quarterly income statement (check Q1 FY27 PAT ₹872.7 cr), analyst price targets and rating counts (check vs dossier 01).
5. News tab: headline, source, timestamp (check vs dossier 02 timeline); Ideas tab: only to read sentiment *counts*, flagged promotional/bot-prone.
6. Peers: NSE:CDSL, NSE:MCX, NSE:ANGELONE, NSE:NUVAMA, NSE:CAMS (13-Oct changes; check vs `results/snapshot.json`).

**B. Market context for a later (post-cutoff) update** — only if the update is made on 14-Oct before the open
NIFTY, BANKNIFTY, INDIAVIX official 13-Oct closes; GIFT Nifty (`NSEIX:NIFTY1!`); S&P 500 / Nasdaq futures; Nikkei, KOSPI, Hang Seng on 14-Oct; Brent, USDINR, US10Y, DXY; US bank earnings reaction. These are the overnight inputs the v1 gap model deliberately did not condition on.

## How it changes the forecast (rules fixed now, before any TradingView number is seen)
* **v1 is never edited.** A v2 record gets its own file (`results/forecast_record_2026-10-14_v2.json`), its own later cutoff timestamp and a list of exactly which new inputs it used.
* Scale models (S6, S4, HAR) are unaffected by TradingView data except through newly available *official* daily/1-minute exchange-type bars; their validated form uses daily OHLC only.
* The only pre-registered way to use an observed **open** is the conditional update already in the report: close ≈ open × exp(I) with σ_I from the S6 intraday model (use the NSE pre-open indicative price at 09:08 IST as the open proxy).
* Overnight information (GIFT Nifty, Asia, US futures) can shift the *gap median* only through a relationship estimated on history. No such history is available to me in-sandbox, so a v2 shift would be a **judgement**, labelled subjective, and would not alter the validated intervals.
* No directional claim is added unless it passes a walk-forward test; TradingView's technical rating cannot be back-tested here (its historical values are not retained), so it is reported but not used.
* Success criterion for the whole exercise stays the same: the stored v1 record is scored after the session with `src/score_forecast.py`; a v2 is scored separately and compared.

## Ready-to-paste prompt for a Claude session that has Claude in Chrome connected
> Open the repo `shauryaa1808g-max/pred_18`, branch `claude/dreamy-albattani-k94wba`. Read `FORECAST_REPORT.md` and `docs/TRADINGVIEW_CAPTURE_PLAN.md`. Using Claude in Chrome (read-only, one tab, my existing TradingView sign-in), capture section A (and B if it is before the 14-Oct open) for NSE:BSE, save raw CSV/screenshot-derived tables under `data/raw/tradingview/` with page timestamps, cross-check against the NSE archive, and write `docs/TRADINGVIEW_FINDINGS.md`. Do not change `results/forecast_record_2026-10-14.json`; if you update the forecast, write a separate v2 record and explain every changed input.
