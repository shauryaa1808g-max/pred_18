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
  --leakage                             junk-replacement leakage test (data from the target session on replaced)     -> results/hl2_leakage.csv, hl2_expiry_advance_check.csv; sets the adoption verdicts in hl2_adoption.csv
  --tables                              print the report's markdown tables from the result files
  --univariate                          rebuild only results/hl2_univariate.csv (descriptive screen; also done by --eval)
  --finalize                            merge results/hl2_leakage.csv into results/hl2_adoption.csv (adopted = conditions i-v); run after --eval and --leakage
  --spotcheck / --sp-buckets            timestamp spot check of the feature panel -> results/hl2_spotcheck.csv; descriptive S&P-bucket table -> results/hl2_sp_buckets.csv
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
LV_Q50 = LV["q50"]
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
LAST_OFFICIAL = pd.Timestamp("2026-10-15")      # last session whose data any study may use (the session of 16 Oct 2026 was in progress; its data must not enter any evaluation)

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
    "sp": ["sp_ret"],         # single-feature pseudo-block, used only by the POST HOC variant P_LO_sp
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
POSTHOC.update({f"{nm}_fix{lam:g}": dict(VARIANTS[nm], fixlam=lam) for nm in ("P_SC_s", "W_SC_s") for lam in (0.3, 3.0)})        # the short-sample (implied vol) block with a fixed ridge instead of CV
POSTHOC.update({"P_LO_b": dict(phase="pre", scale=[], loc=["b"], tail=False), "P_LO_sp": dict(phase="pre", scale=[], loc=["sp"], tail=False), "W_LO_sp": dict(phase="post", scale=[], loc=["sp"], tail=False)})      # post hoc: the location signal of P_LO_f, narrowed to the US block / the S&P return after the coefficients were seen
POSTHOC.update({f"{nm}_fix{lam:g}": dict(DIAG[nm], fixlam=lam) for nm in ("P_PLACEBO", "W_PLACEBO") for lam in (0.3, 3.0)})       # random columns FORCED in with a fixed ridge: what pure noise costs when CV does not shrink it away
BASE = {"pre": "P_S6", "post": "W_I6"}
POSTHOC_LOC = ["P_LO_b", "P_LO_sp", "W_LO_sp"]       # post hoc location variants (US block / S&P return only); listed with the pre-fixed ones in the comparison file and in the leakage test, never adoptable
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


def cap_tables(tb: dict, last) -> dict:
    """The same tables with every row dated after `last` removed (bars, index, breadth, peers, F&O IV, US / FRED series).  Calendar sets (expiry dates, results dates) are kept: they are known in advance."""
    last = pd.Timestamp(last)
    out = dict(tb)
    out["bars"] = tb["bars"][tb["bars"].index <= last]
    for k in ("idx", "br", "iv"):
        out[k] = tb[k][tb[k].index <= last]
    out["peers"] = tb["peers"][tb["peers"]["date"] <= last]
    out["us"] = {k: v[v.index <= last] for k, v in tb["us"].items()}
    return out


def load_tables(fill=True, last=LAST_OFFICIAL) -> dict:
    """Every input table the features read, as plain objects (so that the leakage test can replace parts of them).  The 13-15 Oct 2026 rows missing from the processed files come from results/hl2_fill_*.csv.
    last = the last session date any row may have (default 15 Oct 2026: data/processed/bse_daily_extra.csv also holds the 16 Oct bar, which no study may use); last=None keeps everything."""
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
    tb = {"bars": bars, "idx": ix, "br": br, "peers": pe, "iv": iv, "us": us, "expiries": pd.DatetimeIndex(sorted(set(expiries))), "results": pd.DatetimeIndex(res["first_tradable_session"])}
    return tb if last is None else cap_tables(tb, last)


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
    ctx = make_context(load_tables(last=LAST_OFFICIAL)) if ctx is None else ctx
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


def univariate_screen(ctx, E):
    """DESCRIPTIVE (cannot lead to adoption): Spearman correlation of every feature with what the baseline leaves unexplained, in two windows that never mix (Development + Validation sessions, and Final).
    scale features vs the ratio of the realised path range to the baseline sigma (pre-open: [max(Hp,0)+max(-Lp,0)]/sigma_S6; post-open: ln(H/L)/sigma_I6); location features vs Hp/sigma, Lp/sigma (pre) and HO/sigma, LO/sigma (post)."""
    idx, dts, F = E["idx"], E["dts"], ctx["F"].iloc[E["idx"]]
    wins = {"dev_val": (dts <= pd.Timestamp("2025-06-30")), "final": (dts >= pd.Timestamp("2025-07-01"))}
    rows = []
    for ph in ("pre", "post"):
        V, sg = ctx["V"][ph][idx], ctx["sig"][ph][idx]
        yH, yL = (np.maximum(V[:, 0], 0), np.maximum(-V[:, 1], 0)) if ph == "pre" else (V[:, 0], -V[:, 1])
        tg = {"scale: path range / sigma": (yH + yL) / sg}
        tg.update({"location: high side / sigma": V[:, 0] / sg, "location: low side / sigma": V[:, 1] / sg})
        for lab, y in tg.items():
            feats = SCALE_FEATS if lab.startswith("scale") else LOC_FEATS
            for blk, names in feats.items():
                if (blk == "o" and ph == "pre") or blk == "sp":          # the single-feature pseudo-block "sp" duplicates sp_ret of block b
                    continue
                for f in names:
                    r = dict(phase=ph, target=lab, block=blk, feature=f)
                    for w, m in wins.items():
                        x, yy = F[f].values[m], y[m]
                        ok = np.isfinite(x) & np.isfinite(yy)
                        if ok.sum() >= 40 and np.unique(x[ok]).size > 2:
                            rho, p = stats.spearmanr(x[ok], yy[ok]); r.update({f"n_{w}": int(ok.sum()), f"spearman_{w}": float(rho), f"p_{w}": float(p)})
                        else:
                            r.update({f"n_{w}": int(ok.sum()), f"spearman_{w}": np.nan, f"p_{w}": np.nan})
                    rows.append(r)
    sc = pd.DataFrame(rows)
    sc["same_sign_both_windows"] = np.sign(sc.spearman_dev_val) == np.sign(sc.spearman_final)
    sc["holm_dev_val"] = np.nan
    for (ph, lab), g in sc.groupby(["phase", "target"]):
        ok = g.p_dev_val.notna()
        sc.loc[g.index[ok], "holm_dev_val"] = H1.holm(g.p_dev_val[ok].values)
    sc.to_csv(OUT / "hl2_univariate.csv", index=False)


def evaluate(n_jobs=4, dump=None):
    """Full pre-fixed evaluation -> results/hl2_*.csv."""
    global _CTX
    t00 = time.time()
    tb = load_tables(last=LAST_OFFICIAL); ctx = make_context(tb); E = _eval_frame(ctx); ctx["_idx"] = E["idx"]; _CTX = ctx
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
            gg = g[(g.coef > 0) & np.isfinite(g.lam)].block_start          # "used" = at least one kept column AND a finite ridge strength (not the no-feature fallback)
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
    WIN_ALL = {**H1.WIN, "all": ("2000-01-01", "2099-01-01"), "from_2026_03": ("2026-03-09", "2099-01-01")}       # SUPPLEMENTARY windows, not part of the adoption rule: "all" = every evaluated session (n = 1,640); "from_2026_03" = from the first block in which the short-sample (implied vol) block was fitted with a finite ridge
    for nm in list(VARIANTS) + list(DIAG) + list(POSTHOC):
        ph = "pre" if nm.startswith("P_") else "post"
        for j, tn in enumerate(tgs[ph]):
            for w in ("final", "val", "valfinal", "cas", "dev", "all", "from_2026_03"):
                a, b = WIN_ALL[w]; m = (dts >= a) & (dts <= b)
                md, t_, p1, p2 = H1.dm(L[nm][j][m], L[BASE[ph]][j][m])
                p2l = {}
                for lg in (10, 20):         # SUPPLEMENTARY: the same test with a longer HAC lag (the rule uses lag 5)
                    _, _, p1l = M.diebold_mariano(L[nm][j][m], L[BASE[ph]][j][m], lag=lg)
                    p2l[f"p_two_sided_lag{lg}"] = 2 * min(p1l, 1 - p1l) if np.isfinite(p1l) else np.nan
                rows.append(dict(variant=nm, target=tn, window=w, n=int(m.sum()), pinball_var_x1e4=1e4 * L[nm][j][m].mean(), pinball_base_x1e4=1e4 * L[BASE[ph]][j][m].mean(), gain_x1e4=1e4 * md,
                                 gain_pct=100 * md / L[BASE[ph]][j][m].mean(), dm_t=t_, p_variant_better=p1, p_two_sided=p2, in_family=nm in VARIANTS, **p2l))
    dmt = pd.DataFrame(rows)
    for w in ("final", "valfinal", "all"):
        sel = (dmt.window == w) & dmt.in_family
        dmt.loc[sel, "holm_two_sided"] = H1.holm(dmt.loc[sel, "p_two_sided"].values)
    sel = (dmt.window == "final")                                   # SUPPLEMENTARY: Holm if the post hoc sensitivity variants were added to the family (74 pairs); not part of the adoption rule
    dmt.loc[sel, "holm_incl_posthoc"] = H1.holm(dmt.loc[sel, "p_two_sided"].fillna(1.0).values)
    dmt.to_csv(OUT / "hl2_eval_dm_holm.csv", index=False)
    # ---- the typical rupee miss of the median (mean |error of the 50% quantile| x Rs 3,428) of every variant against the baseline, paired DM on the absolute errors (SUPPLEMENTARY; not part of the adoption rule)
    mm = []
    for nm in list(VARIANTS) + list(DIAG) + list(POSTHOC):
        ph = "pre" if nm.startswith("P_") else "post"
        Y, _ = refs[ph]
        for j, tn in enumerate(tgs[ph]):
            eb, ev = np.abs(Y[:, j] - Q[BASE[ph]][0][:, j, LV_Q50]), np.abs(Y[:, j] - Q[nm][0][:, j, LV_Q50])
            for w in ("final", "val", "valfinal", "cas", "dev"):
                a, b = H1.WIN[w]; m = (dts >= a) & (dts <= b)
                md, t_, p1, p2 = H1.dm(ev[m], eb[m])
                mm.append(dict(variant=nm, target=tn, window=w, n=int(m.sum()), miss_variant_rs_at_now=P_NOW * ev[m].mean(), miss_baseline_rs_at_now=P_NOW * eb[m].mean(), improvement_rs=P_NOW * md, dm_t=t_, p_two_sided=p2,
                               in_family=nm in VARIANTS))
    pd.DataFrame(mm).to_csv(OUT / "hl2_eval_medmiss.csv", index=False)
    fam = int(((dmt.window == "final") & dmt.in_family).sum())
    print(f"family size (variant-target pairs): {fam}")
    # ---- adoption rule (fixed in the report before any variant was run)
    S = summ.set_index(["variant", "target", "window"])

    def adoption_rows(names, holm_col, member):
        ad_ = []
        for nm in names:
            ph = "pre" if nm.startswith("P_") else "post"
            for tn in tgs[ph]:
                g = dmt[(dmt.variant == nm) & (dmt.target == tn)].set_index("window")
                b = BASE[ph]
                n_act_val = None
                if nm in act and act[nm] is not None:
                    vm = (dts >= pd.Timestamp(H1.WIN["val"][0])) & (dts <= pd.Timestamp(H1.WIN["val"][1]))
                    n_act_val = int((idx[vm] >= act[nm]).sum())
                short = VARIANTS.get(nm, DIAG.get(nm, {})).get("short", False)
                hp = g.loc["final", holm_col]
                c1 = bool(g.loc["final", "gain_pct"] >= 2.0 and g.loc["final", "dm_t"] > 0 and (hp < 0.05 if pd.notna(hp) else False))
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
                ad_.append(dict(variant=nm, target=tn, family_member=member(nm), gain_pct_final=g.loc["final", "gain_pct"], p_final=g.loc["final", "p_two_sided"], holm_final=hp, gain_pct_val=g.loc["val", "gain_pct"],
                                active_val_sessions=n_act_val, **cov_info, cas_pinball_ratio=cas_ratio, c1_gain_dm_holm=c1, c2_validation_sign=c2, c3_coverage=bool(cov_ok), c4_cas=c4, c5_leakage="see hl2_leakage.csv",
                                passes_c1_to_c4=bool(c1 and c2 and cov_ok and c4 and member(nm)), miss_med_rs_var=S.loc[(nm, tn, "final"), "mae_med_rs_at_now"], miss_med_rs_base=S.loc[(b, tn, "final"), "mae_med_rs_at_now"]))
        return ad_

    ad = adoption_rows(list(VARIANTS) + list(DIAG), "holm_two_sided", lambda nm: nm in VARIANTS)
    pd.DataFrame(ad).to_csv(OUT / "hl2_adoption.csv", index=False)
    # POST HOC variants (sensitivity checks and the two location variants narrowed after the coefficients were seen): the same five conditions evaluated "as if" they had been in the family, with the Holm that counts every pair
    # tried (pre-fixed + placebo + post hoc).  These rows CANNOT lead to adoption (family_member False => passes False); they exist so that the lead can see how far each would have been from the rule.
    pd.DataFrame(adoption_rows(list(POSTHOC), "holm_incl_posthoc", lambda nm: False)).drop(columns=["passes_c1_to_c4", "c5_leakage"]).to_csv(OUT / "hl2_adoption_posthoc.csv", index=False)
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
    ctx["F"].to_csv(OUT / "hl2_features_panel.csv.gz", float_format="%.6g")
    univariate_screen(ctx, E)
    ft = pd.DataFrame([dict(feature=f, blocks=FEATURES[f][0], timestamp_rule=FEATURES[f][1], first_valid=str(ctx["F"][f].first_valid_index().date()) if ctx["F"][f].notna().any() else "", n_non_missing=int(ctx["F"][f].notna().sum()),
                            n_non_missing_final=int(ctx["F"].loc["2025-07-01":, f].notna().sum())) for f in ALL_FEATS])
    ft.to_csv(OUT / "hl2_feature_timestamps.csv", index=False)
    json.dump({"family_size_pairs": fam, "n_candidate_variants": len(VARIANTS), "n_features_distinct": len(ALL_FEATS), "n_scale_features": len(_names(list(SCALE_FEATS), SCALE_FEATS)), "n_location_features": len(_names(list(LOC_FEATS), LOC_FEATS)),
               "first_active_block_start_ownwindow": {k: (None if v is None else str(ctx['dates'][v].date())) for k, v in act.items()}, "evaluated_sessions": int(len(idx)),
               "windows_n": {w: int(((dts >= a) & (dts <= b)).sum()) for w, (a, b) in H1.WIN.items()}, "seconds": round(time.time() - t00)}, open(OUT / "hl2_meta.json", "w"), indent=1)
    pd.set_option("display.width", 250)
    print(f"done in {time.time() - t00:.0f}s")


# ----------------------------------------------------------------------------------------------- live forecast
def spec_of(name):
    return {**VARIANTS, **DIAG, **POSTHOC}[name]


def live_variant_quantiles(ctx, name, ph):
    """Quantiles [2, 9] (log, vs P0 pre-open or vs the open post-open) and draws [n, 2] of one variant for the unseen session of a live context."""
    spec = BASE_SPEC[ph] if name in BASE.values() else spec_of(name)
    n = ctx["n"]
    S, SH = block_fit(ctx, spec, name, n, None, n + 1, {}, None) if (spec["scale"] or spec["loc"]) else (np.repeat(ctx["sig"][ph][:n + 1, None], 2, axis=1).astype(float), np.zeros((n + 1, 2)))
    dr = draws_at(ctx, spec, S, SH, n)
    return np.quantile(dr, GRID, axis=0).T, dr


BASE_SPEC = {ph: dict(phase=ph, scale=[], loc=[], tail=False) for ph in ("pre", "post")}


def adopted_variants() -> dict:
    """{target: variant name} for every target where a variant met the whole adoption rule (results/hl2_adoption.csv, column adopted); empty when none did (the baseline stays)."""
    f = OUT / "hl2_adoption.csv"
    if not f.exists() or "adopted" not in pd.read_csv(f, nrows=1).columns:
        return {}
    a = pd.read_csv(f)
    return {r.target: r.variant for r in a[a.adopted.astype(bool)].itertuples()}


def _side2(variant, target, ref, q, summ):
    """Same fields as hl_model._side, with the typical miss read from results/hl2_eval_summary.csv (the walk-forward evaluation of THIS variant)."""
    px = {**{k: round(float(ref * np.exp(q[g])), 2) for k, g in LV.items()}, "q2.5": round(float(ref * np.exp(q[0])), 2), "q97.5": round(float(ref * np.exp(q[8])), 2)}
    out = {"variant": variant, "price_quantiles": px, "pct_of_reference": {k: round(100 * float(np.exp(q[g]) - 1), 2) for k, g in LV.items()},
           "band_width_rs": {"50%": round(px["q75"] - px["q25"], 1), "90%": round(px["q95"] - px["q5"], 1)}}
    if summ is not None:
        for w, key in (("final", ""), ("cas", "_cas_slice")):
            x = summ[(summ.variant == variant) & (summ.target == target) & (summ.window == w)]
            if not x.empty:
                out.update({f"typical_miss_rs{key}": round(float(x.mae_med_pct.iloc[0]) / 100 * ref, 1), f"half_the_time_within_rs{key}": round(float(x.medae_med_pct.iloc[0]) / 100 * ref, 1), f"miss_measured_on_sessions{key}": int(x.n.iloc[0])})
    return out


def hl2_forecast(date, open_price=None, variant=None, tb=None, all_variants=False, cap=True) -> dict:
    """Same dict shape as hl_model.hl_forecast.  Only data dated before `date` is used (plus `open_price` = the official 09:08 open, if given).
    Default: for each target the variant that met the whole adoption rule (results/hl2_adoption.csv), else the BASELINE (P_S6 / W_I6); so while no variant is adopted the numbers are the baseline's.
    variant='P_SL_f' (or any other name in VARIANTS) forces that variant for the pre-open (or post-open) targets of its phase: for comparison only, NOT adopted unless the adoption table says so.
    all_variants=True adds 'all_variants': the quantiles of every pre-fixed variant (for the comparison file results/hl2_<date>.json).  tb = input tables (default: the repo's, capped before `date`)."""
    date = pd.Timestamp(date)
    tb = load_tables(last=date - pd.Timedelta(days=1)) if tb is None else (cap_tables(tb, date - pd.Timedelta(days=1)) if cap else tb)       # cap=False only for the leakage test
    ctx = make_context(tb, date, open_price)
    n, d = ctx["n"], ctx["d"]
    known = d.iloc[:n]
    P0 = float(known["close"].iloc[-1])
    if open_price is not None and abs(np.log(open_price / P0)) > 0.2:
        raise ValueError("open more than 20% from the previous close: check the number")
    missing = [str(x.date()) for x in pd.bdate_range(known.index[-1] + pd.Timedelta(days=1), date - pd.Timedelta(days=1))]
    summ = pd.read_csv(OUT / "hl2_eval_summary.csv") if (OUT / "hl2_eval_summary.csv").exists() else None
    ad = adopted_variants()
    used = {"H": ad.get("H", BASE["pre"]), "L": ad.get("L", BASE["pre"]), "HO": ad.get("HO", BASE["post"]), "LO": ad.get("LO", BASE["post"])}
    if variant is not None:
        ph = "pre" if variant.startswith("P_") else "post"
        used.update({k: variant for k in (("H", "L") if ph == "pre" else ("HO", "LO"))})
    cache = {}
    def lvq(nm, ph):
        if (nm, ph) not in cache:
            cache[(nm, ph)] = live_variant_quantiles(ctx, nm, ph)
        return cache[(nm, ph)]
    def phase_block(ph, ref, tn):
        qs, drs = [], []
        for j, tg in enumerate(tn):
            q, dr = lvq(used[tg], ph)
            qs.append(q[j]); drs.append(dr[:, j])
        return qs, drs
    last = str(known.index[-1].date())
    cols = [c for c in ALL_FEATS if c in ctx["F"].columns]
    row = ctx["F"].iloc[n]
    out = {"date": str(date.date()), "p0": P0, "data_through": last, "n_sessions": n, "missing_weekdays_between_data_and_date": missing, "is_weekend": bool(date.dayofweek >= 5),
           "model_pre": "baseline S6 volatility x filtered historical simulation (hl_model.py)" if all(used[k] == BASE["pre"] for k in ("H", "L")) else f"{used['H']} (high) / {used['L']} (low), see research/hl/D_features.md",
           "variants_used": used, "adopted_variants": ad, "sigma_R_pct": 100 * float(ctx["sig"]["pre"][n]),
           "features_missing_on_the_forecast_date_pre_open_scale_and_location": sorted(c for c in cols if c not in ("absgap_z", "beyond_any", "orel_abs", "gap_z", "orel_c", "beyond_signed") and not np.isfinite(row[c]))}
    (qh, ql), (dh, dl_) = phase_block("pre", P0, ["H", "L"])
    out["pre_open"] = {"high": _side2(used["H"], "H", P0, qh, summ), "low": _side2(used["L"], "L", P0, ql, summ)}
    out["pre_open"]["touch_prob"] = {f"high >= P0+{c:g}%": round(float((dh >= np.log1p(c / 100)).mean()), 3) for c in (0.5, 1, 2, 3)} | {f"low <= P0-{c:g}%": round(float((dl_ <= np.log1p(-c / 100)).mean()), 3) for c in (0.5, 1, 2, 3)}
    if open_price is not None:
        (qo, qlo), (dho, dlo) = phase_block("post", float(open_price), ["HO", "LO"])
        out["model_post"] = "baseline S6 open-to-close volatility x filtered historical simulation (hl_model.py)" if all(used[k] == BASE["post"] for k in ("HO", "LO")) else f"{used['HO']} (high) / {used['LO']} (low)"
        out["sigma_I_pct"] = 100 * float(ctx["sig"]["post"][n])
        tp = {f"high >= open+{c:g}%": round(float((dho >= np.log1p(c / 100)).mean()), 3) for c in (0.5, 1, 2, 3)} | {f"low <= open-{c:g}%": round(float((dlo <= np.log1p(-c / 100)).mean()), 3) for c in (0.5, 1, 2, 3)}
        out["gap_pct"], out["open"] = 100 * float(np.log(open_price / P0)), float(open_price)
        out["post_open"] = {"open": float(open_price), "gap_pct": out["gap_pct"], "high": _side2(used["HO"], "HO", float(open_price), qo, summ), "low": _side2(used["LO"], "LO", float(open_price), qlo, summ), "touch_prob": tp}
    if all_variants:
        av = {}
        for nm in [BASE["pre"]] + [k for k in VARIANTS if k.startswith("P_")] + [k for k in POSTHOC_LOC if k.startswith("P_")] + ([BASE["post"]] + [k for k in VARIANTS if k.startswith("W_")] + [k for k in POSTHOC_LOC if k.startswith("W_")] if open_price is not None else []):
            ph = "pre" if nm.startswith("P_") else "post"
            q, _ = lvq(nm, ph)
            ref = P0 if ph == "pre" else float(open_price)
            av[nm] = {tg: {k: round(float(ref * np.exp(q[j][g])), 2) for k, g in LV.items()} for j, tg in enumerate(("high", "low"))}
        out["all_variants"] = av
    return out


def words2(o: dict) -> str:
    day = pd.Timestamp(o["date"]).strftime("%a %d %b %Y")
    L = [f"BSE Ltd (NSE: BSE), session of {day}.  Reference: official close Rs {o['p0']:,.1f} of {o['data_through']}.  Models used: {o['variants_used']}  (adopted variants: {o['adopted_variants'] or 'none, the baseline stays'})."]
    if o["missing_weekdays_between_data_and_date"]:
        L.append(f"WARNING: no official bar for {o['missing_weekdays_between_data_and_date']} between the data and this date (holiday or stale data).")
    def side(blk):
        out = []
        for k, nm in (("high", "HIGH"), ("low", "LOW ")):
            b, q = blk[k], blk[k]["price_quantiles"]
            miss = f"  Typical miss about Rs {b['typical_miss_rs']:,.0f} (half the time within Rs {b['half_the_time_within_rs']:,.0f}), measured out of sample on the last {b['miss_measured_on_sessions']} sessions." if "typical_miss_rs" in b else ""
            out.append(f"  {nm}: best single guess Rs {q['q50']:,.0f}.{miss}\n        Half the time between Rs {q['q25']:,.0f} and {q['q75']:,.0f}; 19 days in 20 below Rs {q['q95']:,.0f} (5% quantile Rs {q['q5']:,.0f}).")
        return "\n".join(out)
    L.append("BEFORE THE OPEN:\n" + side(o["pre_open"]))
    if "post_open" in o:
        L.append(f"AFTER THE OPEN (official open Rs {o['post_open']['open']:,.1f}):\n" + side(o["post_open"]))
    L.append("Honest limits: ranges, not a direction call; see research/hl/D_features.md (no extra-parameter variant met the adoption rule).")
    return "\n".join(L)


# ----------------------------------------------------------------------------------------------- leakage test (adoption rule, condition v)
CONTROL_DATES = ("2022-03-21", "2024-09-18", "2025-09-10", "2026-08-03")          # sessions that also get the two positive controls
LEAK_DATES = ["2020-09-15", "2022-03-21", "2023-08-10", "2024-09-18", "2025-03-12", "2025-05-23", "2025-09-10", "2026-02-18", "2026-07-15", "2026-08-03", "2026-09-09", "2026-10-15"]


def _junk_frame(df: pd.DataFrame, T, rng, datecol=None) -> pd.DataFrame:
    """Copy of df with every row dated >= T replaced by junk: each numeric column gets values drawn at random (with replacement) from its own earlier rows times a random factor in [0.6, 1.6]."""
    df = df.copy()
    dates = pd.DatetimeIndex(df[datecol] if datecol else df.index)
    late = np.where(dates >= T)[0]
    if not len(late):
        return df
    for c in df.columns:
        if c == datecol or not pd.api.types.is_numeric_dtype(df[c]) or pd.api.types.is_bool_dtype(df[c]):
            continue
        df[c] = df[c].astype(float)
        pool = df[c].values[dates < T]
        pool = pool[np.isfinite(pool)] if len(pool) else pool
        if len(pool):
            df.iloc[late, df.columns.get_loc(c)] = rng.choice(pool, len(late)) * rng.uniform(0.6, 1.6, len(late))
    return df


def junk_tables(tb: dict, T, seed: int, keep_open: bool, tail: int = 30, parts=("bars", "tables", "flags")) -> dict:
    """Input tables in which EVERYTHING dated from the session T onward is junk: random coherent OHLC and volumes for BSE ("bars"); bootstrap-times-noise for index, breadth, peers, F&O IV and the US / FRED
    series ("tables"); expiry and results sets with the dates after T replaced by random dates ("flags"; T's own calendar flag is kept because it is known in advance, see the report).
    keep_open: the target session's own official open and previous close are legitimately known to the post-open variants and are kept.  The bars are cut `tail` sessions after T."""
    T = pd.Timestamp(T)
    rng = np.random.default_rng(seed)
    out = dict(tb)
    pos = int(np.searchsorted(tb["bars"].index.values, T.to_datetime64()))
    b = tb["bars"].iloc[: pos + tail].copy()
    if "bars" in parts:
        ci = {c: b.columns.get_loc(c) for c in ("open", "high", "low", "last", "close", "prev", "prev_close_kept", "nse_prev", "vol", "turnover_cr", "trades", "deliv_pct")}
        last_close = float(b["close"].iloc[pos - 1])
        for k, i in enumerate(range(pos, len(b))):
            prev = float(b.iloc[i, ci["prev"]]) if k == 0 else last_close
            o = float(b.iloc[i, ci["open"]]) if (k == 0 and keep_open) else prev * np.exp(rng.normal(0, 0.03))
            c = o * np.exp(rng.normal(0, 0.04))
            hi, lo = max(o, c) * np.exp(abs(rng.normal(0, 0.03))), min(o, c) * np.exp(-abs(rng.normal(0, 0.03)))
            for nm, v in (("open", o), ("high", hi), ("low", lo), ("last", c), ("close", c), ("prev", prev), ("prev_close_kept", prev), ("nse_prev", prev)):
                b.iloc[i, ci[nm]] = v
            b.iloc[i, ci["vol"]], b.iloc[i, ci["trades"]] = int(rng.integers(5e5, 2e7)), int(rng.integers(2e4, 4e5))
            b.iloc[i, ci["turnover_cr"]], b.iloc[i, ci["deliv_pct"]] = float(rng.uniform(100, 5000)), float(rng.uniform(5, 90))
            last_close = c
    out["bars"] = b
    if "tables" in parts:
        out["idx"], out["br"], out["iv"] = (_junk_frame(tb[k], T, rng) for k in ("idx", "br", "iv"))
        out["peers"] = _junk_frame(tb["peers"], T, rng, datecol="date")
        out["us"] = {}
        for k, s_ in tb["us"].items():
            s2 = s_.copy(); late = s_.index >= T
            if late.any():
                s2.iloc[np.where(late)[0]] = rng.choice(s_.values[~late], late.sum()) * rng.uniform(0.8, 1.25, late.sum())
            out["us"][k] = s2
    if "flags" in parts:
        for k in ("expiries", "results"):
            keep, own = tb[k][tb[k] < T], tb[k][tb[k] == T]
            fake = pd.DatetimeIndex(T + pd.to_timedelta(rng.integers(1, 400, 8), unit="D"))
            out[k] = pd.DatetimeIndex(sorted(set(keep) | set(own) | set(fake)))
    return out


def _leak_job(args):
    """One target session: forecasts of every pre-fixed variant from the real tables and from junk tables (junk from T on), plus two positive controls (junk starting one session earlier: bars only, other tables only)."""
    T, row, tb_real = args
    out = []
    t0 = time.time()
    real = make_context(tb_real)
    ti = int(real["dates"].get_loc(pd.Timestamp(T)))
    Tm1 = real["dates"][ti - 1]
    names = [BASE["pre"], BASE["post"]] + list(VARIANTS) + list(DIAG) + POSTHOC_LOC
    cx = {"J": make_context(junk_tables(tb_real, T, 1000 + ti, keep_open=False)), "Jo": make_context(junk_tables(tb_real, T, 2000 + ti, keep_open=True))}
    ctrl = row in CONTROL_DATES
    if ctrl:
        cx.update({"C1": make_context(junk_tables(tb_real, Tm1, 3000 + ti, keep_open=True, parts=("bars",))), "C2": make_context(junk_tables(tb_real, Tm1, 4000 + ti, keep_open=True, parts=("tables",)))})
    lab = {"J": "junk_from_T", "Jo": "junk_from_T_open_kept", "C1": "positive_control_bars_junk_from_T-1", "C2": "positive_control_tables_junk_from_T-1"}
    for nm in names:
        spec = BASE_SPEC["pre" if nm.startswith("P_") else "post"] if nm in BASE.values() else spec_of(nm)
        ph = spec["phase"]
        qr = run_variant(real, spec, nm, [ti])[0][0]
        for kind in cx:
            if ph == "pre" and kind == "Jo":
                continue           # pre-open variants must not use the open: tested with the open junked ("J")
            if ph == "post" and kind == "J":
                continue           # post-open variants legitimately use the open and the previous close of T: tested with them kept ("Jo")
            q = run_variant(cx[kind], spec, nm, [ti])[0][0]
            out.append(dict(session=str(pd.Timestamp(T).date()), row=ti, variant=nm, test=lab[kind], max_abs_diff_log=float(np.nanmax(np.abs(q - qr))), n_quantiles=int(q.size)))
    return out, time.time() - t0


def leakage(n_jobs=4):
    """Condition (v) of the adoption rule.  Sessions spread over Development, Validation, Final and the closing-auction slice, every pre-fixed variant, junk from the target session on.
    PASS = max abs difference < 1e-9 log points; the positive control (junk starting one session earlier) must CHANGE the forecasts of the variants whose coefficients are non-zero.
    Also: the live 16 Oct forecast (junk from 16 Oct on, including the real 16 Oct bar that data/processed/bse_daily_extra.csv now holds) and the 'known in advance' check of the expiry dates."""
    tb = load_tables(last=LAST_OFFICIAL)
    d = tb["bars"].index
    tests = [(d[int(np.searchsorted(d.values, np.datetime64(x)))], x, tb) for x in LEAK_DATES]
    rows = []
    import multiprocessing as mp
    with mp.get_context("fork").Pool(n_jobs) as pool:
        for r, secs in pool.imap_unordered(_leak_job, tests):
            rows += r; print(f"  {r[0]['session']} done in {secs:.0f}s", flush=True)
    # ---- live 16 Oct 2026 forecast: the tables are NOT capped here (cap=False), so the real 16 Oct bar that data/processed/bse_daily_extra.csv holds is present and the junk is what the code sees
    tball = load_tables(last=None)
    live_d = pd.Timestamp("2026-10-16")
    f_real = hl2_forecast(live_d, 3450.0, tb=cap_tables(tball, live_d - pd.Timedelta(days=1)), all_variants=True)
    for lab, tbx, seed in (("junk_from_T_open_kept", junk_tables(tball, live_d, 77, keep_open=True), 77), ("real_16Oct_data_present_vs_removed", tball, 0)):
        fx = hl2_forecast(live_d, 3450.0, tb=tbx, all_variants=True, cap=False)
        for nm, a_ in f_real["all_variants"].items():
            diff = max(abs(np.log(a_[s_][k] / fx["all_variants"][nm][s_][k])) for s_ in ("high", "low") for k in a_[s_])
            rows.append(dict(session="2026-10-16 (live, open 3450)", row=-1, variant=nm, test=lab, max_abs_diff_log=float(diff), n_quantiles=18))
    f_pre = hl2_forecast(live_d, None, tb=tball, cap=False)                       # pre-open only (no open given)
    f_pre_c = hl2_forecast(live_d, None, tb=cap_tables(tball, live_d - pd.Timedelta(days=1)))
    rows.append(dict(session="2026-10-16 (live, no open)", row=-1, variant="default (baseline)", test="real_16Oct_data_present_vs_removed", max_abs_diff_log=float(max(abs(np.log(f_pre["pre_open"][s_]["price_quantiles"][k] / f_pre_c["pre_open"][s_]["price_quantiles"][k])) for s_ in ("high", "low") for k in LV)), n_quantiles=14))
    lk = pd.DataFrame(rows)
    lk["passed"] = np.where(lk.test.str.startswith("positive_control"), np.nan, (lk.max_abs_diff_log < 1e-9).astype(float))
    # ---- expiry dates known in advance: the earliest raw F&O file (or filled file) that lists a contract expiring on E must be dated before E
    first = {}
    files = sorted(RAW.glob("fo_bse/*.csv")) + sorted(OUT.glob("hl2_fill_fo_*.csv"))
    for f in files:
        if f.stat().st_size < 400:
            continue
        x = pd.read_csv(f, usecols=["XpryDt"])
        day = pd.Timestamp(f.stem.replace("hl2_fill_fo_", ""))
        for e in pd.to_datetime(x["XpryDt"]).unique():
            first[pd.Timestamp(e)] = min(first.get(pd.Timestamp(e), day), day)
    adv = pd.DataFrame([dict(expiry=str(e.date()), first_listed_in_file_dated=str(v.date()), days_in_advance=(e - v).days) for e, v in sorted(first.items()) if e >= EXP_START and e <= LAST_OFFICIAL])
    adv.to_csv(OUT / "hl2_expiry_advance_check.csv", index=False)
    lk["expiry_check_min_days_in_advance"] = float(adv.days_in_advance.min()) if len(adv) else np.nan
    lk.to_csv(OUT / "hl2_leakage.csv", index=False)
    chk = lk[lk.passed.notna()]
    pc = lk[lk.test.str.startswith("positive_control")]
    print(f"leakage: {int(chk.passed.sum())}/{len(chk)} comparisons identical (< 1e-9); worst {chk.max_abs_diff_log.max():.2e}; positive control: {int((pc.max_abs_diff_log > 1e-9).sum())}/{len(pc)} forecasts changed; min days in advance of expiry dates {adv.days_in_advance.min()}")
    finalize_adoption()
    return lk


def finalize_adoption():
    """Merge the leakage verdict (condition v) into results/hl2_adoption.csv: adopted = c1 & c2 & c3 & c4 & c5 for the pre-fixed candidates only."""
    a = pd.read_csv(OUT / "hl2_adoption.csv")
    f = OUT / "hl2_leakage.csv"
    if f.exists():
        lk = pd.read_csv(f)
        lk = lk[lk.passed.notna()]
        ok = lk.groupby("variant").passed.min()
        a["c5_leakage"] = a.variant.map(lambda v: bool(ok.get(v, 0.0) == 1.0))
    else:
        a["c5_leakage"] = False
    a["adopted"] = a.passes_c1_to_c4.astype(bool) & a.c5_leakage.astype(bool) & a.family_member.astype(bool)
    a.to_csv(OUT / "hl2_adoption.csv", index=False)
    print("adopted by the full rule:", a[a.adopted][["variant", "target"]].values.tolist() or "none")


# ----------------------------------------------------------------------------------------------- timestamp spot check of the feature panel
def spotcheck(n_sessions=60, seed=5) -> pd.DataFrame:
    """Recompute a sample of feature values for random sessions straight from the input tables with a separate, plain implementation of the timestamp rules (previous BSE session for NSE tables; last US observation
    dated strictly before the IST date, one more observation back for Brent / dollar index / US 10y; calendar rules) and compare with the feature panel the models use -> results/hl2_spotcheck.csv."""
    tb = load_tables(last=LAST_OFFICIAL)
    ctx = make_context(tb)
    F, S = ctx["F"], ctx["dates"]
    bars, ix, br, iv = tb["bars"], tb["idx"], tb["br"], tb["iv"]
    rng = np.random.default_rng(seed)
    sess = list(S[rng.choice(np.arange(START, len(S)), n_sessions, replace=False)]) + [pd.Timestamp(x) for x in ("2026-10-12", "2026-10-15", "2025-05-23", "2022-03-21")]
    rows = []

    def us_obs(s, t, extra, kind, max_age):
        s2 = s[s.index < t]
        if len(s2) < 3 + extra:
            return np.nan
        cur, prv, dte = s2.iloc[-1 - extra], s2.iloc[-2 - extra], s2.index[-1 - extra]
        if (t - dte).days > max_age:
            return np.nan
        return {"lvl": np.log(cur), "abs": abs(np.log(cur / prv)), "ret": np.log(cur / prv), "abschg": abs(cur - prv)}[kind]

    for t in sess:
        i = S.get_loc(t); tp = S[i - 1]
        h, l = bars["high"].values, bars["low"].values
        lt = np.log(bars["turnover_cr"].values.astype(float))
        z = (lt[i - 1] - lt[i - 60:i].mean()) / lt[i - 60:i].std(ddof=1) if i >= 60 else np.nan
        last2 = (pd.Timestamp(t) + pd.offsets.MonthBegin(1))
        month_end = float(np.busday_count(t.date() + pd.Timedelta(days=1), last2.date()) <= 1)
        exp = {
            "lnvix": np.log(ix.loc[tp, "vix_close"]) if tp in ix.index else np.nan,
            "nifty_lnrange": np.log(np.log(ix.loc[tp, "nifty50_high"] / ix.loc[tp, "nifty50_low"])) if tp in ix.index else np.nan,
            "bank_lnrange": np.log(np.log(ix.loc[tp, "bank_high"] / ix.loc[tp, "bank_low"])) if tp in ix.index else np.nan,
            "br_absadv": abs(br.loc[tp, "adv_share"] - 0.5) if tp in br.index else np.nan,
            "lnrange_y": np.log(np.log(h[i - 1] / l[i - 1])),
            "absgap_y": abs(np.log(bars["open"].iloc[i - 1] / bars["prev"].iloc[i - 1])),
            "turn_z60": z,
            "abs_sp": us_obs(tb["us"]["sp"], t, 0, "abs", STALE), "sp_ret": us_obs(tb["us"]["sp"], t, 0, "ret", STALE), "lnvixus": us_obs(tb["us"]["vixus"], t, 0, "lvl", STALE),
            "abs_usdinr": us_obs(tb["us"]["usdinr"], t, 0, "abs", STALE),
            "abs_brent": us_obs(tb["us"]["brent"], t, 1, "abs", STALE_LAG), "abs_dxy": us_obs(tb["us"]["dxy"], t, 1, "abs", STALE_LAG), "abs_us10y": us_obs(tb["us"]["us10y"], t, 1, "abschg", STALE_LAG),
            "fri": float(t.dayofweek == 4), "tue": float(t.dayofweek == 1), "month_end": month_end,
            "post_hol": float((t - tp).days >= 4),
            "lniv": np.log(iv.loc[tp, "iv_atm"]) if (tp in iv.index) else np.nan,
            "exp_day": (float(t in tb["expiries"]) if t >= EXP_START else np.nan),
        }
        for f, e in exp.items():
            v = F.loc[t, f]
            ok = (np.isnan(v) and np.isnan(e)) or (np.isfinite(v) and np.isfinite(e) and abs(v - e) <= 1e-9 * max(1.0, abs(e)))
            rows.append(dict(feature=f, session=str(t.date()), panel=float(v), recomputed=float(e) if np.isfinite(e) else np.nan, match=bool(ok)))
    df = pd.DataFrame(rows)
    df.to_csv(OUT / "hl2_spotcheck.csv", index=False)
    print(df.groupby("feature").match.agg(["count", "sum"]).T.to_string()); print(f"spot check: {int(df.match.sum())} of {len(df)} feature values match")
    return df


# ----------------------------------------------------------------------------------------------- descriptive: where the high and low sit, by the S&P 500 overnight move
def sp_buckets() -> pd.DataFrame:
    """DESCRIPTIVE (no model, no test): the median high / low (ln vs the previous close) and the median gap and open-to-extreme moves, by the size of the S&P 500 move of the last US session (same date rule as the features).
    Evaluated sessions only (session 750 on, to 15 Oct 2026) so that the windows are the ones of the walk-forward."""
    tb = load_tables(last=LAST_OFFICIAL)
    ctx = make_context(tb)
    idx = np.arange(START, ctx["n"])
    F, d = ctx["F"].iloc[idx], ctx["d"].iloc[idx]
    t = targets(ctx["d"]).iloc[idx]
    sp = F["sp_ret"].values
    dts = d.index
    rows = []
    for wl, m in (("all evaluated (1,640)", np.ones(len(idx), bool)), ("Development+Validation", dts <= pd.Timestamp("2025-06-30")), ("Final", dts >= pd.Timestamp("2025-07-01")), ("auction slice", dts >= pd.Timestamp("2026-08-03"))):
        for bl, b in (("S&P down >= 0.5%", sp <= -0.005), ("S&P within +-0.5%", (sp > -0.005) & (sp < 0.005)), ("S&P up >= 0.5%", sp >= 0.005)):
            k = m & b & np.isfinite(sp)
            if k.sum():
                rows.append(dict(window=wl, bucket=bl, n=int(k.sum()), median_gap_pct=100 * float(np.median(np.expm1(t["G"].values[k]))), median_high_vs_prev_close_pct=100 * float(np.median(np.expm1(t["Hp"].values[k]))),
                                 median_low_vs_prev_close_pct=100 * float(np.median(np.expm1(t["Lp"].values[k]))), median_high_vs_open_pct=100 * float(np.median(np.expm1(t["HO"].values[k]))), median_low_vs_open_pct=100 * float(np.median(np.expm1(t["LO"].values[k]))),
                                 mean_sp_ret_pct=100 * float(sp[k].mean())))
    out = pd.DataFrame(rows)
    out.to_csv(OUT / "hl2_sp_buckets.csv", index=False)
    print(out.round(2).to_string(index=False))
    return out


# ----------------------------------------------------------------------------------------------- report tables (markdown, printed from the result files)
def _verdict(r):
    if not r.family_member:
        return "diagnostic"
    if r.passes_c1_to_c4 and bool(r.get("c5_leakage", False)):
        return "ADOPT"
    if r.gain_pct_final <= 0:
        return "worse or equal"
    fails = [lab for lab, ok in (("(i) gain/DM/Holm", r.c1_gain_dm_holm), ("(ii) Validation sign", r.c2_validation_sign), ("(iii) coverage", r.c3_coverage), ("(iv) auction slice", r.c4_cas)) if not ok]
    return "tie: fails " + ", ".join(fails)


def table_blocks() -> dict:
    """Markdown tables for research/hl/D_features.md, built from results/hl2_*.csv (nothing is typed by hand): {'pre': ..., 'post': ..., 'windows': ...}."""
    S, D, A, MM = (pd.read_csv(OUT / f) for f in ("hl2_eval_summary.csv", "hl2_eval_dm_holm.csv", "hl2_adoption.csv", "hl2_eval_medmiss.csv"))
    f = lambda x, k=2: "-" if pd.isna(x) else f"{x:.{k}f}"          # noqa: E731
    fp = lambda x: "-" if pd.isna(x) else ("<0.001" if x < 0.0005 else f"{x:.3f}")          # noqa: E731
    out = {}
    for key, ph, nm_base, title in (("pre", "P_", "P_S6", "Pre-open (baseline P_S6)"), ("post", "W_", "W_I6", "Post-open (baseline W_I6)")):
        L = [f"**{title}: Final window (n = 320), every pre-fixed variant.** pinball x1e4 (lower is better); gain = % lower than baseline; DM p raw and Holm over the {int(((D.window == 'final') & D.in_family).sum())} pairs; "
             "miss = mean absolute error of the median in Rs at 3,428 (baseline in brackets); Val = Validation gain %; CAS = pinball ratio to baseline in the 52 auction sessions; cov dev = coverage minus nominal in percentage points (50% / 90%).\n",
             "| variant | target | pinball | base | gain % | p raw | Holm | miss Rs (base) | Val gain % | CAS ratio | cov dev 50 / 90 | verdict |\n|---|---|---|---|---|---|---|---|---|---|---|---|"]
        for r in A[A.variant.str.startswith(ph)].itertuples():
            d = D[(D.variant == r.variant) & (D.target == r.target) & (D.window == "final")].iloc[0]
            L.append(f"| `{r.variant}` | {r.target} | {f(d.pinball_var_x1e4)} | {f(d.pinball_base_x1e4)} | {f(d.gain_pct)} | {fp(d.p_two_sided)} | {fp(d.holm_two_sided)} | {f(r.miss_med_rs_var, 1)} ({f(r.miss_med_rs_base, 1)}) | {f(r.gain_pct_val)} | {f(r.cas_pinball_ratio, 3)} | {f(100 * r.dev50_var, 1)} / {f(100 * r.dev90_var, 1)} | {_verdict(pd.Series(r._asdict()))} |")
        out[key] = "\n".join(L)
    W = ["**Pinball gain % by window** (positive = variant better; n: dev 1,072, val 248, val+final 568, final 320, auction 52, all evaluated 1,640; 'all' is supplementary, not part of the rule; the rows below the pre-fixed ones are the POST HOC variants).\n",
         "| variant | target | dev | val | val+final | final | auction | all | p raw (all) |\n|---|---|---|---|---|---|---|---|---|"]
    for v in [k for k in VARIANTS] + list(POSTHOC):
        for tg in (("H", "L") if v.startswith("P_") else ("HO", "LO")):
            g = D[(D.variant == v) & (D.target == tg)].set_index("window")
            if g.empty:
                continue
            W.append(f"| `{v}` | {tg} | " + " | ".join(f(g.loc[w, "gain_pct"]) for w in ("dev", "val", "valfinal", "final", "cas", "all")) + f" | {fp(g.loc['all', 'p_two_sided'])} |")
    out["windows"] = "\n".join(W)
    return out


def tables():
    print("\n\n".join(table_blocks().values()))


# ----------------------------------------------------------------------------------------------- command line
def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--date"); ap.add_argument("--open", type=float, default=None); ap.add_argument("--variant", default=None); ap.add_argument("--json", action="store_true"); ap.add_argument("--save", action="store_true")
    ap.add_argument("--refresh-fill", action="store_true"); ap.add_argument("--fill-cache", default=None)
    ap.add_argument("--baseline-check", action="store_true"); ap.add_argument("--tables", action="store_true"); ap.add_argument("--spotcheck", action="store_true"); ap.add_argument("--sp-buckets", action="store_true"); ap.add_argument("--finalize", action="store_true"); ap.add_argument("--univariate", action="store_true"); ap.add_argument("--eval", action="store_true"); ap.add_argument("--leakage", action="store_true"); ap.add_argument("--jobs", type=int, default=4)
    a = ap.parse_args()
    if a.refresh_fill:
        return refresh_fill(cache=a.fill_cache)
    if a.baseline_check:
        return baseline_check()
    if a.tables:
        return tables()
    if a.spotcheck:
        return spotcheck()
    if a.sp_buckets:
        return sp_buckets()
    if a.finalize:
        return finalize_adoption()
    if a.univariate:
        ctx = make_context(load_tables(last=LAST_OFFICIAL))
        return univariate_screen(ctx, _eval_frame(ctx))
    if a.eval:
        return evaluate(n_jobs=a.jobs)
    if a.leakage:
        return leakage(n_jobs=a.jobs)
    if not a.date:
        ap.error("--date YYYY-MM-DD (or --eval / --leakage / --baseline-check)")
    o = hl2_forecast(a.date, a.open, a.variant, all_variants=a.save)
    if a.save:
        b = H1.hl_forecast(a.date, open_price=a.open)               # the baseline module on the same date: with no adopted variant the two must agree to the paisa
        diffs = [abs(o[ph][sd]["price_quantiles"][k] - b[ph][sd]["price_quantiles"][k]) for ph in (("pre_open", "post_open") if a.open else ("pre_open",)) for sd in ("high", "low") for k in b[ph][sd]["price_quantiles"]]
        o["check_vs_hl_model_baseline"] = {"max_abs_difference_rs_all_quantiles": float(max(diffs)), "applies_when": "no variant adopted (variants_used are the baseline models)", "baseline_pre_open_median_high_low": [b["pre_open"]["high"]["price_quantiles"]["q50"], b["pre_open"]["low"]["price_quantiles"]["q50"]],
                                           "baseline_post_open_median_high_low": ([b["post_open"]["high"]["price_quantiles"]["q50"], b["post_open"]["low"]["price_quantiles"]["q50"]] if a.open else None)}
        o["note"] = ("Comparison file for the lead. 'pre_open' / 'post_open' = the models in 'variants_used' (the baseline, because no extra-parameter variant met the whole adoption rule). 'all_variants' = the quantiles every pre-fixed variant "
                     "would give: for comparison only, NOT adopted.")
    if a.save:
        OUT.mkdir(exist_ok=True); (OUT / f"hl2_{a.date}.json").write_text(json.dumps(o, indent=1, default=float))
    print(json.dumps(o, indent=1, default=float) if a.json else words2(o))


if __name__ == "__main__":
    main()
