"""Shared loading + target/feature construction for NSE:BSE.  All definitions follow docs/PREREGISTRATION.md."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

PROC = Path("data/processed")
GRID = np.array([0.025, 0.05, 0.10, 0.25, 0.50, 0.75, 0.90, 0.95, 0.975])
CENTRAL = {0.50: (0.25, 0.75), 0.80: (0.10, 0.90), 0.90: (0.05, 0.95), 0.95: (0.025, 0.975)}
EPS = 1e-8


def load_bse(path: Path | None = None) -> pd.DataFrame:
    d = pd.read_csv(path or PROC / "bse_daily.csv", parse_dates=["date"]).set_index("date").sort_index()
    d = d[~d.index.duplicated(keep="last")]
    # drop listing day: its 'prev' is the IPO issue price, not a traded close
    d = d.iloc[1:].copy()
    ok = (d[["prev", "open", "high", "low", "close"]] > 0).all(axis=1) & (d["high"] >= d["low"])
    if not ok.all():
        raise ValueError(f"bad OHLC rows: {d.index[~ok].tolist()[:10]}")
    return d


def targets(d: pd.DataFrame) -> pd.DataFrame:
    """Log-return targets relative to the exchange-adjusted previous close."""
    t = pd.DataFrame(index=d.index)
    t["G"] = np.log(d["open"] / d["prev"])           # opening gap
    t["I"] = np.log(d["close"] / d["open"])          # open -> close
    t["R"] = np.log(d["close"] / d["prev"])          # close -> close (== G + I)
    t["Hp"] = np.log(d["high"] / d["prev"])          # high vs P0
    t["Lp"] = np.log(d["low"] / d["prev"])           # low vs P0
    t["rho"] = np.log(d["high"] / d["low"])          # daily range
    t["HO"] = np.log(d["high"] / d["open"])
    t["LO"] = np.log(d["low"] / d["open"])
    gk = 0.5 * np.log(d["high"] / d["low"]) ** 2 - (2 * np.log(2) - 1) * np.log(d["close"] / d["open"]) ** 2
    t["gk"] = gk.clip(lower=EPS)                      # Garman-Klass intraday variance proxy
    t["v"] = (t["G"] ** 2 + t["gk"]).clip(lower=EPS)  # total daily variance proxy (gap^2 + GK)
    return t


def load_index(path: Path | None = None) -> pd.DataFrame:
    return pd.read_csv(path or PROC / "index_daily.csv", parse_dates=["date"]).set_index("date").sort_index()


def load_breadth(path: Path | None = None) -> pd.DataFrame:
    return pd.read_csv(path or PROC / "breadth_daily.csv", parse_dates=["date"]).set_index("date").sort_index()


def index_returns(ix: pd.DataFrame) -> pd.DataFrame:
    """Close-to-close log returns of indices (index files carry no adjusted prev close; indices have no corporate actions)."""
    cols = [c for c in ix.columns if c.endswith("_close")]
    c = ix[cols].copy()
    c.columns = [x[:-6] for x in cols]
    r = np.log(c).diff()
    r.columns = [f"r_{x}" for x in r.columns]
    out = pd.concat([c.add_prefix("lvl_"), r], axis=1)
    return out
