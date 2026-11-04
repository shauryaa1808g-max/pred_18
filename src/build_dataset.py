"""Turn the raw NSE archive cache into compact, auditable daily datasets.

Outputs (data/processed/):
  bse_daily.csv      NSE:BSE OHLCV + exchange-adjusted previous close + delivery %
  peers_daily.csv    same for capital-market peers
  index_daily.csv    OHLC of selected NSE indices incl. India VIX
  breadth_daily.csv  cross-sectional market aggregates from the full EQ-series universe
  corp_actions.csv   BSE sessions where PREV_CLOSE != previous session CLOSE (bonus/split/other re-basing)
  build_report.json  coverage + integrity checks

Adjustment convention: NSE re-bases PREV_CLOSE on the ex-date of bonus/split/rights; cash dividends are NOT
re-based.  Hence close/prev_close-1 is a clean *price* return and the intraday gap open/prev_close-1 is clean too.
"""
from __future__ import annotations

import json
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

RAW = Path("data/raw")
OUT = Path("data/processed")
SHORT_RATIO = 0.35
PEERS = ["BSE", "CDSL", "MCX", "ANGELONE", "NUVAMA", "KFINTECH", "CAMS", "IEX", "MOTILALOFS", "ANANDRATHI", "IIFLSEC", "GEOJITFSL", "NSDL", "5PAISA"]
INDICES = {
    "nifty 50": "nifty50", "nifty 500": "nifty500", "nifty midcap 100": "midcap100", "nifty smallcap 100": "smallcap100",
    "nifty next 50": "next50", "nifty bank": "bank", "nifty financial services": "finserv", "nifty capital markets": "capmkts",
    "india vix": "vix",
}
NUM = ["prev", "open", "high", "low", "last", "close", "vol", "trades"]


def read_sec(p: Path) -> pd.DataFrame:
    d = pd.read_csv(p, skipinitialspace=True, na_values=["-", " -", ""])
    d.columns = [c.strip() for c in d.columns]
    d = d.rename(columns={"SYMBOL": "symbol", "SERIES": "series", "PREV_CLOSE": "prev", "OPEN_PRICE": "open", "HIGH_PRICE": "high",
                          "LOW_PRICE": "low", "LAST_PRICE": "last", "CLOSE_PRICE": "close", "TTL_TRD_QNTY": "vol",
                          "TURNOVER_LACS": "turnover_lacs", "NO_OF_TRADES": "trades", "DELIV_QTY": "deliv_qty", "DELIV_PER": "deliv_pct"})
    d["symbol"] = d["symbol"].str.strip()
    d["series"] = d["series"].str.strip()
    d["turnover_cr"] = pd.to_numeric(d["turnover_lacs"], errors="coerce") / 100.0
    for c in NUM + ["deliv_qty", "deliv_pct"]:
        d[c] = pd.to_numeric(d[c], errors="coerce")
    return d[["symbol", "series", "prev", "open", "high", "low", "last", "close", "vol", "turnover_cr", "trades", "deliv_qty", "deliv_pct"]]


def read_legacy(p: Path) -> pd.DataFrame:
    z = zipfile.ZipFile(p)
    d = pd.read_csv(z.open(z.namelist()[0]))
    d = d.rename(columns={"SYMBOL": "symbol", "SERIES": "series", "OPEN": "open", "HIGH": "high", "LOW": "low", "CLOSE": "close",
                          "LAST": "last", "PREVCLOSE": "prev", "TOTTRDQTY": "vol", "TOTALTRADES": "trades"})
    d["symbol"] = d["symbol"].str.strip()
    d["series"] = d["series"].str.strip()
    d["turnover_cr"] = pd.to_numeric(d["TOTTRDVAL"], errors="coerce") / 1e7
    for c in NUM:
        d[c] = pd.to_numeric(d[c], errors="coerce")
    d["deliv_qty"] = np.nan
    d["deliv_pct"] = np.nan
    return d[["symbol", "series", "prev", "open", "high", "low", "last", "close", "vol", "turnover_cr", "trades", "deliv_qty", "deliv_pct"]]


def read_udiff(p: Path) -> pd.DataFrame:
    z = zipfile.ZipFile(p)
    d = pd.read_csv(z.open(z.namelist()[0]))
    d = d.rename(columns={"TckrSymb": "symbol", "SctySrs": "series", "PrvsClsgPric": "prev", "OpnPric": "open", "HghPric": "high", "LwPric": "low",
                          "LastPric": "last", "ClsPric": "close", "TtlTradgVol": "vol", "TtlNbOfTxsExctd": "trades"})
    d["symbol"] = d["symbol"].astype(str).str.strip()
    d["series"] = d["series"].astype(str).str.strip()
    d["turnover_cr"] = pd.to_numeric(d["TtlTrfVal"], errors="coerce") / 1e7
    for c in NUM:
        d[c] = pd.to_numeric(d[c], errors="coerce")
    d["deliv_qty"] = np.nan
    d["deliv_pct"] = np.nan
    return d[["symbol", "series", "prev", "open", "high", "low", "last", "close", "vol", "turnover_cr", "trades", "deliv_qty", "deliv_pct"]]


def read_idx(p: Path) -> pd.DataFrame:
    d = pd.read_csv(p, na_values=["-", " -"])
    d.columns = [c.strip() for c in d.columns]
    d["key"] = d["Index Name"].str.strip().str.lower()
    d = d[d["key"].isin(INDICES)].copy()
    out = pd.DataFrame({
        "name": d["key"].map(INDICES),
        "open": pd.to_numeric(d["Open Index Value"], errors="coerce"),
        "high": pd.to_numeric(d["High Index Value"], errors="coerce"),
        "low": pd.to_numeric(d["Low Index Value"], errors="coerce"),
        "close": pd.to_numeric(d["Closing Index Value"], errors="coerce"),
        "volume": pd.to_numeric(d["Volume"], errors="coerce"),
    })
    return out


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((RAW / "manifest.json").read_text())
    udiff_days = sorted(p.stem for p in (RAW / "udiff").glob("*.zip")) if (RAW / "udiff").exists() else []
    sessions = sorted({d for d, r in manifest.items() if r["idx"] == 200} | {f"{k[:4]}-{k[4:6]}-{k[6:]}" for k in udiff_days})
    bse_rows, peer_rows, breadth_rows, idx_rows = [], [], [], []
    missing_bhav = []
    for ds in sessions:
        key = ds.replace("-", "")
        date = pd.Timestamp(ds)
        sec, leg, udf = RAW / "sec" / f"{key}.csv", RAW / "legacy" / f"{key}.zip", RAW / "udiff" / f"{key}.zip"
        if sec.exists():
            day, src = read_sec(sec), "sec"
        elif udf.exists():
            day, src = read_udiff(udf), "udiff"
        elif leg.exists():
            day, src = read_legacy(leg), "legacy"
        else:
            missing_bhav.append(ds)
            day = None
        idx_file = RAW / "idx" / f"{key}.csv"
        if idx_file.exists():                      # index files are published later (~23:20 IST) than the bhavcopy; a session may exist without them
            ix = read_idx(idx_file)
            ix["date"] = date
            idx_rows.append(ix)
        if day is None:
            continue
        eq = day[day["series"].isin(["EQ", "BE", "BZ", "BL"])].copy()
        eq["date"] = date
        eq["src"] = src
        peer_rows.append(eq[eq["symbol"].isin(PEERS)])
        # cross-sectional breadth on liquid EQ names (turnover >= Rs 1 crore, valid prev/close)
        u = eq[(eq["series"] == "EQ") & (eq["prev"] > 0) & (eq["close"] > 0) & (eq["turnover_cr"] >= 1.0)].copy()
        r = u["close"] / u["prev"] - 1.0
        breadth_rows.append({
            "date": date, "n_liquid": len(u), "adv_share": float((r > 0).mean()), "dec_share": float((r < 0).mean()),
            "med_ret": float(r.median()), "mean_ret_w": float(r.clip(r.quantile(.01), r.quantile(.99)).mean()),
            "turnover_cr_eq": float(eq.loc[eq["series"] == "EQ", "turnover_cr"].sum()),
            "n_ge_5pct_up": int((r >= .05).sum()), "n_ge_5pct_dn": int((r <= -.05).sum()),
        })
    peers = pd.concat(peer_rows, ignore_index=True).sort_values(["symbol", "date"])
    bse = peers[peers["symbol"] == "BSE"].drop(columns="symbol").set_index("date").sort_index()
    idx = pd.concat(idx_rows, ignore_index=True)
    idx_wide = idx.pivot_table(index="date", columns="name", values=["open", "high", "low", "close", "volume"])
    idx_wide.columns = [f"{n}_{f}" for f, n in idx_wide.columns]
    br = pd.DataFrame(breadth_rows).set_index("date").sort_index()

    # --- session-quality flag: short special sessions (Muhurat, DR-drill Saturdays) have a tiny Nifty-50 share volume
    nv = idx_wide["nifty50_volume"].reindex(bse.index)
    med20 = nv.rolling(20, min_periods=10).median().shift(1)
    bse["nifty_vol_ratio"] = nv / med20
    bse["short_session"] = (bse["nifty_vol_ratio"] < SHORT_RATIO)
    bse["weekend"] = bse.index.dayofweek >= 5

    # --- corporate actions: NSE's PREV_CLOSE is NOT re-based on bonus/split ex-dates in these archive files, so the
    # adjustment is applied here from a verified list (data/corp_actions_verified.csv) and returns use our own previous close.
    ca_list = pd.read_csv("data/corp_actions_verified.csv", parse_dates=["ex_date"])
    reg = bse[~bse["short_session"]].copy()
    reg["prev_close_kept"] = reg["close"].shift(1)
    fac = pd.Series(1.0, index=reg.index)
    for _, r in ca_list.iterrows():
        if r["ex_date"] in fac.index:
            fac.loc[r["ex_date"]] = r["factor"]
    reg["ca_factor"] = fac
    reg["prev_adj"] = reg["prev_close_kept"] / fac
    reg["nse_prev"] = reg["prev"]
    reg["nse_prev_vs_kept_close"] = reg["nse_prev"] / reg["prev_close_kept"]
    reg = reg.drop(columns=["prev"]).rename(columns={"prev_adj": "prev"})
    reg = reg.iloc[1:]  # first retained row has no previous kept close
    ca = reg[(reg["nse_prev_vs_kept_close"] - 1).abs() > 0.0005][["nse_prev", "prev_close_kept", "nse_prev_vs_kept_close", "ca_factor", "close", "weekend"]]
    bse_all = bse
    bse = reg

    peers.to_csv(OUT / "peers_daily.csv", index=False)
    bse.to_csv(OUT / "bse_daily.csv")
    bse_all.to_csv(OUT / "bse_all_sessions_with_flags.csv")
    idx_wide.to_csv(OUT / "index_daily.csv")
    br.to_csv(OUT / "breadth_daily.csv")
    ca.to_csv(OUT / "corp_actions.csv")
    rep = {
        "sessions_in_manifest": len(sessions), "sessions_with_bhavcopy": len(sessions) - len(missing_bhav), "missing_bhavcopy": missing_bhav,
        "bse_rows": int(len(bse)), "short_sessions_dropped": [str(x.date()) for x in bse_all.index[bse_all["short_session"].fillna(False)]],
        "weekend_sessions_kept": [str(x.date()) for x in bse.index[bse["weekend"]]], "bse_first": str(bse.index.min().date()), "bse_last": str(bse.index.max().date()),
        "rebase_events": json.loads(ca.reset_index().assign(date=lambda x: x["date"].dt.strftime("%Y-%m-%d")).to_json(orient="records")),
        "series_values_for_bse": sorted(peers[peers["symbol"] == "BSE"]["series"].unique().tolist()),
        "index_first": str(idx_wide.index.min().date()), "index_last": str(idx_wide.index.max().date()),
        "index_cols_with_gaps": {c: int(idx_wide[c].isna().sum()) for c in idx_wide.columns if c.endswith("_close") and idx_wide[c].isna().any()},
    }
    (OUT / "build_report.json").write_text(json.dumps(rep, indent=1))
    print(json.dumps({k: v for k, v in rep.items() if k not in ("missing_bhavcopy",)}, indent=1)[:4000])


if __name__ == "__main__":
    main()
