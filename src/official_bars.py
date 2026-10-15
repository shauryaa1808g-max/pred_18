"""Official NSE daily bars for BSE that are newer than data/processed/bse_daily.csv.

NSE publishes the CM UDiFF bhavcopy about 16:34 IST on each session day.  `ensure_bars()` downloads every missing session up to today, parses the BSE (EQ) row and appends it to
data/processed/bse_daily_extra.csv (raw zips go to data/raw/udiff/).  `load_bse_ext()` returns the original table plus those rows, in the same layout `common.targets` expects.
No corporate action is assumed in the extra rows (ca_factor = 1): check data/corp_actions_verified.csv before using it across an ex-date.
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path

import numpy as np
import pandas as pd

from common import load_bse

EXTRA = Path("data/processed/bse_daily_extra.csv")
IST = dt.timezone(dt.timedelta(hours=5, minutes=30))


def _fetch_zip(day: pd.Timestamp) -> Path | None:
    zp = Path("data/raw/udiff") / f"{day:%Y%m%d}.zip"
    if zp.exists():
        return zp
    import requests
    from fetch_nse import CA, UA
    try:
        r = requests.get(f"https://nsearchives.nseindia.com/content/cm/BhavCopy_NSE_CM_0_0_0_{day:%Y%m%d}_F_0000.csv.zip", headers={"User-Agent": UA}, timeout=60, verify=CA)
    except Exception:
        return None
    if r.status_code != 200 or r.content[:2] != b"PK":
        return None
    zp.parent.mkdir(parents=True, exist_ok=True); zp.write_bytes(r.content)
    return zp


def ensure_bars(verbose: bool = True) -> pd.DataFrame:
    base = load_bse()
    extra = pd.read_csv(EXTRA, index_col=0, parse_dates=True) if EXTRA.exists() else pd.DataFrame()
    last = max([base.index[-1]] + ([extra.index[-1]] if len(extra) else []))
    today = pd.Timestamp(dt.datetime.now(IST).date())
    from build_dataset import read_udiff
    prev_close = float((extra if len(extra) else base)["close"].iloc[-1])
    rows = []
    for day in pd.date_range(last + pd.Timedelta(days=1), today):
        if day.dayofweek >= 5:
            continue                                   # Budget Saturdays and special sessions must be added by hand
        zp = _fetch_zip(day)
        if zp is None:
            if verbose and day < today:
                print(f"no official file for {day.date()} (holiday, or not published yet)")
            continue
        u = read_udiff(zp); r = u[(u["symbol"] == "BSE") & (u["series"] == "EQ")]
        if r.empty:
            continue
        r = r.iloc[0]
        rows.append(pd.Series({"series": "EQ", "open": r["open"], "high": r["high"], "low": r["low"], "last": r["last"], "close": r["close"], "vol": r["vol"], "turnover_cr": r["turnover_cr"], "trades": r["trades"],
                               "src": "udiff", "short_session": False, "weekend": False, "prev_close_kept": prev_close, "ca_factor": 1.0, "prev": prev_close, "nse_prev": r["prev"], "nse_prev_vs_kept_close": r["prev"] / prev_close}, name=day))
        prev_close = float(r["close"])
    if rows:
        new = pd.DataFrame(rows); new.index.name = "date"
        extra = pd.concat([extra, new]) if len(extra) else new
        extra.to_csv(EXTRA)
        if verbose:
            print("added official bars:", [str(i.date()) for i in new.index])
    return extra


def load_bse_ext() -> pd.DataFrame:
    ensure_bars(verbose=False)
    base = load_bse()
    if not EXTRA.exists():
        return base
    extra = pd.read_csv(EXTRA, index_col=0, parse_dates=True)
    extra = extra[~extra.index.isin(base.index)]
    return pd.concat([base, extra.reindex(columns=base.columns)]).sort_index()


if __name__ == "__main__":
    ensure_bars()
    d = load_bse_ext(); print(d[["open", "high", "low", "close", "vol", "prev"]].tail(4))
