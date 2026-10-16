"""Specialist D of the H/L study: do extra parameters (VIX / implied vol, US overnight, Indian market and peers, BSE volume and position, calendar, post-open block)
make the day's HIGH and LOW more precise?   Report: research/hl/D_features.md.     Baseline = src/hl_model.py (S6 volatility x filtered historical simulation, FHS).

Every variant is a walk-forward RE-SCALING and/or RE-LOCATING of the baseline, so that "no information" reproduces the baseline exactly:
  scale    sigma'_t = sigma_S6,t x exp(z_t' gamma): gamma from a log-link (Poisson pseudo-ML) ridge regression of the ratio  y_s / sigma_S6,s  on standardised features;
           y = max(Hp,0)+max(-Lp,0) (pre-open, range of the path P0 -> day) or ln(H/L) (post-open); tail-specific variants regress the high side and the low side separately.
           Ridge strength by forward-chaining CV inside the training rows; the grid contains "infinite" (= baseline, no features).  Refit every 20 sessions on sessions strictly before the block.
  location the same walk-forward ridge OLS on the (winsorised) standardised residual of H and of L: a translation of the whole residual distribution (post-open: clipped at HO >= 0, LO <= 0).
  quantiles the baseline's filtered historical simulation: trailing 500 sessions of V_s / sigma'_s (minus the location shift of the current fit), times sigma'_t (plus the shift).
Timestamp rule of every feature: FEATURES below (also written to results/hl2_feature_timestamps.csv).  hl2_forecast() uses no network; results/hl2_fill_*.csv hold the few inputs the repo's
processed files lack for 13-15 Oct 2026 (index / VIX, F&O implied vol, breadth, peers, delivery %, S&P 500 and US VIX, USD/INR); `--refresh-fill` rebuilds them (network).

Usage (repo root; python3 src/hl_model2.py ...):
  --refresh-fill [--fill-cache DIR]     (network) rebuild results/hl2_fill_*.csv and results/hl2_data_usdinr_ecb.csv
  --baseline-check                      reproduce the baseline (Final pinball, misses) before anything else       -> results/hl2_baseline_repro.csv
  --eval                                full walk-forward evaluation of every pre-fixed variant                      -> results/hl2_*.csv   (several minutes)
  --leakage                             junk-replacement leakage test (data from the target session on replaced)     -> results/hl2_leakage.csv
  --date 2026-10-16 [--open 3450] [--variant P_SL_f] [--json] [--save]   forecast in the shape of hl_model.hl_forecast (the baseline unless a variant was adopted)
Importable: hl2_forecast(date, open_price=None, variant=None) -> dict (same shape as hl_model.hl_forecast).
"""
from __future__ import annotations

import argparse
import datetime as dt
import io
import json
import sys
import time
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hl_model as H1  # noqa: E402
import metrics as M  # noqa: E402
import models as P  # noqa: E402
from common import EPS, GRID, load_breadth, load_index, targets  # noqa: E402

OUT, PROC, RAW = Path("results"), Path("data/processed"), Path("data/raw")
FILL = {k: OUT / f"hl2_fill_{k}.csv" for k in ("index", "breadth", "peers", "iv", "delivery", "us", "expiries")}
USDINR_FILE = OUT / "hl2_data_usdinr_ecb.csv"
P_NOW, LV, WIN, START, W = H1.P_NOW, H1.LV, H1.WIN, H1.START, H1.W
BLOCK = P.REFIT                       # 20 sessions between refits, as the project
FIT_START = 640                       # first refit block (rows 500..639 = 140 training rows); the baseline's sigma exists from session 500
MIN_ROWS = 120                        # a feature column is used only if it has >= 120 non-missing training rows
MIN_ROWS_CV = 40                      # same inside a CV fold
LAM_EVERY = 5                         # the ridge strength is re-selected by CV every 5th refit (every 100 sessions); coefficients are refitted at every refit
LAMS = (0.01, 0.03, 0.1, 0.3, 1.0, 3.0, 10.0, np.inf)       # np.inf = no features (= baseline)
CV_CUTS = (0.5, 0.625, 0.75, 0.875, 1.0)                    # forward-chaining folds: train on rows[:cut_k], validate on rows[cut_k:cut_k+1]
WINS = (0.01, 0.99)                   # features and location targets are winsorised at the 1st / 99th percentile of the training rows
STALE, STALE_LAG = 6, 9               # a US observation older than this many calendar days before the session is treated as missing
PEERS_USED = ["CDSL", "MCX", "ANGELONE", "CAMS", "IEX", "KFINTECH", "NUVAMA", "MOTILALOFS", "ANANDRATHI"]
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
UA_SHORT = "Mozilla/5.0"                # Yahoo rate-limits (429) the long browser string
PROXY_CA = "/root/.ccr/ca-bundle.crt" if Path("/root/.ccr/ca-bundle.crt").exists() else True
EXP_START, RES_START = pd.Timestamp("2024-11-18"), pd.Timestamp("2024-11-13")

# ----------------------------------------------------------------------------------------------- the feature menu (names, blocks, timestamp rules)
SCALE_FEATS = {
    "a": ["lnvix", "dlnvix", "vix_rv_spread"],
    "b": ["abs_sp", "lnvixus", "dvixus", "abs_usdinr", "abs_brent", "abs_dxy", "abs_us10y"],
    "c": ["nifty_lnrange", "nifty_abs", "bank_lnrange", "br_tails", "br_absadv", "peers_lnrange_rel", "mkt_turn_z"],
    "d": ["lnrange_y", "absgap_y", "turn_z60", "deliv_z60", "pk10_rel", "pk20_rel", "dist_hi250", "dist_lo250"],
    "e": ["tue", "wed", "thu", "fri", "month_end", "post_hol"],
    "s": ["lniv", "iv_skew", "iv_rv_spread", "exp_day", "results_next", "cap_lnrange"],       # SHORT samples (BSE option IV from 2024-11-29, expiry flags, results flags, Capital Markets index high/low from 2024-11-11)
    "o": ["absgap_z", "beyond_any", "orel_abs"],                                               # post-open block (needs the official open of the session)
}
LOC_FEATS = {
    "b": ["sp_ret", "usdinr_ret", "dvixus", "brent_ret", "dxy_ret", "us10y_chg"],
    "c": ["nifty_ret", "bank_ret", "br_adv", "peers_ret", "dlnvix"],
    "d": ["ret1", "ret5", "ret20", "close_loc_c", "dist_hi250", "dist_lo250", "streak", "rel_nifty"],
    "e": ["tue", "wed", "thu", "fri", "month_end", "post_hol"],
    "o": ["gap_z", "orel_c", "beyond_signed"],
}
ALL_FEATS = list(dict.fromkeys([f for b in SCALE_FEATS.values() for f in b] + [f for b in LOC_FEATS.values() for f in b]))
FEATURES = {      # name -> (block(s), timestamp rule).  Every rule: the value used for session t is known before the t open (09:00 IST) except the block-o features (09:08 IST, official open).
    "lnvix": ("a", "ln India VIX close of session t-1 (NSE index file; value fixed 15:30 IST t-1)"),
    "dlnvix": ("a,c-loc", "ln(VIX t-1 / VIX t-2)"),
    "vix_rv_spread": ("a", "ln(VIX_{t-1}/100/sqrt(252)) - ln(Nifty-50 realised daily vol, 10 sessions to t-1)"),
    "abs_sp": ("b", "|ln S&P 500| of the last US session dated strictly before the IST date of t (closes 01:30 IST on that date: lag zero); FRED SP500, Yahoo ^GSPC for 13-15 Oct"),
    "lnvixus": ("b", "ln US VIX close, same date rule (closes ~01:45 IST; lag zero)"),
    "dvixus": ("b,b-loc", "ln change of US VIX, same date rule"),
    "abs_usdinr": ("b", "|ln change| of the ECB USD/INR reference rate (14:15 CET fixing, posted 16:00 CET: lag zero), last date strictly before t"),
    "abs_brent": ("b", "|ln change| Brent (FRED DCOILBRENTEU, EIA: publication lag not provably zero -> value shifted ONE more observation back; > 9 days old = missing)"),
    "abs_dxy": ("b", "|ln change| broad dollar index (FRED DTWEXBGS, weekly release: shifted one more observation back; > 9 days old = missing)"),
    "abs_us10y": ("b", "|change| US 10y yield (FRED DGS10, released next day: shifted one more observation back; > 9 days old = missing)"),
    "nifty_lnrange": ("c", "ln ln(H/L) of Nifty 50, session t-1 (NSE index file)"),
    "nifty_abs": ("c", "|Nifty 50 close-to-close log return| of t-1"),
    "bank_lnrange": ("c", "ln ln(H/L) of Nifty Bank, session t-1"),
    "br_tails": ("c", "share of liquid EQ names with |return| >= 5% on t-1 (NSE bhavcopy, ~16:34 IST t-1)"),
    "br_absadv": ("c", "|advancing share - 0.5| on t-1"),
    "peers_lnrange_rel": ("c", "median over peers (CDSL MCX ANGELONE CAMS IEX KFINTECH NUVAMA MOTILALOFS ANANDRATHI listed at t-1, >= 3) of ln ln(H/L)_{t-1} minus the peer's own 60-session mean to t-1"),
    "mkt_turn_z": ("c", "z-score of ln(total EQ turnover) on t-1 over the 60 sessions to t-1"),
    "lnrange_y": ("d", "ln ln(H/L) of BSE on t-1 (bhavcopy ~16:34 IST t-1)"),
    "absgap_y": ("d", "|opening gap| of BSE on t-1 (ln O/P0 of session t-1)"),
    "turn_z60": ("d", "z-score of ln BSE turnover on t-1 over 60 sessions to t-1"),
    "deliv_z60": ("d", "z-score of BSE delivery % on t-1 over 60 sessions to t-1 (delivery file ~18:00 IST t-1; NaN before 2019-2020)"),
    "pk10_rel": ("d", "ln Parkinson vol (10 sessions to t-1) - ln sigma_S6,t"),
    "pk20_rel": ("d", "ln Parkinson vol (20 sessions to t-1) - ln sigma_S6,t"),
    "dist_hi250": ("d,d-loc", "adjusted ln close t-1 - max adjusted ln high over the 250 sessions to t-1 (<= 0)"),
    "dist_lo250": ("d,d-loc", "adjusted ln close t-1 - min adjusted ln low over the 250 sessions to t-1 (>= 0)"),
    "tue": ("e,e-loc", "weekday of t (known in advance); Monday is the reference"), "wed": ("e,e-loc", "weekday"), "thu": ("e,e-loc", "weekday"), "fri": ("e,e-loc", "weekday"),
    "month_end": ("e,e-loc", "t is one of the last two weekdays of its calendar month"),
    "post_hol": ("e,e-loc", "previous session >= 4 calendar days before t (holiday or long weekend)"),
    "lniv": ("s", "ln BSE ATM implied vol from NSE F&O settlement prices of t-1 (src/options_iv.py; data from 2024-11-29)"),
    "iv_skew": ("s", "IV(OTM put side) - IV(OTM call side) at the two strikes around the future, t-1"),
    "iv_rv_spread": ("s", "ln(IV_{t-1}/sqrt(252)) - ln(BSE realised daily vol, 20 sessions to t-1)"),
    "exp_day": ("s", "t is a BSE F&O expiry date (contract expiries read from data/raw/fo_bse + fill; defined from 2024-11-18)"),
    "results_next": ("s", "t is the first session after a results announcement (data/results_dates.csv, announced after market on t-1; defined from 2024-11-13; 7 events)"),
    "cap_lnrange": ("s", "ln ln(H/L) of the Nifty Capital Markets index, t-1 (high/low in the index file from 2024-11-11)"),
    "absgap_z": ("o", "|G_t| / sigma_S6,t, capped at 4; G_t = ln(O_t/P0): official open O_t (NSE pre-open auction, final 09:08 IST); sigma known at the t-1 close"),
    "beyond_any": ("o", "O_t above yesterday's high or below yesterday's low (bonus-adjusted)"),
    "orel_abs": ("o", "|position of O_t in yesterday's range - 0.5|, capped at 2"),
    "sp_ret": ("b-loc", "signed S&P 500 log return, same date rule as abs_sp"), "usdinr_ret": ("b-loc", "signed ln change USD/INR (positive = rupee weaker)"),
    "brent_ret": ("b-loc", "signed ln change Brent (shifted one more observation)"), "dxy_ret": ("b-loc", "signed ln change dollar index (shifted)"), "us10y_chg": ("b-loc", "signed change US 10y (shifted)"),
    "nifty_ret": ("c-loc", "Nifty 50 return of t-1"), "bank_ret": ("c-loc", "Nifty Bank return of t-1"), "br_adv": ("c-loc", "advancing share - 0.5 on t-1"),
    "peers_ret": ("c-loc", "median peer return on t-1 (each clipped to +-15%)"),
    "ret1": ("d-loc", "BSE return of t-1"), "ret5": ("d-loc", "ln(adjusted close t-1 / close t-6)"), "ret20": ("d-loc", "ln(adjusted close t-1 / close t-21)"),
    "close_loc_c": ("d-loc", "(C-L)/(H-L) of BSE on t-1 minus 0.5"), "streak": ("d-loc", "signed run length of up / down closes to t-1, capped at +-5"),
    "rel_nifty": ("d-loc", "BSE return minus Nifty 50 return on t-1"),
    "gap_z": ("o-loc", "G_t / sigma_S6,t capped at +-4 (official open, 09:08 IST)"), "orel_c": ("o-loc", "position of O_t in yesterday's range - 0.5, clipped to +-2"),
    "beyond_signed": ("o-loc", "+1 if O_t above yesterday's high, -1 if below yesterday's low, else 0"),
}

# ----------------------------------------------------------------------------------------------- pre-fixed variants (see the report, Section 0)
VARIANTS = {}
for _b in "abcde":
    VARIANTS[f"P_SC_{_b}"] = dict(phase="pre", scale=[_b], loc=[], tail=False)
VARIANTS.update({
    "P_SC_f": dict(phase="pre", scale=list("abcde"), loc=[], tail=False),
    "P_SC_s": dict(phase="pre", scale=["s"], loc=[], tail=False, short=True),
    "P_SC_fs": dict(phase="pre", scale=list("abcdes"), loc=[], tail=False, short=True),
    "P_TS_f": dict(phase="pre", scale=list("abcde"), loc=[], tail=True),
    "P_LO_f": dict(phase="pre", scale=[], loc=list("bcde"), tail=False),
    "P_SL_f": dict(phase="pre", scale=list("abcde"), loc=list("bcde"), tail=False),
})
for _b in "abcde":
    VARIANTS[f"W_SC_{_b}"] = dict(phase="post", scale=[_b], loc=[], tail=False)
VARIANTS.update({
    "W_SC_o": dict(phase="post", scale=["o"], loc=[], tail=False),
    "W_SC_fo": dict(phase="post", scale=list("abcdeo"), loc=[], tail=False),
    "W_SC_s": dict(phase="post", scale=["s"], loc=[], tail=False, short=True),
    "W_SC_fso": dict(phase="post", scale=list("abcdeso"), loc=[], tail=False, short=True),
    "W_TS_fo": dict(phase="post", scale=list("abcdeo"), loc=[], tail=True),
    "W_LO_fo": dict(phase="post", scale=[], loc=list("bcdeo"), tail=False),
    "W_SL_fo": dict(phase="post", scale=list("abcdeo"), loc=list("bcdeo"), tail=False),
})
DIAG = {"P_PLACEBO": dict(phase="pre", scale=["rnd"], loc=[], tail=False), "W_PLACEBO": dict(phase="post", scale=["rnd"], loc=[], tail=False)}   # random N(0,1) features: diagnostic, not a candidate
# POST HOC sensitivity variants (added after the first results were seen; NOT candidates, not in the Holm family, cannot be adopted): the same models with a FIXED ridge strength instead of CV
POSTHOC = {f"{nm}_fix{lam:g}": dict(VARIANTS[nm], fixlam=lam) for nm in ("P_SC_f", "P_LO_f", "P_SL_f", "W_SC_fo", "W_LO_fo") for lam in (0.3, 3.0)}
BASE = {"pre": "P_S6", "post": "W_I6"}
N_RND = 10


# ----------------------------------------------------------------------------------------------- network step: fill-in files
def refresh_fill(last="2026-10-15", cache=None) -> None:
    """NETWORK (run once; the results are cached in results/hl2_fill_*.csv).  Rows the repo's processed files lack for the sessions after the last processed index row up to `last`:
    index / VIX, F&O implied vol and expiry dates, breadth and peers (from the local UDiFF zips), BSE delivery %, Yahoo S&P 500 and US VIX closes, ECB USD/INR history (Frankfurter).
    Nothing dated after `last` is requested.  `cache` = a directory holding already downloaded idx_DDMMYYYY.csv / fo_YYYYMMDD.zip / sec_DDMMYYYY.csv files."""
    import requests

    import build_dataset as BD
    import options_iv as OIV
    from fetch_nse import CA
    OUT.mkdir(exist_ok=True)
    cache = Path(cache) if cache else None
    d = H1.load_ohlc(); ix0 = load_index(); br0 = load_breadth()
    days = [x for x in d.index if x > ix0.index.max() and x <= pd.Timestamp(last)]
    s = requests.Session(); s.headers["User-Agent"] = UA

    def get(url, verify=CA, **kw):
        for k in range(4):
            try:
                r = s.get(url, timeout=60, verify=verify, headers={"User-Agent": UA if verify is CA else UA_SHORT}, **kw)
                if r.status_code in (200, 404):
                    return r
            except requests.RequestException:
                pass
            time.sleep(2 * (k + 1))
        raise RuntimeError(f"cannot fetch {url}")

    def local(name, url):
        if cache is not None and (cache / name).exists():
            return (cache / name).read_bytes()
        r = get(url)
        return r.content if r.status_code == 200 else b""

    idx_rows, iv_rows, deliv_rows = [], [], []
    for day in days:
        k8, k8b = day.strftime("%d%m%Y"), day.strftime("%Y%m%d")
        b = local(f"idx_{k8}.csv", f"https://nsearchives.nseindia.com/content/indices/ind_close_all_{k8}.csv")
        if b[:5] == b"Index":
            p = Path(f"/tmp/hl2_idx_{k8}.csv"); p.write_bytes(b); ix = BD.read_idx(p); ix["date"] = day; idx_rows.append(ix)
        b = local(f"fo_{k8b}.zip", f"https://nsearchives.nseindia.com/content/fo/BhavCopy_NSE_FO_0_0_0_{k8b}_F_0000.csv.zip")
        if b[:2] == b"PK":
            z = zipfile.ZipFile(io.BytesIO(b)); f = pd.read_csv(z.open(z.namelist()[0])); f = f[f["TckrSymb"] == "BSE"]
            row = OIV.day_iv(f, day)
            if row:
                iv_rows.append(row)
            f.assign(date=day).to_csv(OUT / f"hl2_fill_fo_{k8b}.csv", index=False)       # BSE contract rows (expiry dates)
        b = local(f"sec_{k8}.csv", f"https://nsearchives.nseindia.com/products/content/sec_bhavdata_full_{k8}.csv")
        if b[:6] == b"SYMBOL":
            p = Path(f"/tmp/hl2_sec_{k8}.csv"); p.write_bytes(b); sec = BD.read_sec(p); bb = sec[(sec.symbol == "BSE") & (sec.series == "EQ")]
            if len(bb):
                deliv_rows.append({"date": day, "deliv_pct": float(bb["deliv_pct"].iloc[0])})
    if idx_rows:
        iw = pd.concat(idx_rows, ignore_index=True).pivot_table(index="date", columns="name", values=["open", "high", "low", "close", "volume"])
        iw.columns = [f"{n}_{f}" for f, n in iw.columns]; iw.to_csv(FILL["index"])
    if iv_rows:
        pd.DataFrame(iv_rows).set_index("date").to_csv(FILL["iv"])
    pd.DataFrame(deliv_rows).to_csv(FILL["delivery"], index=False)
    # expiry dates: every contract expiry seen in the raw F&O files of BSE (+ the filled days)
    exp = set()
    for f in sorted(RAW.glob("fo_bse/*.csv")):
        x = pd.read_csv(f, usecols=["XpryDt"]) if f.stat().st_size > 400 else pd.DataFrame({"XpryDt": []})
        exp |= set(pd.to_datetime(x["XpryDt"]).unique())
    for f in OUT.glob("hl2_fill_fo_*.csv"):
        exp |= set(pd.to_datetime(pd.read_csv(f)["XpryDt"]).unique())
    pd.DataFrame({"expiry": sorted(pd.Timestamp(e) for e in exp)}).to_csv(FILL["expiries"], index=False)
    # breadth + peers for the sessions after the last processed row, from the local UDiFF bhavcopies (same code as build_dataset.main)
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
    pd.DataFrame(br_rows).set_index("date").to_csv(FILL["breadth"])
    pd.concat(pe_rows, ignore_index=True).to_csv(FILL["peers"], index=False)
    # Yahoo S&P 500 and US VIX daily closes (US session dates)
    us = {}
    for nm, sym in (("sp", "%5EGSPC"), ("vix", "%5EVIX")):
        j = get(f"https://query2.finance.yahoo.com/v8/finance/chart/{sym}?interval=1d&range=3mo", verify=PROXY_CA).json()["chart"]["result"][0]
        c = pd.Series(j["indicators"]["quote"][0]["close"], index=pd.to_datetime(j["timestamp"], unit="s", utc=True).tz_convert("America/New_York").tz_localize(None).normalize()).dropna()
        us[nm] = c[~c.index.duplicated(keep="last")]
    uf = pd.DataFrame(us); uf = uf[uf.index <= pd.Timestamp(last)]; uf.index.name = "date"; uf.to_csv(FILL["us"])
    # USD/INR, ECB reference rates via Frankfurter (chunks < 90 days so that the answer is daily)
    rows, a = {}, pd.Timestamp("2017-01-01")
    while a <= pd.Timestamp(last):
        b_ = min(a + pd.Timedelta(days=80), pd.Timestamp(last))
        r = get(f"https://api.frankfurter.app/{a.date()}..{b_.date()}?from=USD&to=INR", verify=PROXY_CA, allow_redirects=True)
        rows.update({k: v["INR"] for k, v in r.json()["rates"].items()}); a = b_ + pd.Timedelta(days=1)
    pd.DataFrame({"date": list(rows), "usdinr": list(rows.values())}).sort_values("date").to_csv(USDINR_FILE, index=False)
    meta = {"retrieved_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "last_session_requested": last,
            "rows": {"index": len(idx_rows), "iv": len(iv_rows), "breadth": len(br_rows), "delivery": len(deliv_rows), "us_last": str(uf.index.max().date()), "usdinr": len(rows)},
            "sources": {"index": "nsearchives ind_close_all", "iv": "NSE F&O UDiFF bhavcopy via src/options_iv.day_iv", "delivery": "nsearchives sec_bhavdata_full", "us": "Yahoo chart ^GSPC ^VIX",
                        "usdinr": "api.frankfurter.app (ECB reference rates)", "breadth_peers": "data/raw/udiff local zips"}}
    (OUT / "hl2_fill_meta.json").write_text(json.dumps(meta, indent=1)); print(json.dumps(meta, indent=1))



# ----------------------------------------------------------------------------------------------- input tables (with the fill rows) and the feature panel
def _fred(name) -> pd.Series:
    x = pd.read_csv(RAW / "macro" / f"{name}.csv", parse_dates=["observation_date"]).set_index("observation_date")[name]
    return pd.to_numeric(x, errors="coerce").dropna()


def load_tables(fill=True) -> dict:
    """Every input table the features read, as plain objects (so that the leakage test can replace parts of them).  The 13-15 Oct 2026 rows missing from the processed files come from results/hl2_fill_*.csv."""
    bars = H1.load_ohlc()
    ix, br = load_index(), load_breadth()
    pe = pd.read_csv(PROC / "peers_daily.csv", parse_dates=["date"])
    pe = pe[pe["symbol"].isin(PEERS_USED)][["symbol", "date", "prev", "high", "low", "close"]].drop_duplicates(["symbol", "date"])
    iv = pd.read_csv(PROC / "bse_iv_daily.csv", parse_dates=["date"]).set_index("date")
    us = {"sp": _fred("SP500"), "vixus": _fred("VIXCLS"), "brent": _fred("DCOILBRENTEU"), "dxy": _fred("DTWEXBGS"), "us10y": _fred("DGS10")}
    u = pd.read_csv(USDINR_FILE, parse_dates=["date"]).set_index("date")["usdinr"] if USDINR_FILE.exists() else pd.Series(dtype=float)
    us["usdinr"] = u.dropna()
    res = pd.read_csv("data/results_dates.csv", parse_dates=["first_tradable_session"])
    expiries = pd.DatetimeIndex(pd.read_csv(FILL["expiries"], parse_dates=["expiry"])["expiry"]) if FILL["expiries"].exists() else pd.DatetimeIndex([])
    if fill:
        f = FILL["index"]
        if f.exists():
            x = pd.read_csv(f, parse_dates=["date"]).set_index("date"); ix = pd.concat([ix, x[~x.index.isin(ix.index)].reindex(columns=ix.columns)]).sort_index()
        f = FILL["breadth"]
        if f.exists():
            x = pd.read_csv(f, parse_dates=["date"]).set_index("date"); br = pd.concat([br, x[~x.index.isin(br.index)].reindex(columns=br.columns)]).sort_index()
        f = FILL["peers"]
        if f.exists():
            x = pd.read_csv(f, parse_dates=["date"])
            x = x[x["symbol"].isin(PEERS_USED)][["symbol", "date", "prev", "high", "low", "close"]].drop_duplicates(["symbol", "date"])
            pe = pd.concat([pe, x.merge(pe[["symbol", "date"]], on=["symbol", "date"], how="left", indicator=True).query("_merge=='left_only'").drop(columns="_merge")], ignore_index=True)
        f = FILL["iv"]
        if f.exists():
            x = pd.read_csv(f, parse_dates=["date", "expiry"]).set_index("date"); iv = pd.concat([iv, x[~x.index.isin(iv.index)].reindex(columns=iv.columns)]).sort_index()
        f = FILL["delivery"]
        if f.exists():
            x = pd.read_csv(f, parse_dates=["date"]).set_index("date")["deliv_pct"]
            for dte, v in x.items():
                if dte in bars.index and not np.isfinite(bars.loc[dte, "deliv_pct"]):
                    bars.loc[dte, "deliv_pct"] = v
        f = FILL["us"]
        if f.exists():
            x = pd.read_csv(f, parse_dates=["date"]).set_index("date")
            for k, c in (("sp", "sp"), ("vixus", "vix")):
                y = x[c].dropna(); us[k] = pd.concat([us[k], y[~y.index.isin(us[k].index) & (y.index > us[k].index.max())]]).sort_index()
    return {"bars": bars, "idx": ix, "br": br, "peers": pe, "iv": iv, "us": us, "expiries": pd.DatetimeIndex(sorted(set(expiries))), "results": pd.DatetimeIndex(res["first_tradable_session"])}


def extend_bars(bars: pd.DataFrame, date, open_price=None) -> pd.DataFrame:
    """Append the not yet played session `date` (only the previous close = P0 and, if given, the official open O are known)."""
    date = pd.Timestamp(date)
    row = pd.DataFrame({c: [np.nan] for c in bars.columns}, index=pd.DatetimeIndex([date], name=bars.index.name))
    row["prev"] = float(bars["close"].iloc[-1]); row["open"] = np.nan if open_price is None else float(open_price)
    return pd.concat([bars, row.astype(bars.dtypes.to_dict(), errors="ignore")])


def _lag(x, k=1):
    x = np.asarray(x, float)
    return np.r_[np.full(k, np.nan), x[:-k]]


def _roll(x, w, f="mean", mp=None):
    return getattr(pd.Series(x).rolling(w, min_periods=mp or w), f)().values


def _us_feat(s: pd.Series, S: pd.DatetimeIndex, lag_extra: int, kind: str) -> np.ndarray:
    """Feature of a US/FRED series for IST sessions S: the last observation dated strictly before the session date (minus `lag_extra` observations if the publication lag is not provably zero)."""
    v, di = s.values.astype(float), s.index.values
    k = np.searchsorted(di, S.values, side="left") - 1 - lag_extra
    ok = k >= 1
    kk = np.where(ok, k, 1)
    age = (S.values - di[kk]) / np.timedelta64(1, "D")
    ok &= age <= (STALE_LAG if lag_extra else STALE)
    cur, prv = v[kk], v[kk - 1]
    with np.errstate(all="ignore"):
        out = {"lvl": np.log(cur), "ret": np.log(cur / prv), "abs": np.abs(np.log(cur / prv)), "chg": cur - prv, "abschg": np.abs(cur - prv)}[kind]
    return np.where(ok, out, np.nan)


def build_panel(tb: dict, d: pd.DataFrame, sigR: np.ndarray) -> pd.DataFrame:
    """Feature panel for every row (session) of `d`.  Row t uses only data dated before the t open, except the block-o features, which also use the official open O_t of the session t itself
    (and sigma_S6,t, known at the t-1 close).  `d` may end with a not-yet-played session (NaN bars)."""
    S, m = d.index, len(d)
    t = targets(d)
    R, G, rho, Hp, Lp = (t[c].values for c in ("R", "G", "rho", "Hp", "Lp"))
    F = pd.DataFrame(index=S, dtype=float)
    pdates = pd.DatetimeIndex(np.r_[np.datetime64("NaT"), S.values[:-1]])
    at_prev = lambda s: s.reindex(pdates).values.astype(float)           # noqa: E731   value of a table series dated exactly the previous BSE session
    with np.errstate(all="ignore"):
        # --- BSE own (all dated <= t-1)
        c = np.nancumsum(np.nan_to_num(R, nan=0.0)); c[np.isnan(R)] = np.nan
        c = pd.Series(c).ffill().values
        hadj, ladj = _lag(c) + Hp, _lag(c) + Lp                              # adjusted ln high / low of session s (bonus-adjusted scale)
        F["lnrange_y"] = _lag(np.log(np.clip(rho, 1e-4, None)))
        F["absgap_y"] = _lag(np.abs(G))
        lt = np.log(d["turnover_cr"].values.astype(float))
        F["turn_z60"] = _lag((lt - _roll(lt, 60, "mean", 40)) / _roll(lt, 60, "std", 40))
        dv = d["deliv_pct"].values.astype(float)
        F["deliv_z60"] = _lag((dv - _roll(dv, 60, "mean", 30)) / _roll(dv, 60, "std", 30))
        pk = lambda w: np.sqrt(_roll(rho ** 2, w) / (4 * np.log(2)))         # noqa: E731   Parkinson daily vol, w sessions
        F["pk10_rel"] = _lag(np.log(pk(10))) - np.log(sigR)
        F["pk20_rel"] = _lag(np.log(pk(20))) - np.log(sigR)
        F["dist_hi250"] = _lag(c) - _lag(_roll(hadj, 250, "max", 120))
        F["dist_lo250"] = _lag(c) - _lag(_roll(ladj, 250, "min", 120))
        F["ret1"], F["ret5"], F["ret20"] = _lag(R), _lag(c) - _lag(c, 6), _lag(c) - _lag(c, 21)
        F["close_loc_c"] = _lag((np.log(d["close"].values) - np.log(d["low"].values)) / np.log(d["high"].values / d["low"].values)) - 0.5
        st = np.zeros(m); run = 0
        for i in range(m):
            r = R[i]
            run = 0 if not np.isfinite(r) else (max(run, 0) + 1 if r > 0 else (min(run, 0) - 1 if r < 0 else 0))
            st[i] = run
        F["streak"] = np.clip(_lag(st), -5, 5)
        # --- Indian market (index file, breadth, peers): tables dated exactly the previous BSE session
        ix = tb["idx"]
        nr = np.log(ix["nifty50_close"]).diff()
        lvix = np.log(ix["vix_close"])
        F["lnvix"], F["dlnvix"] = at_prev(lvix), at_prev(lvix.diff())
        F["vix_rv_spread"] = at_prev(np.log(ix["vix_close"] / 100 / np.sqrt(252)) - np.log(np.sqrt((nr ** 2).rolling(10, min_periods=10).mean())))
        rg = lambda h, l: np.log(np.log(ix[h] / ix[l])).replace([np.inf, -np.inf], np.nan)          # noqa: E731
        F["nifty_lnrange"], F["bank_lnrange"] = at_prev(rg("nifty50_high", "nifty50_low")), at_prev(rg("bank_high", "bank_low"))
        F["cap_lnrange"] = at_prev(rg("capmkts_high", "capmkts_low")) if "capmkts_high" in ix else np.nan
        F["nifty_abs"], F["nifty_ret"] = at_prev(nr.abs()), at_prev(nr)
        F["bank_ret"] = at_prev(np.log(ix["bank_close"]).diff())
        F["rel_nifty"] = _lag(R) - F["nifty_ret"].values
        br = tb["br"]
        F["br_tails"] = at_prev((br["n_ge_5pct_up"] + br["n_ge_5pct_dn"]) / br["n_liquid"])
        F["br_absadv"], F["br_adv"] = at_prev((br["adv_share"] - 0.5).abs()), at_prev(br["adv_share"] - 0.5)
        lb = np.log(br["turnover_cr_eq"])
        F["mkt_turn_z"] = at_prev((lb - lb.rolling(60, min_periods=40).mean()) / lb.rolling(60, min_periods=40).std())
        pe = tb["peers"]
        LR = pe.assign(v=np.log(np.log(pe["high"] / pe["low"]))).pivot(index="date", columns="symbol", values="v").replace([np.inf, -np.inf], np.nan).sort_index()
        RT = pe.assign(v=np.log(pe["close"] / pe["prev"]).clip(-0.15, 0.15)).pivot(index="date", columns="symbol", values="v").sort_index()
        rel = LR - LR.rolling(60, min_periods=30).mean()
        F["peers_lnrange_rel"] = at_prev(rel.median(axis=1).where(rel.notna().sum(axis=1) >= 3))
        F["peers_ret"] = at_prev(RT.median(axis=1).where(RT.notna().sum(axis=1) >= 3))
        # --- BSE option-implied vol (short sample)
        iv = tb["iv"]
        F["lniv"], F["iv_skew"] = at_prev(np.log(iv["iv_atm"])), at_prev(iv["iv_lo_otm"] - iv["iv_hi_otm"])
        rv20 = np.sqrt(_roll(R ** 2, 20))
        F["iv_rv_spread"] = at_prev(np.log(iv["iv_atm"] / np.sqrt(252))) - _lag(np.log(rv20))
        # --- US / macro overnight: last observation dated strictly before the IST session date
        us = tb["us"]
        F["sp_ret"], F["abs_sp"] = _us_feat(us["sp"], S, 0, "ret"), _us_feat(us["sp"], S, 0, "abs")
        F["lnvixus"], F["dvixus"] = _us_feat(us["vixus"], S, 0, "lvl"), _us_feat(us["vixus"], S, 0, "ret")
        F["usdinr_ret"], F["abs_usdinr"] = _us_feat(us["usdinr"], S, 0, "ret"), _us_feat(us["usdinr"], S, 0, "abs")
        F["brent_ret"], F["abs_brent"] = _us_feat(us["brent"], S, 1, "ret"), _us_feat(us["brent"], S, 1, "abs")
        F["dxy_ret"], F["abs_dxy"] = _us_feat(us["dxy"], S, 1, "ret"), _us_feat(us["dxy"], S, 1, "abs")
        F["us10y_chg"], F["abs_us10y"] = _us_feat(us["us10y"], S, 1, "chg"), _us_feat(us["us10y"], S, 1, "abschg")
        # --- calendar
        dow = S.dayofweek.values
        for k, nm in enumerate(["tue", "wed", "thu", "fri"], start=1):
            F[nm] = (dow == k).astype(float)
        nxt = (S + pd.offsets.MonthBegin(1)).values.astype("datetime64[D]")
        F["month_end"] = (np.busday_count((S.values.astype("datetime64[D]") + 1), nxt) <= 1).astype(float)
        F["post_hol"] = np.r_[0.0, (np.diff(S.values).astype("timedelta64[D]").astype(int) >= 4).astype(float)]
        F["exp_day"] = np.where(S >= EXP_START, S.isin(tb["expiries"]).astype(float), np.nan)
        F["results_next"] = np.where(S >= RES_START, S.isin(tb["results"]).astype(float), np.nan)
        # --- block o (post-open): the official open of the session itself
        Oadj = _lag(c) + G
        hy, ly = _lag(hadj), _lag(ladj)
        gz = np.clip(G / sigR, -4, 4)
        F["gap_z"], F["absgap_z"] = gz, np.abs(gz)
        bs = np.where(Oadj > hy, 1.0, np.where(Oadj < ly, -1.0, 0.0)); bs[~np.isfinite(Oadj) | ~np.isfinite(hy)] = np.nan
        F["beyond_signed"], F["beyond_any"] = bs, np.abs(bs)
        oc = np.clip((Oadj - ly) / (hy - ly) - 0.5, -2, 2)
        F["orel_c"], F["orel_abs"] = oc, np.abs(oc)
    rng = np.random.default_rng(20261016).standard_normal((6000, N_RND))
    for j in range(N_RND):
        F[f"rnd{j}"] = rng[:m, j]
    return F.replace([np.inf, -np.inf], np.nan)


def sigma_paths(R, v, I, gk, live: bool) -> tuple[np.ndarray, np.ndarray]:
    """Baseline S6 scale paths (walk-forward, refit every 20 sessions); with live=True one extra element = the scale of the unseen next session (parameters fitted on all known sessions)."""
    sR, sI = H1.wf_sigmas(R, v, ("S6",))["S6"], H1.wf_sigmas(I, gk, ("S6",))["S6"]
    if live:
        sR, sI = np.r_[sR, H1.s6_next(R, v)], np.r_[sI, H1.s6_next(I, gk)]
    return sR, sI


def make_context(tb: dict, date=None, open_price=None) -> dict:
    """Everything the engine needs.  date=None: all sessions of the bars table (evaluation).  date given: sessions before `date` plus the unseen session `date` (live forecast)."""
    bars = tb["bars"]
    live = date is not None
    if live:
        bars = bars[bars.index < pd.Timestamp(date)]
    n = len(bars)
    t = targets(bars)
    sR, sI = sigma_paths(t["R"].values, t["v"].values, t["I"].values, t["gk"].values, live)
    d = extend_bars(bars, date, open_price) if live else bars
    td = targets(d)
    F = build_panel(tb, d, sR)
    cols = list(dict.fromkeys(ALL_FEATS + [f"rnd{j}" for j in range(N_RND)]))
    return dict(d=d, n=n, m=len(d), sig={"pre": sR, "post": sI}, V={"pre": td[["Hp", "Lp"]].values, "post": td[["HO", "LO"]].values}, F=F, FX=F[cols].values.astype(float), cols=cols, col_ix={c: i for i, c in enumerate(cols)},
                dates=d.index, live=live, tb=tb)


# ----------------------------------------------------------------------------------------------- regression pieces (numpy only)
class Prep:
    """Winsorise (1st / 99th percentile of the training rows; not for 0/1 columns), standardise, impute missing with 0 (= the training mean).  Columns with < min_rows finite training values or no variance are dropped."""

    def __init__(self, X, min_rows):
        n, p = X.shape
        fin = np.isfinite(X)
        self.keep = fin.sum(0) >= min_rows
        self.lo, self.hi, self.mu, self.sd = np.full(p, -np.inf), np.full(p, np.inf), np.zeros(p), np.ones(p)
        for j in np.where(self.keep)[0]:
            x = X[fin[:, j], j]
            if len(np.unique(x)) > 3:
                self.lo[j], self.hi[j] = np.quantile(x, WINS)
            xw = np.clip(x, self.lo[j], self.hi[j])
            self.mu[j], self.sd[j] = xw.mean(), xw.std()
            if not self.sd[j] > 1e-10:
                self.keep[j] = False

    def tf(self, X):
        k = np.where(self.keep)[0]
        with np.errstate(invalid="ignore"):
            Z = (np.clip(X[:, k], self.lo[k], self.hi[k]) - self.mu[k]) / self.sd[k]
        return np.where(np.isfinite(Z), Z, 0.0)


def fit_poisson(Z, r, lam, iters=40):
    """min_{a,g} mean(exp(a+Zg) - r (a+Zg)) + lam/2 |g|^2   (log-link pseudo-ML for E[r|Z] = exp(a+Zg); r >= 0).  lam = inf: g = 0, a = ln mean r.  Returns (a, g)."""
    n, p = Z.shape
    a0 = float(np.log(max(r.mean(), 1e-12)))
    if not np.isfinite(lam) or p == 0:
        return a0, np.zeros(p)
    a, g = a0, np.zeros(p)
    obj = lambda a_, g_: np.mean(np.exp(np.clip(a_ + Z @ g_, -8, 8)) - r * np.clip(a_ + Z @ g_, -8, 8)) + 0.5 * lam * g_ @ g_      # noqa: E731
    cur = obj(a, g)
    for _ in range(iters):
        mu = np.exp(np.clip(a + Z @ g, -8, 8))
        grad = np.r_[np.mean(mu - r), Z.T @ (mu - r) / n + lam * g]
        Hgg = (Z * mu[:, None]).T @ Z / n + lam * np.eye(p)
        Hag = Z.T @ mu / n
        H = np.block([[np.array([[mu.mean()]]), Hag[None, :]], [Hag[:, None], Hgg]])
        step = np.linalg.solve(H, grad)
        t = 1.0
        while t > 1e-4:
            a2, g2 = a - t * step[0], g - t * step[1:]
            new = obj(a2, g2)
            if new <= cur + 1e-13:
                break
            t *= 0.5
        else:
            break
        done = cur - new < 1e-11
        a, g, cur = a2, g2, new
        if done:
            break
    return a, g


def fit_ols(Z, y, lam):
    """Ridge OLS with unpenalised intercept: min mean((y-a-Zb)^2) + lam |b|^2.  lam = inf: b = 0.  Returns (a, b) for the uncentred Z."""
    n, p = Z.shape
    ym = float(y.mean())
    if not np.isfinite(lam) or p == 0:
        return ym, np.zeros(p)
    zm = Z.mean(0)
    Zc = Z - zm
    b = np.linalg.solve(Zc.T @ Zc / n + lam * np.eye(p), Zc.T @ (y - ym) / n)
    return ym - zm @ b, b


def cv_lambda(X, y, kind) -> float:
    """Ridge strength by forward-chaining CV on the training rows (time-ordered): train on rows[:cut_k], validate on rows[cut_k:cut_{k+1}], pooled loss; ties go to the stronger shrinkage; np.inf = no features."""
    m = len(y)
    cuts = [int(round(f * m)) for f in CV_CUTS]
    loss, used = np.zeros(len(LAMS)), False
    for k in range(len(cuts) - 1):
        a, b = cuts[k], cuts[k + 1]
        if a < 60 or b <= a:
            continue
        pr = Prep(X[:a], MIN_ROWS_CV)
        Ztr, Zva = pr.tf(X[:a]), pr.tf(X[a:b])
        if kind == "ols":
            lo_, hi_ = np.quantile(y[:a], WINS)
            ytr, yva = np.clip(y[:a], lo_, hi_), np.clip(y[a:b], lo_, hi_)
        for i, lam in enumerate(LAMS):
            if kind == "pois":
                a0, g = fit_poisson(Ztr, y[:a], lam)
                eta = np.clip(a0 + Zva @ g, -8, 8)
                loss[i] += float(np.sum(np.exp(eta) - y[a:b] * eta))
            else:
                a0, g = fit_ols(Ztr, ytr, lam)
                loss[i] += float(np.sum((yva - a0 - Zva @ g) ** 2))
        used = True
    if not used:
        return np.inf
    best = min(range(len(LAMS)), key=lambda i: (round(loss[i], 9), -i))
    return LAMS[best]


# ----------------------------------------------------------------------------------------------- the walk-forward engine
def _names(blocks, table):
    out = []
    for b in blocks:
        out += [f"rnd{j}" for j in range(N_RND)] if b == "rnd" else table[b]
    return list(dict.fromkeys(out))


def _clipmult(z):
    return np.exp(np.clip(z, -1.0, 1.0))


def block_fit(ctx, spec, name, b0, k, hi, lam_cache, log=None):
    """Fit the scale and location models of one refit block on the rows strictly before b0 and return the arrays needed to build the draws for sessions b0..hi-1.
    Returns S [hi,2] (scale per side), SH [hi,2] (location shift per side).  lam_cache: dict (name, side, kind, k0) -> lambda; k0 = the last CV block (every LAM_EVERY-th refit)."""
    ph = spec["phase"]
    V, sig, FX, cix = ctx["V"][ph], ctx["sig"][ph], ctx["FX"], ctx["col_ix"]
    S = np.repeat(sig[:hi, None], 2, axis=1).astype(float)
    SH = np.zeros((hi, 2))
    live = b0 == ctx["n"] and ctx["live"]
    rows_all = np.where(np.isfinite(sig[:b0]) & np.isfinite(V[:b0]).all(axis=1))[0]
    k0 = k if (live or k is None) else (k // LAM_EVERY) * LAM_EVERY
    b0_k0 = b0 if live else FIT_START + k0 * BLOCK
    rows_cv = rows_all[rows_all < b0_k0]
    yH = np.maximum(V[:, 0], 0) if ph == "pre" else V[:, 0]
    yL = np.maximum(-V[:, 1], 0) if ph == "pre" else -V[:, 1]
    sc = _names(spec["scale"], SCALE_FEATS)
    if sc and len(rows_all) >= MIN_ROWS:
        Xs = FX[:, [cix[c] for c in sc]]
        sides = ["H", "L"] if spec["tail"] else ["sym"]
        for sd in sides:
            y = {"H": yH, "L": yL, "sym": yH + yL}[sd]
            key = (name, sd, "pois", k0)
            if key not in lam_cache:
                lam_cache[key] = spec["fixlam"] if "fixlam" in spec else (cv_lambda(Xs[rows_cv], y[rows_cv] / sig[rows_cv], "pois") if len(rows_cv) >= MIN_ROWS else np.inf)
            lam = lam_cache[key]
            pr = Prep(Xs[rows_all], MIN_ROWS)
            a0, g = fit_poisson(pr.tf(Xs[rows_all]), y[rows_all] / sig[rows_all], lam)
            mult = _clipmult(pr.tf(Xs[:hi]) @ g) if len(g) else np.ones(hi)
            if sd == "sym":
                S[:, 0] *= mult; S[:, 1] *= mult
            else:
                S[:, 0 if sd == "H" else 1] *= mult
            if log is not None and len(g):
                kept = [sc[j] for j in np.where(pr.keep)[0]]
                log += [dict(variant=name, kind="scale", side=sd, block_start=int(b0), lam=lam, feature=f, coef=float(c)) for f, c in zip(kept, g)] + [dict(variant=name, kind="scale", side=sd, block_start=int(b0), lam=lam, feature="(n_features_used)", coef=float(len(g)))]
    lo = _names(spec["loc"], LOC_FEATS)
    if lo and len(rows_all) >= MIN_ROWS:
        Xl = FX[:, [cix[c] for c in lo]]
        U = V[:hi] / S
        for j, sd in enumerate(["H", "L"]):
            key = (name, sd, "ols", k0)
            if key not in lam_cache:
                lam_cache[key] = spec["fixlam"] if "fixlam" in spec else (cv_lambda(Xl[rows_cv], U[rows_cv, j], "ols") if len(rows_cv) >= MIN_ROWS else np.inf)
            lam = lam_cache[key]
            pr = Prep(Xl[rows_all], MIN_ROWS)
            ylo, yhi = np.quantile(U[rows_all, j], WINS)
            a0, b = fit_ols(pr.tf(Xl[rows_all]), np.clip(U[rows_all, j], ylo, yhi), lam)
            if len(b):
                SH[:, j] = pr.tf(Xl[:hi]) @ b
            if log is not None and len(b):
                kept = [lo[q] for q in np.where(pr.keep)[0]]
                log += [dict(variant=name, kind="location", side=sd, block_start=int(b0), lam=lam, feature=f, coef=float(c)) for f, c in zip(kept, b)] + [dict(variant=name, kind="location", side=sd, block_start=int(b0), lam=lam, feature="(n_features_used)", coef=float(len(b)))]
    return S, SH


def draws_at(ctx, spec, S, SH, t):
    """Filtered-historical-simulation draws for session t: sigma'_t x (standardised residuals of the trailing 500 sessions, minus their location shift, plus the shift at t)."""
    ph = spec["phase"]
    V = ctx["V"][ph]
    lo = max(0, t - W)
    E = V[lo:t] / S[lo:t] - SH[lo:t]
    E = E[np.isfinite(E).all(axis=1)]
    dr = S[t] * (E + SH[t])
    if ph == "post":
        dr = np.c_[np.maximum(dr[:, 0], 0.0), np.minimum(dr[:, 1], 0.0)]
    return dr


def qnom(dr):
    """[2, 9] quantiles on GRID and [2, 2] nominal (model-implied) central coverage of the 50% and 90% bands, which differs from 0.5 / 0.9 when the draws have an atom at zero (post-open)."""
    q = np.quantile(dr, GRID, axis=0).T
    i = lambda x: list(GRID).index(x)               # noqa: E731
    nom = np.array([[np.mean(dr[:, j] <= q[j, i(0.75)]) - np.mean(dr[:, j] < q[j, i(0.25)]), np.mean(dr[:, j] <= q[j, i(0.95)]) - np.mean(dr[:, j] < q[j, i(0.05)])] for j in range(2)])
    return q, nom


def run_variant(ctx, spec, name, eval_rows, log=None, lam_cache=None):
    """Walk-forward quantile forecasts of one variant for the given session rows.  The baseline is the same engine with no features.  Returns Q [n,2,9], NOM [n,2,2]."""
    lam_cache = {} if lam_cache is None else lam_cache
    eval_rows = np.asarray(eval_rows)
    Q, NOM = np.full((len(eval_rows), 2, len(GRID)), np.nan), np.full((len(eval_rows), 2, 2), np.nan)
    sig = ctx["sig"][spec["phase"]]
    live = ctx["live"] and len(eval_rows) == 1 and eval_rows[0] == ctx["n"]
    blocks = {}
    for i, t in enumerate(eval_rows):
        b0 = ctx["n"] if live else FIT_START + ((t - FIT_START) // BLOCK) * BLOCK
        blocks.setdefault(b0, []).append((i, t))
    has_feat = bool(spec["scale"] or spec["loc"])
    for b0, items in sorted(blocks.items()):
        hi = max(t for _, t in items) + 1
        if has_feat and b0 >= FIT_START:
            k = None if live else (b0 - FIT_START) // BLOCK
            S, SH = block_fit(ctx, spec, name, b0, k, hi, lam_cache, log)
        else:
            S, SH = np.repeat(sig[:hi, None], 2, axis=1).astype(float), np.zeros((hi, 2))
        for i, t in items:
            Q[i], NOM[i] = qnom(draws_at(ctx, spec, S, SH, t))
    return Q, NOM


# ----------------------------------------------------------------------------------------------- baseline reproduction
def _eval_frame(ctx):
    d = ctx["d"]
    idx = np.arange(START, ctx["n"])
    return dict(idx=idx, dts=d.index[idx], Yp=ctx["V"]["pre"][idx], Yq=ctx["V"]["post"][idx], P0=d["prev"].values[idx], O=d["open"].values[idx], hl=d[["high", "low"]].values[idx])


def baseline_Q(ctx, idx):
    """The baseline in this engine (a variant with no features): P_S6 and W_I6."""
    return {ph: run_variant(ctx, dict(phase=ph, scale=[], loc=[], tail=False), BASE[ph], idx) for ph in ("pre", "post")}


def baseline_check(ctx=None):
    """Reproduce the baseline before anything else: (1) this engine without features equals hl_model.build() quantiles to 1e-12; (2) the Final-window pinball and typical misses of hl_eval_preopen/postopen.csv."""
    ctx = make_context(load_tables()) if ctx is None else ctx
    E = _eval_frame(ctx)
    t0 = time.time()
    Qp, Qo, _ = H1.build(ctx["d"])
    mine = baseline_Q(ctx, E["idx"])
    rows = [dict(check="max |this engine (no features) - hl_model.build|, pre-open P_S6, quantile (log)", value=float(np.nanmax(np.abs(mine["pre"][0] - Qp["P_S6"]))), n=len(E["idx"])),
            dict(check="max |this engine (no features) - hl_model.build|, post-open W_I6, quantile (log)", value=float(np.nanmax(np.abs(mine["post"][0] - Qo["W_I6"]))), n=len(E["idx"]))]
    stored = {"pre": pd.read_csv(OUT / "hl_eval_preopen.csv"), "post": pd.read_csv(OUT / "hl_eval_postopen.csv")}
    for ph, nm, tg in (("pre", "P_S6", ["H", "L"]), ("post", "W_I6", ["HO", "LO"])):
        Y, ref = (E["Yp"], E["P0"]) if ph == "pre" else (E["Yq"], E["O"])
        sr = pd.DataFrame(H1.score_rows(nm, mine[ph][0], Y, ref, E["hl"], E["dts"], tg))
        for _, r in sr[sr.window.isin(["final", "cas"])].iterrows():
            s = stored[ph][(stored[ph].variant == nm) & (stored[ph].target == r.target) & (stored[ph].window == r.window)].iloc[0]
            for col in ("pinball_x1e4", "mae_med_rs_at_now", "cov90"):
                rows.append(dict(check=f"{nm} {r.target} {r.window} {col}: this run vs results/hl_eval_*open.csv (stored)", value=float(r[col]), stored=float(s[col]), diff=float(r[col] - s[col]), n=int(r.n)))
    out = pd.DataFrame(rows); out.to_csv(OUT / "hl2_baseline_repro.csv", index=False)
    print(out.round(5).to_string(index=False)); print(f"({time.time() - t0:.0f}s)")
    return out


# ----------------------------------------------------------------------------------------------- evaluation
_CTX = None


def _run_one(args):
    name, spec = args
    log = []
    t0 = time.time()
    Q, NOM = run_variant(_CTX, spec, name, _CTX["_idx"], log=log)
    return name, Q, NOM, log, time.time() - t0


def atom_cov_rows(name, Q, NOM, Y, dts, tg):
    """Coverage of the 50% / 90% central bands against the model-implied nominal (from the model's own draws: an atom at zero makes the post-open high band cover more than 90%), with a z-test on
    sum(hits) - sum(nominal) (Poisson-binomial variance).  For continuous targets the nominal is 0.5 / 0.9 up to the 1/500 grid of the draws."""
    rows = []
    i = lambda x: list(GRID).index(x)                # noqa: E731
    for j, tn in enumerate(tg):
        for w, (a, b) in H1.WIN.items():
            m = (dts >= a) & (dts <= b)
            if m.sum() < 5:
                continue
            r = dict(variant=name, target=tn, window=w, n=int(m.sum()))
            for lab, (lo, hi), k in (("50", (0.25, 0.75), 0), ("90", (0.05, 0.95), 1)):
                hit = ((Y[m, j] >= Q[m, j, i(lo)]) & (Y[m, j] <= Q[m, j, i(hi)])).astype(float)
                p = NOM[m, j, k]
                z = (hit.sum() - p.sum()) / np.sqrt(np.sum(p * (1 - p)))
                r.update({f"cov{lab}": hit.mean(), f"nominal{lab}": p.mean(), f"dev{lab}": hit.mean() - p.mean(), f"atom_p{lab}": float(2 * (1 - stats.norm.cdf(abs(z))))})
            rows.append(r)
    return rows


def evaluate(n_jobs=4, dump=None):
    """Full pre-fixed evaluation -> results/hl2_*.csv."""
    global _CTX
    t00 = time.time()
    tb = load_tables(); ctx = make_context(tb); E = _eval_frame(ctx); ctx["_idx"] = E["idx"]; _CTX = ctx
    OUT.mkdir(exist_ok=True)
    idx, dts, hl = E["idx"], E["dts"], E["hl"]
    print(f"sessions {ctx['n']} ({ctx['dates'][0].date()} -> {ctx['dates'][-1].date()}); evaluated {len(idx)} ({dts[0].date()} -> {dts[-1].date()})")
    base = baseline_Q(ctx, idx)
    Q = {BASE["pre"]: base["pre"], BASE["post"]: base["post"]}
    logs = []
    jobs = [(nm, sp) for nm, sp in {**VARIANTS, **DIAG, **POSTHOC}.items()]
    import multiprocessing as mp
    with mp.get_context("fork").Pool(n_jobs) as pool:
        for nm, Qv, NOMv, log, secs in pool.imap_unordered(_run_one, jobs):
            Q[nm] = (Qv, NOMv); logs += log; print(f"  {nm:10s} done in {secs:5.0f}s", flush=True)
    # ---- first session at which a variant used at least one feature (own-window variants)
    cl = pd.DataFrame(logs)
    act = {}
    if len(cl):
        nf = cl[cl.feature == "(n_features_used)"]
        for nm, g in nf.groupby("variant"):
            gg = g[g.coef > 0].block_start
            act[nm] = int(gg.min()) if len(gg) else None
    cl.to_csv(OUT / "hl2_coefs.csv", index=False)
    # ---- benchmark quantiles: trailing-250 empirical, price stays
    Vp, Vq = ctx["V"]["pre"], ctx["V"]["post"]
    bench = {"P_EMP250": (np.array([H1.emp_q(Vp, i, 250) for i in idx]), None), "W_EMP250": (np.array([H1.emp_q(Vq, i, 250) for i in idx]), None)}
    tgs = {"pre": ["H", "L"], "post": ["HO", "LO"]}
    refs = {"pre": (E["Yp"], E["P0"]), "post": (E["Yq"], E["O"])}
    allv = {**{k: (v, "pre" if k.startswith("P_") else "post") for k, v in Q.items()}, **{k: (v, "pre" if k.startswith("P_") else "post") for k, v in bench.items()}}
    S_rows, C_rows, L = [], [], {}
    for nm, ((q, nom), ph) in [(k, ((v[0], v[1]), p)) for k, (v, p) in allv.items()]:
        Y, ref = refs[ph]
        S_rows += H1.score_rows(nm, q, Y, ref, hl, dts, tgs[ph])
        if nom is not None:
            C_rows += atom_cov_rows(nm, q, nom, Y, dts, tgs[ph])
        L[nm] = [M.pinball(Y[:, j], q[:, j, :]) for j in range(2)]
    for nm, ph in (("PRICE_STAYS", "pre"), ("OPEN_STAYS", "post")):
        Y, ref = refs[ph]
        for r in H1.score_rows(nm, np.zeros((len(idx), 2, len(GRID))), Y, ref, hl, dts, tgs[ph]):
            S_rows.append({k: (np.nan if k in ("pinball_x1e4", "pinball_rs_at_now", "cov50", "cov90", "cov90_wilson_lo", "cov90_wilson_hi", "kupiec50", "kupiec90", "below_q5", "above_q95", "p_below_q5", "p_above_q95") else x) for k, x in r.items()})
    summ = pd.DataFrame(S_rows).merge(pd.DataFrame(C_rows), on=["variant", "target", "window", "n"], how="left", suffixes=("", "_atom"))
    summ.to_csv(OUT / "hl2_eval_summary.csv", index=False)
    # ---- DM against the baseline, per window; Holm over the whole family (Final window)
    rows = []
    WIN_ALL = {**H1.WIN, "all": ("2000-01-01", "2099-01-01")}                 # "all" = every evaluated session (n = 1,640): SUPPLEMENTARY, not part of the adoption rule
    for nm in list(VARIANTS) + list(DIAG) + list(POSTHOC):
        ph = "pre" if nm.startswith("P_") else "post"
        for j, tn in enumerate(tgs[ph]):
            for w in ("final", "val", "valfinal", "cas", "dev", "all"):
                a, b = WIN_ALL[w]; m = (dts >= a) & (dts <= b)
                md, t_, p1, p2 = H1.dm(L[nm][j][m], L[BASE[ph]][j][m])
                rows.append(dict(variant=nm, target=tn, window=w, n=int(m.sum()), pinball_var_x1e4=1e4 * L[nm][j][m].mean(), pinball_base_x1e4=1e4 * L[BASE[ph]][j][m].mean(), gain_x1e4=1e4 * md,
                                 gain_pct=100 * md / L[BASE[ph]][j][m].mean(), dm_t=t_, p_variant_better=p1, p_two_sided=p2, in_family=nm in VARIANTS))
    dmt = pd.DataFrame(rows)
    for w in ("final", "valfinal", "all"):
        sel = (dmt.window == w) & dmt.in_family
        dmt.loc[sel, "holm_two_sided"] = H1.holm(dmt.loc[sel, "p_two_sided"].values)
    dmt.to_csv(OUT / "hl2_eval_dm_holm.csv", index=False)
    fam = int(((dmt.window == "final") & dmt.in_family).sum())
    print(f"family size (variant-target pairs): {fam}")
    # ---- adoption rule (fixed in the report before any variant was run)
    ad = []
    S = summ.set_index(["variant", "target", "window"])
    for nm in list(VARIANTS) + list(DIAG):
        ph = "pre" if nm.startswith("P_") else "post"
        for tn in tgs[ph]:
            g = dmt[(dmt.variant == nm) & (dmt.target == tn)].set_index("window")
            b = BASE[ph]
            n_act_val = None
            if nm in act and act[nm] is not None:
                vm = (dts >= pd.Timestamp(H1.WIN["val"][0])) & (dts <= pd.Timestamp(H1.WIN["val"][1]))
                n_act_val = int((idx[vm] >= act[nm]).sum())
            short = VARIANTS.get(nm, DIAG.get(nm, {})).get("short", False)
            c1 = bool(g.loc["final", "gain_pct"] >= 2.0 and g.loc["final", "dm_t"] > 0 and (g.loc["final", "holm_two_sided"] < 0.05 if g.loc["final", "in_family"] else False))
            c2 = bool(g.loc["val", "gain_pct"] > 0 and (not short or (n_act_val is not None and n_act_val >= 0.5 * g.loc["val", "n"])))
            cov_ok, cov_info = True, {}
            for lab in ("50", "90"):
                if ph == "pre":          # pre-open: nominal level 0.5 / 0.9 (as fixed in the report); post-open: the model-implied nominal (atom at zero)
                    lvl = 0.5 if lab == "50" else 0.9
                    dv, db = S.loc[(nm, tn, "final"), f"cov{lab}"] - lvl, S.loc[(b, tn, "final"), f"cov{lab}"] - lvl
                else:
                    dv, db = S.loc[(nm, tn, "final"), f"dev{lab}"], S.loc[(b, tn, "final"), f"dev{lab}"]
                pv = S.loc[(nm, tn, "final"), f"atom_p{lab}"] if ph == "post" else S.loc[(nm, tn, "final"), f"kupiec{lab}"]
                cov_info[f"dev{lab}_var"], cov_info[f"dev{lab}_base"], cov_info[f"p{lab}_var"] = dv, db, pv
                cov_ok &= bool(abs(dv) <= abs(db) + 1e-12 and pv > 0.05)
            cas_ratio = S.loc[(nm, tn, "cas"), "pinball_x1e4"] / S.loc[(b, tn, "cas"), "pinball_x1e4"]
            c4 = bool(cas_ratio <= 1.05)
            ad.append(dict(variant=nm, target=tn, family_member=nm in VARIANTS, gain_pct_final=g.loc["final", "gain_pct"], p_final=g.loc["final", "p_two_sided"], holm_final=g.loc["final", "holm_two_sided"], gain_pct_val=g.loc["val", "gain_pct"],
                           active_val_sessions=n_act_val, **cov_info, cas_pinball_ratio=cas_ratio, c1_gain_dm_holm=c1, c2_validation_sign=c2, c3_coverage=bool(cov_ok), c4_cas=c4, c5_leakage="see hl2_leakage.csv",
                           passes_c1_to_c4=bool(c1 and c2 and cov_ok and c4 and nm in VARIANTS), miss_med_rs_var=S.loc[(nm, tn, "final"), "mae_med_rs_at_now"], miss_med_rs_base=S.loc[(b, tn, "final"), "mae_med_rs_at_now"]))
    pd.DataFrame(ad).to_csv(OUT / "hl2_adoption.csv", index=False)
    # ---- descriptive: pinball by calendar year (gain vs baseline, %)
    by = []
    for nm in list(VARIANTS) + list(POSTHOC):
        ph = "pre" if nm.startswith("P_") else "post"
        for j, tn in enumerate(tgs[ph]):
            for yr in sorted(set(dts.year)):
                m = dts.year == yr
                by.append(dict(variant=nm, target=tn, year=int(yr), n=int(m.sum()), pinball_x1e4=1e4 * L[nm][j][m].mean(), base_x1e4=1e4 * L[BASE[ph]][j][m].mean(), gain_pct=100 * (1 - L[nm][j][m].mean() / L[BASE[ph]][j][m].mean())))
    pd.DataFrame(by).to_csv(OUT / "hl2_eval_byyear.csv", index=False)
    if dump:
        np.savez_compressed(dump, idx=idx, **{k: v[0][0] for k, v in allv.items()})
    # ---- stored quantile predictions
    pr = []
    for nm, ((q, nom), ph) in [(k, ((v[0], v[1]), p)) for k, (v, p) in allv.items()]:
        ref = refs[ph][1]
        for j, tn in enumerate(tgs[ph]):
            df = pd.DataFrame({"date": dts, "variant": nm, "target": tn, "ref": ref})
            for lev in (0.05, 0.25, 0.5, 0.75, 0.95):
                df[f"q{int(lev * 100)}"] = q[:, j, list(GRID).index(lev)]
            pr.append(df)
    pd.concat(pr).to_csv(OUT / "hl2_predictions.csv.gz", index=False, float_format="%.6g")
    ctx["F"].assign(_dummy=0).drop(columns="_dummy").to_csv(OUT / "hl2_features_panel.csv.gz", float_format="%.6g")
    ft = pd.DataFrame([dict(feature=f, blocks=FEATURES[f][0], timestamp_rule=FEATURES[f][1], first_valid=str(ctx["F"][f].first_valid_index().date()) if ctx["F"][f].notna().any() else "", n_non_missing=int(ctx["F"][f].notna().sum()),
                            n_non_missing_final=int(ctx["F"].loc["2025-07-01":, f].notna().sum())) for f in ALL_FEATS])
    ft.to_csv(OUT / "hl2_feature_timestamps.csv", index=False)
    json.dump({"family_size_pairs": fam, "n_candidate_variants": len(VARIANTS), "n_features_distinct": len(ALL_FEATS), "n_scale_features": len(_names(list(SCALE_FEATS), SCALE_FEATS)), "n_location_features": len(_names(list(LOC_FEATS), LOC_FEATS)),
               "first_active_block_start_ownwindow": {k: (None if v is None else str(ctx['dates'][v].date())) for k, v in act.items()}, "evaluated_sessions": int(len(idx)),
               "windows_n": {w: int(((dts >= a) & (dts <= b)).sum()) for w, (a, b) in H1.WIN.items()}, "seconds": round(time.time() - t00)}, open(OUT / "hl2_meta.json", "w"), indent=1)
    pd.set_option("display.width", 250)
    print(f"done in {time.time() - t00:.0f}s")
