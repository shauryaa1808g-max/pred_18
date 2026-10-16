"""Specialist D of the H/L study: do extra parameters (VIX / implied vol, US overnight, Indian market and peers, BSE volume and position, calendar, post-open block)
make the day's HIGH and LOW more precise?  Report: research/hl/D_features.md.   Baseline = src/hl_model.py (S6 volatility x filtered historical simulation).

Everything is a walk-forward RE-SCALING / RE-LOCATING of the baseline, so that "no information" reproduces the baseline exactly:
  scale   : sigma'_t = sigma_S6,t x exp(gamma' x_t).  gamma from a Poisson pseudo-ML (log-link) ridge regression of a range proxy on standardised features with the baseline sigma as
            offset (the baseline's HAR/GARCH terms are therefore already inside the offset; the regression estimates the features' INCREMENTAL effect).  Ridge strength by forward-chaining
            CV inside the training sample (the grid includes "infinite" = baseline).  Refit every 20 sessions on sessions strictly before the block.
            pre-open  proxy y = max(Hp,0) + max(-Lp,0)  (= range of the path P0 -> day, "range including the previous close");  post-open y = ln(H/L)
  tails   : the same regression done separately for the high side [max(Hp,0), or HO] and the low side [max(-Lp,0), or -LO] (asymmetric scale; signed + unsigned features)
  location: median shift of H and L in sigma' units, ridge OLS of the winsorised standardised residual on signed features (post-open: quantiles clipped at HO >= 0 and LO <= 0)
  quantiles: the baseline's filtered historical simulation, trailing 500 sessions of V_s / sigma'_s (minus the walk-forward shift), times sigma'_t (plus the shift).
Timestamp rules of every feature: build_features() docstring and TIMESTAMPS below.  No network access is used by hl2_forecast(); the files results/hl2_fill_*.csv hold the few
inputs the repo's processed files lacked (13-15 Oct 2026 index / F&O / breadth / peers rows, Yahoo S&P and US VIX for those days, USD/INR from the ECB via Frankfurter);
`python3 src/hl_model2.py --refresh-fill` rebuilds them (network).

Usage (repo root):
  python3 src/hl_model2.py --eval                      full walk-forward evaluation -> results/hl2_*.csv   (several minutes)
  python3 src/hl_model2.py --leakage                   junk-replacement leakage test -> results/hl2_leakage.csv
  python3 src/hl_model2.py --date 2026-10-16 --open 3450 [--variant SL_f] [--json] [--save]
  python3 src/hl_model2.py --refresh-fill              (network)
Importable: hl2_forecast(date, open_price=None, variant=None) -> dict of the same shape as hl_model.hl_forecast.
"""
from __future__ import annotations

import argparse
import datetime as dt
import glob
import hashlib
import io
import json
import time
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

import hl_model as H1
import metrics as M
import models as P
from common import EPS, GRID, load_bse, load_index, load_breadth, targets

OUT = Path("results")
PROC = Path("data/processed")
RAW = Path("data/raw")
FILL = {k: OUT / f"hl2_fill_{k}.csv" for k in ("index", "breadth", "peers", "iv", "delivery", "us", "expiries")}
USDINR_FILE = OUT / "hl2_data_usdinr_ecb.csv"
RESULTS_DATES = Path("data/results_dates.csv")
P_NOW = H1.P_NOW
LV = H1.LV
WIN = H1.WIN
START = H1.START                    # first evaluated session (index 750, 2020-02-25), as the baseline
W = H1.W                            # bootstrap window 500
FIT_START = 650                     # first session for which a feature multiplier is fitted (sigma S6 exists from 500; needs >= MIN_ROWS training rows)
MIN_ROWS = 120                      # a feature column is used only if it has >= 120 non-missing training observations; a fit needs >= 120 rows
BLOCK = P.REFIT                     # 20 sessions
LAM_EVERY = 5                       # the ridge strength is re-selected every 5th refit (every 100 sessions), coefficients every refit
LAMS = (0.001, 0.003, 0.01, 0.03, 0.1, 0.3, 1.0, np.inf)       # np.inf = no features = baseline
CV_CUTS = (0.40, 0.55, 0.70, 0.85, 1.0)                        # forward-chaining folds (fractions of the training rows)
PEERS_USED = ["CDSL", "MCX", "ANGELONE", "CAMS", "IEX", "KFINTECH", "NUVAMA", "MOTILALOFS", "ANANDRATHI"]
STALE_DAYS, STALE_DAYS_LAG = 6, 9   # a US/FRED observation older than this (calendar days before the session) is treated as missing
WIN_Q = (0.01, 0.99)                # features are winsorised at the 1st / 99th percentile of the training rows
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"

# ----------------------------------------------------------------------------------------------- feature menu (names, blocks, timestamp rules)
SCALE_BLOCKS = {
    "a":  ["lnvix", "dlnvix", "vix_rv_spread"],
    "a2": ["lniv", "iv_skew", "iv_rv_spread"],
    "b":  ["abs_sp", "lnvixus", "dvixus", "abs_usdinr", "abs_brent", "abs_dxy", "abs_us10y"],
    "c":  ["nifty_lnrange", "nifty_abs", "cap_lnrange", "br_tails", "br_absadv", "peers_lnrange", "mkt_turn_z"],
    "d":  ["lnrange_y", "absgap_y", "turn_z60", "deliv_z60", "pk10_rel", "pk20_rel"],
    "e":  ["tue", "wed", "thu", "fri", "month_end", "post_hol", "exp_day", "results_next"],
    "o":  ["absgap_z", "beyond_any", "orel_abs"],
}
LOC_BLOCKS = {
    "b": ["sp_ret", "usdinr_ret", "dvixus", "brent_ret", "dxy_ret", "us10y_chg"],
    "c": ["nifty_ret", "cap_ret", "br_adv", "peers_ret", "dlnvix"],
    "d": ["ret1", "ret5", "ret20", "close_loc_c", "dist_hi250", "dist_lo250", "streak", "rel_nifty"],
    "o": ["gap_z", "orel_c", "beyond_signed"],
}
TIMESTAMPS = {
    "lnvix, dlnvix, vix_rv_spread": "India VIX close of the previous BSE session t-1 (NSE index file; the market value is fixed at 15:30 IST t-1, the file is posted ~23:20 IST t-1); spread = ln(VIX/100/sqrt(252)) - ln(Nifty 10-session realised daily vol to t-1)",
    "lniv, iv_skew, iv_rv_spread": "BSE ATM implied vol from NSE F&O settlement prices of t-1 (bhavcopy posted ~17:00 IST t-1; src/options_iv.py); skew = iv_lo_otm - iv_hi_otm; spread = ln(IV/sqrt(252)) - ln(BSE 20-session realised daily vol to t-1)",
    "abs_sp, sp_ret": "S&P 500 close of the last US session dated strictly before the Indian session date (closes 01:30 IST on the session date: lag provably zero); FRED SP500, Yahoo ^GSPC for the 13-15 Oct 2026 days FRED lacks",
    "lnvixus, dvixus": "US VIX (VIXCLS, closes 16:15 ET = ~01:45 IST of the session date, lag zero); same date rule; Yahoo ^VIX for 13-15 Oct 2026",
    "abs_usdinr, usdinr_ret": "ECB euro reference rate USD/INR (fixed 14:15 CET, posted ~16:00 CET) of the last date strictly before the session date: lag zero; data/raw/macro/usdinr_ecb_2017_2026.json is an HTML error page, so the series comes from Frankfurter (results/hl2_data_usdinr_ecb.csv)",
    "abs_brent, brent_ret, abs_dxy, dxy_ret, abs_us10y, us10y_chg": "FRED DCOILBRENTEU / DTWEXBGS / DGS10: publication lag NOT provably zero, so the value is shifted ONE MORE observation back (observation dated before the session date, then one more earlier); an observation older than 9 days is missing",
    "nifty_*, cap_*, br_*, peers_*, mkt_turn_z": "Nifty 50 / Capital Markets index, NSE breadth (bhavcopy), peers' bhavcopy rows (CDSL MCX ANGELONE CAMS IEX KFINTECH NUVAMA MOTILALOFS ANANDRATHI), all of the previous BSE session t-1 (bhavcopy posted ~16:34 IST, index file ~23:20 IST); 60-session z-scores / means include t-1 and nothing later",
    "lnrange_y, absgap_y, turn_z60, deliv_z60, pk10_rel, pk20_rel, ret1, ret5, ret20, close_loc_c, dist_hi250, dist_lo250, streak, rel_nifty": "BSE's own official bars of t-1 and earlier (bhavcopy ~16:34 IST t-1; delivery % ~18:00 IST t-1); rolling windows end at t-1",
    "tue..fri, month_end, post_hol": "calendar of the exchange sessions (known in advance); month_end = one of the last two sessions of the calendar month; post_hol = previous session >= 4 calendar days earlier",
    "exp_day": "BSE Ltd monthly F&O expiry dates read from the contract rows of data/raw/fo_bse (+ fill); defined only from 2024-11-18 (earlier = missing)",
    "results_next": "data/results_dates.csv first_tradable_session (results announced after market; defined only from 2024-11-13; 7 events)",
    "absgap_z, gap_z, beyond_any, beyond_signed, orel_abs, orel_c": "POST-OPEN only: official open O of the session (NSE pre-open auction, final 09:08 IST) vs P0 = close t-1, S6 sigma of t (pre-open), and yesterday's high / low (bonus-adjusted)",
}


# ----------------------------------------------------------------------------------------------- network step: fill-in files
def refresh_fill(last="2026-10-15") -> None:
    """NETWORK (run once; results are cached in results/hl2_fill_*.csv).  Rows the repo's processed files lack: index/VIX, F&O (IV), breadth, peers for sessions after the last processed index row up to `last`,
    BSE delivery % for sessions without it, Yahoo S&P 500 and US VIX closes, USD/INR (ECB via Frankfurter) history.  Nothing dated after `last` is requested."""
    import requests
    import build_dataset as BD
    import options_iv as OIV
    from fetch_nse import CA
    OUT.mkdir(exist_ok=True)
    meta = {"retrieved_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "last_session_requested": last, "sources": {}}
    d = H1.load_ohlc(); ix0 = load_index(); br0 = load_breadth()
    days = [x for x in d.index if x > ix0.index.max() and x <= pd.Timestamp(last)]
    s = requests.Session(); s.headers["User-Agent"] = UA

    def get(url, **kw):
        for k in range(4):
            try:
                r = s.get(url, timeout=60, verify=CA, **kw)
                if r.status_code in (200, 404):
                    return r
            except requests.RequestException:
                pass
            time.sleep(2 * (k + 1))
        raise RuntimeError(f"cannot fetch {url}")

    idx_rows, iv_rows, exp_rows, deliv_rows = [], [], set(), []
    for day in days:
        k8, k8b = day.strftime("%d%m%Y"), day.strftime("%Y%m%d")
        r = get(f"https://nsearchives.nseindia.com/content/indices/ind_close_all_{k8}.csv")
        if r.status_code == 200 and r.content[:5] == b"Index":
            p = Path(f"/tmp/hl2_idx_{k8}.csv"); p.write_bytes(r.content)
            ix = BD.read_idx(p); ix["date"] = day; idx_rows.append(ix)
        r = get(f"https://nsearchives.nseindia.com/content/fo/BhavCopy_NSE_FO_0_0_0_{k8b}_F_0000.csv.zip")
        if r.status_code == 200 and r.content[:2] == b"PK":
            z = zipfile.ZipFile(io.BytesIO(r.content)); f = pd.read_csv(z.open(z.namelist()[0])); f = f[f["TckrSymb"] == "BSE"]
            for e in pd.to_datetime(f["XpryDt"]).unique():
                exp_rows.add(pd.Timestamp(e))
            row = OIV.day_iv(f, day)
            if row:
                iv_rows.append(row)
        r = get(f"https://nsearchives.nseindia.com/products/content/sec_bhavdata_full_{k8}.csv")
        if r.status_code == 200 and r.content[:6] == b"SYMBOL":
            p = Path(f"/tmp/hl2_sec_{k8}.csv"); p.write_bytes(r.content)
            sec = BD.read_sec(p); b = sec[(sec.symbol == "BSE") & (sec.series == "EQ")]
            if len(b):
                deliv_rows.append({"date": day, "deliv_pct": float(b["deliv_pct"].iloc[0])})
    if idx_rows:
        iw = pd.concat(idx_rows, ignore_index=True).pivot_table(index="date", columns="name", values=["open", "high", "low", "close", "volume"])
        iw.columns = [f"{n}_{f}" for f, n in iw.columns]; iw.to_csv(FILL["index"])
    if iv_rows:
        pd.DataFrame(iv_rows).set_index("date").to_csv(FILL["iv"])
    pd.DataFrame({"expiry": sorted(exp_rows)}).to_csv(FILL["expiries"], index=False)
    pd.DataFrame(deliv_rows).to_csv(FILL["delivery"], index=False)
    # breadth + peers from the local UDiFF bhavcopies (the same code as build_dataset.main)
    br_rows, pe_rows = [], []
    for day in [x for x in d.index if x > br0.index.max() and x <= pd.Timestamp(last)]:
        z = RAW / "udiff" / f"{day.strftime('%Y%m%d')}.zip"
        if not z.exists():
            continue
        dd = BD.read_udiff(z); eq = dd[dd["series"].isin(["EQ", "BE", "BZ", "BL"])].copy(); eq["date"] = day; eq["src"] = "udiff"
        pe_rows.append(eq[eq["symbol"].isin(BD.PEERS)])
        u = eq[(eq["series"] == "EQ") & (eq["prev"] > 0) & (eq["close"] > 0) & (eq["turnover_cr"] >= 1.0)].copy(); r_ = u["close"] / u["prev"] - 1.0
        br_rows.append({"date": day, "n_liquid": len(u), "adv_share": float((r_ > 0).mean()), "dec_share": float((r_ < 0).mean()), "med_ret": float(r_.median()),
                        "mean_ret_w": float(r_.clip(r_.quantile(.01), r_.quantile(.99)).mean()), "turnover_cr_eq": float(eq.loc[eq["series"] == "EQ", "turnover_cr"].sum()),
                        "n_ge_5pct_up": int((r_ >= .05).sum()), "n_ge_5pct_dn": int((r_ <= -.05).sum())})
    if br_rows:
        pd.DataFrame(br_rows).set_index("date").to_csv(FILL["breadth"])
    if pe_rows:
        pd.concat(pe_rows, ignore_index=True).to_csv(FILL["peers"], index=False)
    # Yahoo S&P 500 and US VIX daily closes (US session dates), 2026-08-15 .. last
    us = {}
    for nm, sym in (("sp", "%5EGSPC"), ("vix", "%5EVIX")):
        j = get(f"https://query2.finance.yahoo.com/v8/finance/chart/{sym}?interval=1d&range=3mo").json()["chart"]["result"][0]
        c = pd.Series(j["indicators"]["quote"][0]["close"], index=pd.to_datetime(j["timestamp"], unit="s", utc=True).tz_convert("America/New_York").tz_localize(None).normalize()).dropna()
        us[nm] = c[~c.index.duplicated(keep="last")]
    uf = pd.DataFrame(us); uf = uf[uf.index <= pd.Timestamp(last)]; uf.index.name = "date"; uf.to_csv(FILL["us"])
    # USD/INR, ECB reference rates via Frankfurter
    r = get(f"https://api.frankfurter.app/2017-01-01..{last}?from=USD&to=INR", allow_redirects=True)
    rates = r.json()["rates"]
    pd.DataFrame({"date": list(rates), "usdinr": [v["INR"] for v in rates.values()]}).to_csv(USDINR_FILE, index=False)
    meta["rows"] = {"index": len(idx_rows), "iv": len(iv_rows), "breadth": len(br_rows), "us_last": str(uf.index.max().date()), "usdinr": len(rates)}
    meta["sources"] = {"index": "nsearchives ind_close_all", "iv": "nsearchives NSE F&O UDiFF bhavcopy via src/options_iv.day_iv", "delivery": "nsearchives sec_bhavdata_full", "us": "Yahoo chart ^GSPC ^VIX",
                       "usdinr": "api.frankfurter.app (ECB reference rates)", "breadth_peers": "data/raw/udiff local zips"}
    (OUT / "hl2_fill_meta.json").write_text(json.dumps(meta, indent=1)); print(json.dumps(meta, indent=1))
